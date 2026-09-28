import json
import sys
from pathlib import Path

from openpyxl import load_workbook


def rows(ws):
    headers = [cell.value for cell in ws[4]]
    output = []
    for values in ws.iter_rows(min_row=5, values_only=True):
        if not values[0]:
            continue
        output.append({header: value for header, value in zip(headers, values)})
    return output


def compact_rows(items, fields):
    """Keep the published payload small while the workbook remains readable."""
    return [[item.get(field) for field in fields] for item in items]


def main():
    if len(sys.argv) != 4:
        raise SystemExit("Usage: python scripts/export_catalog.py <workbook.xlsx> <catalog.json> <source-manifest.json>")
    source = Path(sys.argv[1]).resolve()
    target = Path(sys.argv[2]).resolve()
    manifest_path = Path(sys.argv[3]).resolve()
    workbook = load_workbook(source, data_only=True, read_only=True)
    relationships = rows(workbook["Relationship Catalog"])
    roles = rows(workbook["D-s Role Catalog"])
    captured_menus = rows(workbook["Captured Menus"])
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    relationship_fields = [
        "Relationship term", "Classification", "Catalog presence", "Partner-side label",
        "Pairing confidence", "Pairing rule", "FetLife excerpt", "Definition basis", "Source",
    ]
    role_fields = [
        "Role", "FetLife category", "Catalog presence", "Authority axis", "Activity axis",
        "Relationship-role axis", "Partner-side label", "Pairing confidence", "Pairing rule",
        "Partner label in catalog?", "FetLife excerpt", "Definition basis", "Source",
    ]

    payload = {
        "schemaVersion": 2,
        "meta": {
            "captured": manifest["captured"],
            "relationshipCount": len(relationships),
            "roleCount": len(roles),
            "relationshipKinktionaryCount": sum("Relationship Kinktionary" in item["Catalog presence"] for item in relationships),
            "relationshipMenuCount": sum(item["Surface"] == "Add Relationship" for item in captured_menus),
            "dsMenuCount": sum(item["Surface"] == "Add D/s Relationship" for item in captured_menus),
            "kinktionaryRoleCount": sum("Kinktionary" in item["Catalog presence"] for item in roles),
            "selectorRoleCount": sum(item["Catalog presence"].startswith("Public join") for item in roles),
            "officialRelationshipDefinitions": sum(str(item["Definition basis"]).startswith("Official") for item in relationships),
            "officialRoleDefinitions": sum(str(item["Definition basis"]).startswith("Official") for item in roles),
            "scope": f"Captured {manifest['captured']} from the Relationship Kinktionary, Role Kinktionary, public join/profile role selector, authenticated Add Relationship menu, and authenticated Add D/s Relationship menu.",
            "verified": manifest["verified"],
            "defaultRelationshipCatalog": "authenticated-menu",
            "defaultRoleCatalog": "authenticated-menu",
            "pairingAuthority": manifest["pairingAuthority"],
            "licenseUrl": manifest["license"]["url"],
            "licenseScope": manifest["license"]["scope"],
            "termsUrl": manifest["terms"]["url"],
        },
        "relationshipFields": relationship_fields,
        "roleFields": role_fields,
        "relationships": compact_rows(relationships, relationship_fields),
        "roles": compact_rows(roles, role_fields),
    }
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(json.dumps(payload["meta"]))


if __name__ == "__main__":
    main()
