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

/** Single-letter party label shown inside a candidate's color swatch. */
export function partyAbbrev(party: string): string {
  if (party === "Democratic") return "D";
  if (party === "Republican") return "R";
  return party.slice(0, 1).toUpperCase();
}

export type ProbabilityTier = 50 | 60 | 75 | 95;

/** One of 4 confidence tiers per party: 95+ / 75-95 / 60-75 / 50-60. Winner
 * win_probability is always >= 50% by construction, so "50" is the floor. */
export function probabilityTier(
  party: string,
  winProbability: number
): { slug: string; tier: ProbabilityTier } | null {
  if (!KNOWN_PARTIES.has(party)) return null;
  const pct = winProbability * 100;
  const tier: ProbabilityTier = pct >= 95 ? 95 : pct >= 75 ? 75 : pct >= 60 ? 60 : 50;
  return { slug: party.toLowerCase(), tier };
}

export function probabilityColorVar(party: string, winProbability: number): string {
  const t = probabilityTier(party, winProbability);
  return t ? `var(--party-${t.slug}-${t.tier})` : "var(--text-muted)";
}
