/**
 * Format a monetary value with comma (,) thousands separators and 2 decimal places.
 *
 * Accepts the raw Decimal string from the backend (precision-safe for large
 * values like "123456789012345.67") or a number. Negatives render with a
 * leading minus sign.
 *
 * Currency is a display concern handled at the call site (symbol after the
 * number, space-separated). Pass `currency` only when you want it appended to
 * the formatted string; otherwise render it as a separate element.
 */
export function formatAmount(value: string | number, currency?: string): string {
  // String-based formatting preserves full Decimal precision from the backend
  // and avoids parseFloat, which loses precision for large values.
  const total = String(value)
  const isNegative = total.startsWith('-')
  const abs = isNegative ? total.slice(1) : total
  const [intPart, decPart = '00'] = abs.split('.')
  const paddedDec = decPart.length < 2 ? decPart.padEnd(2, '0') : decPart.slice(0, 2)
  const formattedInt = intPart.replace(/\B(?=(\d{3})+(?!\d))/g, ',')
  const sign = isNegative ? '-' : ''
  const base = `${sign}${formattedInt}.${paddedDec}`
  return currency ? `${base} ${currency}` : base
}
