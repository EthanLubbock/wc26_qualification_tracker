"""
bracket.py — exact knockout-stage probability engine for World Cup 2026.

Pure and offline-testable: no network or framework imports. Takes parsed
knockout fixtures plus an OddsProvider-style object exposing
``match_probabilities(home, away)`` and walks the fixed bracket tree exactly
(no Monte Carlo) to produce, for every team:

  * reach probabilities  (P reach R16 / QF / SF / Final / champion)
  * opponent distributions per round (free by-product of the same pass)
  * whole-field title odds (champion probability for all 32 teams)

The bracket is a fixed binary tree. ``ADVANCE`` distributions are computed
bottom-up: A[slot][team] is the probability that ``team`` wins ``slot``'s tie
and advances out of it. A parent's distribution follows from its two children:

    A[parent][t] = A[childX][t] * Σ_o A[childY][o] * P(t beats o)
                 + A[childY][t] * Σ_o A[childX][o] * P(t beats o)

When a tie's winner is already known (from ESPN), the slot short-circuits to a
point mass on the winner — keeping displayed numbers anchored to reality.
"""

from __future__ import annotations

from dataclasses import dataclass

# Leaf (Round of 32) to root (Final). Kept local so the engine is self-contained.
ROUNDS = ["R32", "R16", "QF", "SF", "F"]
SLOT_COUNTS = {"R32": 16, "R16": 8, "QF": 4, "SF": 2, "F": 1}

# Round a team reaches by *winning* a tie in the given round.
NEXT_ROUND = {"R32": "R16", "R16": "QF", "QF": "SF", "SF": "F", "F": "champion"}

SHOOTOUT_SPLIT = 0.5   # share of 90-min draw mass assigned to team A (ET+pens ≈ coin flip)

# Fixed 2026 tree: parent slot -> its two child slots (0-based indices).
# Derived from the ESPN feed's placeholder wiring (e.g. R16 #1 is fed by
# "Round of 32 1 Winner" and "Round of 32 3 Winner"), verified 2026-06-29.
CHILDREN: dict[tuple[str, int], list[tuple[str, int]]] = {
    ("R16", 0): [("R32", 0), ("R32", 2)],
    ("R16", 1): [("R32", 1), ("R32", 4)],
    ("R16", 2): [("R32", 3), ("R32", 5)],
    ("R16", 3): [("R32", 6), ("R32", 7)],
    ("R16", 4): [("R32", 10), ("R32", 11)],
    ("R16", 5): [("R32", 8), ("R32", 9)],
    ("R16", 6): [("R32", 12), ("R32", 14)],
    ("R16", 7): [("R32", 13), ("R32", 15)],
    ("QF", 0): [("R16", 0), ("R16", 1)],
    ("QF", 1): [("R16", 4), ("R16", 5)],
    ("QF", 2): [("R16", 2), ("R16", 3)],
    ("QF", 3): [("R16", 6), ("R16", 7)],
    ("SF", 0): [("QF", 0), ("QF", 1)],
    ("SF", 1): [("QF", 2), ("QF", 3)],
    ("F", 0): [("SF", 0), ("SF", 1)],
}


@dataclass
class Slot:
    round: str
    index: int
    team_a: str | None = None
    team_b: str | None = None
    winner: str | None = None
    feeds_into: tuple[str, int] | None = None


# --- bracket construction --------------------------------------------------

