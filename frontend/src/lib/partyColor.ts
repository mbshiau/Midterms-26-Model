// Party identity is a fixed encoding (not a cycled categorical order): the
// same candidate always gets the same color everywhere in the app. Pair
// validated with scripts/validate_palette.js (dataviz skill) — CVD deltaE
// 74.6 light / 66.4 dark, well clear of the safety floor. Actual hex values
// live in index.css as --party-* custom properties (swapped per color-scheme).
const KNOWN_PARTIES = new Set(["Democratic", "Republican"]);

export function partyColorVar(party: string): string {
  const slug = party.toLowerCase();
  if (!KNOWN_PARTIES.has(party)) return "var(--text-muted)";
  return `var(--party-${slug})`;
}
