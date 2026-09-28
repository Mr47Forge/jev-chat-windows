#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
export_group.py — 从解密后的微信数据库导出群聊消息,按发送者拆分

为每位 top sender 生成一份与 export_contact.py 兼容的 CSV
(is_sender=1 全部标记为该成员),后续可直接喂给 data_loader/sampler/personality 现成管线。

用法:
  python export_group.py --list-groups
  python export_group.py --group "群名片段"
  python export_group.py --group "滕刘丁" --top 4 --output ./group_out
"""

import argparse
import csv
import hashlib
import json
import os
import re
import sqlite3
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Optional

from export_contact import (
    _SCRIPT_DIR, get_db_dir, get_message_dbs,
    get_avatar_path, get_self_wxid,
)


def md5(text: str) -> str:
    return hashlib.md5(text.encode()).hexdigest()


def list_groups(db_dir: Path):
    contact_db = db_dir / 'contact' / 'contact.db'
    conn = sqlite3.connect(contact_db)
    rows = conn.execute(
        "SELECT username, remark, nick_name FROM contact "
        "WHERE username LIKE '%@chatroom' ORDER BY remark, nick_name"
    ).fetchall()
    conn.close()
    print(f"{'群名 / 备注':<30} {'群 ID'}")
    print('-' * 70)
    for username, remark, nick in rows:
        name = remark or nick or '(无名)'
        print(f"{name:<30} {username}")


def find_group(db_dir: Path, query: str):
    contact_db = db_dir / 'contact' / 'contact.db'
    conn = sqlite3.connect(contact_db)
    rows = conn.execute(
        "SELECT username, remark, nick_name FROM contact "
        "WHERE username LIKE '%@chatroom' "
        "AND (remark LIKE ? OR nick_name LIKE ? OR username LIKE ?)",
        (f'%{query}%', f'%{query}%', f'%{query}%')
    ).fetchall()
    conn.close()
    return rows


def get_member_display_name(contact_db: Path, wxid: str) -> str:
    """优先用 remark,其次 nick_name,最后 wxid。"""
    try:
        conn = sqlite3.connect(contact_db)
        row = conn.execute(
            "SELECT remark, nick_name FROM contact WHERE username=?", (wxid,)
        ).fetchone()
        conn.close()
        if row:
            return row[0] or row[1] or wxid
    except Exception:
        pass
    return wxid


def decode_zstd(raw):
    """复用 export_contact 的解码逻辑(避免互相导入)。"""
    try:
        import zstd
    except ImportError:
        zstd = None
    if raw is None:
        return ''
    if isinstance(raw, bytes):
        if zstd and raw[:4] == b'\x28\xb5\x2f\xfd':
            try:
                return zstd.decompress(raw).decode('utf-8', errors='replace')
            except Exception:
                pass
        return raw.decode('utf-8', errors='replace')
    return str(raw)


def strip_sender_prefix(text: str, wxid: str) -> str:
    """群消息内容里其他人发的消息会被前缀化为 'wxid:\n实际内容',去掉。"""
    if not text:
        return text
    prefix = f'{wxid}:\n'
    if text.startswith(prefix):
        return text[len(prefix):]
    # 也兜底匹配 'xxxxx:\n' 形式(短 ID/英文名)
    m = re.match(r'^[A-Za-z0-9_\-]{2,40}:\n', text)
    if m:
        return text[m.end():]
    return text


def collect_group_messages(db_dir: Path, chatroom_wxid: str):
    """返回 [(create_time, sender_wxid, local_type, content_clean), ...]"""
    table = 'Msg_' + md5(chatroom_wxid)
    msg_dbs = get_message_dbs(db_dir)
    if not msg_dbs:
        return [], []

    out = []
    matched = []
    for msg_db in msg_dbs:
        conn = sqlite3.connect(msg_db)
        tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if table not in tables:
            conn.close()
            continue
        name2id = {rowid: u for rowid, u in conn.execute(
            'SELECT rowid, user_name FROM Name2Id'
        ).fetchall()}
        rows = conn.execute(
            f'SELECT create_time, real_sender_id, local_type, message_content '
            f'FROM {table} ORDER BY create_time ASC'
        ).fetchall()
        conn.close()
        matched.append(msg_db.name)
        for ct, sid, lt, content in rows:
            sender = name2id.get(sid, '')
            text = decode_zstd(content)
            text = strip_sender_prefix(text, sender)
            out.append((ct, sender, lt, text))
    return out, matched


def write_member_csv(member_wxid: str, member_name: str,
                     all_msgs, output_path: Path):
    """把某成员的消息写成 export_contact.py 兼容的 CSV(is_sender=1)。"""
    rows = [(ct, lt, text) for ct, sender, lt, text in all_msgs if sender == member_wxid]
    with open(output_path, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.writer(f)
        writer.writerow(['timestamp', 'datetime', 'sender', 'is_sender', 'type', 'content'])
        for ct, lt, text in rows:
            dt = datetime.fromtimestamp(ct).strftime('%Y-%m-%d %H:%M:%S')
            writer.writerow([ct, dt, member_name, 1, lt, text])
    return len(rows)


def main():
    parser = argparse.ArgumentParser(description='导出微信群聊消息(按发送者拆分)')
    parser.add_argument('--group', help='群名片段(模糊匹配)')
    parser.add_argument('--list-groups', action='store_true', help='列出所有群')
    parser.add_argument('--top', type=int, default=4, help='只导出消息量前 N 的成员(默认 4)')
    parser.add_argument('--output', default=None, help='输出目录(默认 ./group_<群名>)')
    parser.add_argument('--db-dir', help='解密数据库目录(覆盖 config.json)')
    args = parser.parse_args()

    db_dir = Path(os.path.expanduser(args.db_dir)) if args.db_dir else get_db_dir()

    if args.list_groups:
        list_groups(db_dir)
        return

    if not args.group:
        parser.print_help()
        sys.exit(1)

    matches = find_group(db_dir, args.group)
    if not matches:
        print(f'❌ 找不到匹配的群: {args.group}')
        sys.exit(1)
    if len(matches) > 1:
        print(f'找到 {len(matches)} 个匹配群:')
        for i, (u, r, n) in enumerate(matches):
            print(f'  [{i+1}] {r or n}  ({u})')
        choice = input('请输入编号: ').strip()
        try:
            username, remark, nick = matches[int(choice) - 1]
        except (ValueError, IndexError):
            print('无效选择'); sys.exit(1)
    else:
        username, remark, nick = matches[0]

    group_name = remark or nick or username
    print(f'[*] 分析群: {group_name} ({username})')

    self_wxid = get_self_wxid(db_dir)
    print(f'[*] 自己 wxid: {self_wxid}')

    msgs, matched_dbs = collect_group_messages(db_dir, username)
    if not msgs:
        print(f'❌ 找不到群消息表 Msg_{md5(username)}')
        sys.exit(1)
    print(f'[*] 共 {len(msgs)} 条消息(来自 {", ".join(matched_dbs)})')

    sender_count = Counter(s for _, s, _, _ in msgs)
    contact_db = db_dir / 'contact' / 'contact.db'

    print(f'[*] 全部成员发言量:')
    for s, c in sender_count.most_common():
        if not s:
            print(f'    [系统/未知]   {c}')
            continue
        name = get_member_display_name(contact_db, s)
        marker = ' ← 你' if s == self_wxid else ''
        print(f'    {name:<15} {c:>5}{marker}')

    # 选 top N(忽略空 sender 系统消息)
    top_senders = [(s, c) for s, c in sender_count.most_common() if s][: args.top]

    safe_group = re.sub(r'[^\w\u4e00-\u9fff]+', '_', group_name).strip('_')
    output_dir = Path(args.output) if args.output else _SCRIPT_DIR / f'group_{safe_group}'
    output_dir.mkdir(parents=True, exist_ok=True)
    print(f'[*] 输出目录: {output_dir}')

    members_meta = []
    for member_wxid, count in top_senders:
        member_name = get_member_display_name(contact_db, member_wxid)
        is_self = (member_wxid == self_wxid)
        slug = re.sub(r'[^A-Za-z0-9_]+', '_', member_wxid)[:30] or 'member'
        member_dir = output_dir / slug
        member_dir.mkdir(exist_ok=True)
        csv_path = member_dir / f'{slug}.csv'
        n = write_member_csv(member_wxid, member_name, msgs, csv_path)
        avatar_path = get_avatar_path(member_wxid, db_dir)
        meta = {
            'self_wxid': member_wxid,
            'self_name': member_name,
            'self_avatar_path': avatar_path,
            'partner_wxid': '',
            'partner_name': '',
            'partner_avatar_path': None,
        }
        meta_path = csv_path.with_suffix('.meta.json')
        with open(meta_path, 'w', encoding='utf-8') as f:
            json.dump(meta, f, ensure_ascii=False, indent=2)
        members_meta.append({
            'wxid': member_wxid,
            'name': member_name,
            'is_self': is_self,
            'message_count': n,
            'csv_path': str(csv_path),
            'meta_path': str(meta_path),
            'slug': slug,
        })
        print(f'    ✓ {member_name:<15} {n:>5} 条 → {csv_path.name}')

    # group overview JSON
    dr_min = min(ct for ct, *_ in msgs)
    dr_max = max(ct for ct, *_ in msgs)
    overview = {
        'group_wxid': username,
        'group_name': group_name,
        'self_wxid': self_wxid,
        'message_count': len(msgs),
        'date_range': [
            datetime.fromtimestamp(dr_min).strftime('%Y-%m-%d'),
            datetime.fromtimestamp(dr_max).strftime('%Y-%m-%d'),
        ],
        'sender_counts': [
            {
                'wxid': s,
                'name': (get_member_display_name(contact_db, s) if s else '[系统]'),
                'count': c,
            }
            for s, c in sender_count.most_common()
        ],
        'top_members': members_meta,
        'source_databases': matched_dbs,
    }
    overview_path = output_dir / 'group_overview.json'
    with open(overview_path, 'w', encoding='utf-8') as f:
        json.dump(overview, f, ensure_ascii=False, indent=2)
    print(f'\n[*] 群级总览写入: {overview_path}')


if __name__ == '__main__':
    main()