def build_bracket(knockout_matches, valid_abbrs) -> dict[str, list[Slot]]:
    """Build the wired 2026 bracket from parsed knockout fixtures.

    ``knockout_matches`` are tracker.KnockoutMatch records (duck-typed: needs
    ``.round/.order/.home/.away/.winner``). ``valid_abbrs`` is the set of real
    team codes — competitors outside it are placeholder slots ("Round of 32 3
    Winner") and stored as None. R32 leaves carry real teams; higher-round
    occupants are derived by the engine, but a decided ``winner`` is recorded
    wherever the feed reports one (anchoring).
    """
    valid = set(valid_abbrs)
    bracket: dict[str, list[Slot]] = {}
    for rnd in ROUNDS:
        bracket[rnd] = [Slot(round=rnd, index=i) for i in range(SLOT_COUNTS[rnd])]

    # Wire feeds_into from the fixed child map.
    for (prnd, pidx), kids in CHILDREN.items():
        for crnd, cidx in kids:
            bracket[crnd][cidx].feeds_into = (prnd, pidx)

    # Populate each round's slots from its fixtures, ordered by ESPN match number.
    by_round: dict[str, list] = {r: [] for r in ROUNDS}
    for m in knockout_matches:
        if m.round in by_round:
            by_round[m.round].append(m)
    for rnd, matches in by_round.items():
        matches.sort(key=lambda m: (getattr(m, "order", 0), m.kickoff))
        for slot, m in zip(bracket[rnd], matches):
            slot.team_a = m.home if m.home in valid else None
            slot.team_b = m.away if m.away in valid else None
            slot.winner = m.winner if m.winner in valid else None
    return bracket


# --- advance probability (no draws) ----------------------------------------

def advance_probability(odds, a: str, b: str, winner: str | None = None) -> tuple[float, float]:
    """P(a advances), P(b advances) for a knockout tie — sums to 1.

    Knockout ties can't draw: extra time then penalties. We split the
    90-minute draw mass with ``SHOOTOUT_SPLIT`` (0.5 = honest coin flip, which
    also absorbs the fact that the Elo p_draw is a 90-minute figure). If the tie
    is already decided, return the certain outcome.
    """
    if winner is not None:
        if winner == a:
            return 1.0, 0.0
        if winner == b:
            return 0.0, 1.0
    p = odds.match_probabilities(a, b)
    tot = p["p_a"] + p["p_draw"] + p["p_b"]
    if tot <= 0:
        return 0.5, 0.5
    pa, pd, pb = p["p_a"] / tot, p["p_draw"] / tot, p["p_b"] / tot
    adv_a = pa + SHOOTOUT_SPLIT * pd
    return adv_a, 1.0 - adv_a


# --- recursive engine ------------------------------------------------------

def advance_distributions(bracket: dict[str, list[Slot]], odds) -> dict[tuple[str, int], dict[str, float]]:
    """A[(round, index)] -> {team: P(team advances out of that slot)}.

    Computed bottom-up over the rounds present in ``bracket`` (the first present
    round is treated as the leaves). Each distribution sums to ~1.
    """
    present = [r for r in ROUNDS if r in bracket]
    if not present:
        return {}
    leaf_round = present[0]

    # Memoise the matchup so the odds provider is hit at most once per *pairing*:
    # one call yields both directions (neutral knockout, so orientation is moot).
    _pbeat: dict[tuple[str, str], float] = {}

    def pbeat(t: str, o: str) -> float:
        if (t, o) not in _pbeat:
            adv_t, adv_o = advance_probability(odds, t, o)
            _pbeat[(t, o)] = adv_t
            _pbeat[(o, t)] = adv_o
        return _pbeat[(t, o)]

    adv: dict[tuple[str, int], dict[str, float]] = {}

    for rnd in present:
        for slot in bracket[rnd]:
            key = (rnd, slot.index)

            # Anchor to reality: a decided tie is a point mass on its winner.
            if slot.winner is not None:
                adv[key] = {slot.winner: 1.0}
                continue

            if rnd == leaf_round:
                a, b = slot.team_a, slot.team_b
                if a and b:
                    pa, pb = advance_probability(odds, a, b)
                    adv[key] = {a: pa, b: pb}
                elif a:
                    adv[key] = {a: 1.0}
                elif b:
                    adv[key] = {b: 1.0}
                else:
                    adv[key] = {}
                continue

            kids = CHILDREN.get(key)
            if not kids:
                adv[key] = {}
                continue
            dist_x = adv.get(kids[0], {})
            dist_y = adv.get(kids[1], {})
            out: dict[str, float] = {}
            for t, pt in dist_x.items():
                out[t] = pt * sum(po * pbeat(t, o) for o, po in dist_y.items())
            for t, pt in dist_y.items():
                out[t] = out.get(t, 0.0) + pt * sum(po * pbeat(t, o) for o, po in dist_x.items())
            adv[key] = out
    return adv


