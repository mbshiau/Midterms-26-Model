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

export interface CombinedTicket {
  candidates: { name: string; party: string; voteShare: number }[];
  winner: { name: string; party: string; probability: number };
}

/** When every candidate in a race shares the same major party -- a
 * top-two/top-four blanket-primary race with no opposing-party nominee at
 * all, e.g. California's or Washington's jungle primaries, or Alaska's
 * top-four primary -- there's no real basis to forecast which specific
 * same-party candidate wins: the backend's fundamentals model gives them
 * an identical baseline share by design (fundamentals_vote_share is
 * party-symmetric), so splitting on Monte Carlo noise alone would
 * misrepresent a coin flip as a real projection between two people.
 * Collapses the ticket into a single combined row instead, matching how
 * VoteHub displays these: the two names joined by " / ", shown as 100%
 * for that party and 0% for the other major party, with the ticket's
 * combined win probability (the sum of the individual ones, since exactly
 * one of them winning is what "this party holds the seat" means) standing
 * in for the seat outcome. Returns null for anything else (an
 * opposite-party race, a third-party-only race, or a single candidate) so
 * the caller falls back to normal per-candidate display. */
export function combinedSamePartyTicket<T extends { name: string; party: string; win_probability: number }>(
  candidates: T[]
): CombinedTicket | null {
  if (candidates.length < 2) return null;
  const parties = new Set(candidates.map((c) => c.party));
  if (parties.size !== 1) return null;
  const [party] = parties;
  if (party !== "Democratic" && party !== "Republican") return null;

  const otherParty = party === "Democratic" ? "Republican" : "Democratic";
  const name = [...candidates].sort((a, b) => b.win_probability - a.win_probability).map((c) => c.name).join(" / ");
  const probability = candidates.reduce((sum, c) => sum + c.win_probability, 0);

  return {
    candidates: [
      { name, party, voteShare: 100 },
      { name: "No Candidate", party: otherParty, voteShare: 0 },
    ],
    winner: { name, party, probability },
  };
}

/** Whether the projected winner represents a change from the seat's
 * current holder. `currentHolderParty` is null whenever the backend has no
 * real basis to name a holder (a scaffolded race, or a redrawn-map state
 * like Texas where the old district's history can't be attributed to the
 * new lines) -- in that case there is no flip signal at all, so this
 * always returns false rather than treating "unknown" as a flip-able
 * party of its own (which previously showed every winner, even a 95%+
 * favorite in an uncompetitive open seat, as a "flip"). */
export function isProjectedFlip(winnerParty: string, currentHolderParty: string | null): boolean {
  return currentHolderParty !== null && winnerParty !== currentHolderParty;
}
