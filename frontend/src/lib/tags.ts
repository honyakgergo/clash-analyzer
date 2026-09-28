// Mirrors backend normalization so the URL is canonical before any request goes out.
const TAG_RE = /^[0289CGJLPQRUVY]{3,15}$/

/** "#pqggvojp" -> "PQGGV0JP" (no #), or null when invalid. */
export function cleanTag(raw: string): string | null {
  const tag = raw.trim().toUpperCase().replace(/%23/g, '').replace(/^#+/, '').replace(/O/g, '0')
  return TAG_RE.test(tag) ? tag : null
}

/** Path segment for the backend (it accepts tags without the #). */
export function tagPath(tag: string): string {
  return encodeURIComponent(cleanTag(tag) ?? tag)
}
