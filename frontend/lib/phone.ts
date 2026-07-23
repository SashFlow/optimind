/**
 * Normalize a user-entered phone number to E.164.
 * Accepts +E.164 or 10-digit Indian mobiles (prefixed with +91).
 */
export function normalizePhoneNumber(raw: string): string | null {
  const trimmed = raw.trim();
  if (!trimmed) return null;

  const digits = trimmed.replace(/[^\d+]/g, '');

  if (digits.startsWith('+')) {
    const rest = digits.slice(1).replace(/\D/g, '');
    if (rest.length < 8 || rest.length > 15) return null;
    return `+${rest}`;
  }

  const onlyDigits = digits.replace(/\D/g, '');
  if (onlyDigits.length === 10) {
    return `+91${onlyDigits}`;
  }
  if (onlyDigits.length === 12 && onlyDigits.startsWith('91')) {
    return `+${onlyDigits}`;
  }
  if (onlyDigits.length >= 8 && onlyDigits.length <= 15) {
    return `+${onlyDigits}`;
  }

  return null;
}