def _target_path(bracket: dict[str, list[Slot]], target: str) -> list[Slot]:
    """Slots ``target`` would occupy from its leaf up to the Final, or [] if the
    team isn't in the bracket."""
    present = [r for r in ROUNDS if r in bracket]
    leaf = next(
        (s for r in present[:1] for s in bracket[r] if target in (s.team_a, s.team_b)),
        None,
    )
    if leaf is None:
        return []
    path = [leaf]
    cur = leaf
    while cur.feeds_into is not None:
        prnd, pidx = cur.feeds_into
        cur = bracket[prnd][pidx]
        path.append(cur)
    return path


def target_path(bracket: dict[str, list[Slot]], target: str) -> list[Slot]:
    """Public wrapper: the slots ``target`` would occupy from its leaf up to the
    Final, or [] if the team isn't in the bracket. The first element is the
    team's leaf (R32) slot."""
    return _target_path(bracket, target)


def reach_probabilities(bracket: dict[str, list[Slot]], odds, target: str, adv=None) -> dict[str, float]:
    """{"R16","QF","SF","F","champion"} -> probability target reaches that round.

    reach(R) = P(target wins its tie in the round below). Monotonic
    non-increasing across rounds (asserted)."""
    keys = ["R16", "QF", "SF", "F", "champion"]
    out = {k: 0.0 for k in keys}
    path = _target_path(bracket, target)
    if not path:
        return out
    if adv is None:
        adv = advance_distributions(bracket, odds)
    # Walk the path leaf -> final; each step is winning one more tie, so the
    # probabilities are non-increasing along the path the team actually takes.
    seq = []
    for slot in path:
        p = adv.get((slot.round, slot.index), {}).get(target, 0.0)
        out[NEXT_ROUND[slot.round]] = p
        seq.append(p)
    for earlier, later in zip(seq, seq[1:]):
        assert later <= earlier + 1e-9, f"reach not monotonic for {target}: {seq}"
    return out


def opponent_distribution(bracket: dict[str, list[Slot]], odds, target: str, round: str, adv=None) -> dict[str, float]:
    """{team: P(team is target's opponent in `round` | target reaches it)}.

    Sums to ~1. For the target's leaf round the opponent is the single other
    team in the tie. For later rounds it's the advance distribution of the
    sibling sub-bracket — the only teams that can meet the target there."""
    path = _target_path(bracket, target)
    if not path:
        return {}
    slot = next((s for s in path if s.round == round), None)
    if slot is None:
        return {}

    present = [r for r in ROUNDS if r in bracket]
    leaf_round = present[0] if present else None
    kids = CHILDREN.get((slot.round, slot.index), [])
    if slot.round == leaf_round or not kids:
        # Leaf tie: the opponent is simply the other listed team.
        other = slot.team_b if slot.team_a == target else slot.team_a
        return {other: 1.0} if other else {}

    target_child = next((s for s in path if (s.round, s.index) in kids), None)
    sibling = next((k for k in kids if target_child is None or k != (target_child.round, target_child.index)), None)
    if sibling is None:
        return {}
    if adv is None:
        adv = advance_distributions(bracket, odds)
    return dict(adv.get(sibling, {}))


def title_odds(bracket: dict[str, list[Slot]], odds, adv=None) -> dict[str, float]:
    """{team: P(champion)} across the whole field. Sums to ~1 (asserted)."""
    present = [r for r in ROUNDS if r in bracket]
    if not present:
        return {}
    if adv is None:
        adv = advance_distributions(bracket, odds)
    final_round = present[-1]
    final_slots = bracket[final_round]
    out: dict[str, float] = {}
    for slot in final_slots:
        for team, p in adv.get((slot.round, slot.index), {}).items():
            out[team] = out.get(team, 0.0) + p
    total = sum(out.values())
    assert total < 1e-9 or abs(total - 1.0) < 1e-6, f"title odds sum to {total}, not 1"
    return out
