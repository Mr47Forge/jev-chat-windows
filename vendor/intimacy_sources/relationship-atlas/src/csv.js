export const neutralizeSpreadsheetFormula = (value) => {
  const text = String(value ?? '')
  return /^\s*[=+@-]/.test(text) ? `'${text}` : text
}

export const csvCell = (value) => `"${neutralizeSpreadsheetFormula(value).replaceAll('"', '""')}"`
