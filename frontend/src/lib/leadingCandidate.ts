/** The candidate actually projected to win -- always the highest
 * win_probability, never assumed from array order. RaceSummaryOut.candidates
 * (see the backend's race_movement_summary) is sorted by mean_vote_share,
 * descending, for display purposes (ranking candidates in the "closest
 * races" list, etc.) -- in a near-toss-up race that ordering can disagree
 * with win_probability (simulation variance means the higher-mean-vote-share
 * candidate isn't always the one more likely to actually win), so treating
 * candidates[0] as "the winner" produces a map tile colored for one party
 * while its own tooltip names the other party's candidate as the projected
 * winner. Every place in the app that needs "who's projected to win" (map
 * fill color, tooltips, the home dashboard's mini-maps and Dem/Rep counts,
 * the race page's favorite label) must go through this instead of indexing
 * into the array directly. */
export function leadingCandidate<T extends { win_probability: number }>(
  candidates: T[]
): T | undefined {
  return candidates.reduce<T | undefined>(
    (best, c) => (!best || c.win_probability > best.win_probability ? c : best),
    undefined
  );
}
