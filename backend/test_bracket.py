"""
test_bracket.py — offline tests for the knockout probability engine.

Run: python3 test_bracket.py  (no network; stub odds only)
"""

from types import SimpleNamespace

import bracket
from bracket import (
    Slot, build_bracket, advance_probability, advance_distributions,
    reach_probabilities, opponent_distribution, title_odds,
)


class StubOdds:
    """match_probabilities driven by a strength map; no draw mass unless given.
    P(a beats b) = s[a] / (s[a] + s[b])."""

    def __init__(self, strengths=None, draw=0.0):
        self.s = strengths or {}
        self.draw = draw

    def match_probabilities(self, a, b):
        sa, sb = self.s.get(a, 1.0), self.s.get(b, 1.0)
        scale = 1.0 - self.draw
        tot = sa + sb
        return {"p_a": scale * sa / tot, "p_draw": self.draw,
                "p_b": scale * sb / tot, "supremacy": 0.0}


def approx(x, y, tol=1e-9):
    return abs(x - y) <= tol


# --- toy 4-team bracket: 2 semis -> final ---------------------------------

def toy_bracket():
    return {
        "SF": [
            Slot(round="SF", index=0, team_a="A", team_b="B", feeds_into=("F", 0)),
            Slot(round="SF", index=1, team_a="C", team_b="D", feeds_into=("F", 0)),
        ],
        "F": [Slot(round="F", index=0)],
    }


def test_toy_hand_computed():
    odds = StubOdds({"A": 3, "B": 1, "C": 1, "D": 1})
    b = toy_bracket()
    adv = advance_distributions(b, odds)

    # SF0: A 3/4, B 1/4 ; SF1: C 1/2, D 1/2
    assert approx(adv[("SF", 0)]["A"], 0.75)
    assert approx(adv[("SF", 0)]["B"], 0.25)
    assert approx(adv[("SF", 1)]["C"], 0.5)

    champ = adv[("F", 0)]
    assert approx(champ["A"], 9 / 16), champ        # 0.5625
    assert approx(champ["B"], 1 / 8), champ          # 0.125
    assert approx(champ["C"], 5 / 32), champ         # 0.15625
    assert approx(champ["D"], 5 / 32), champ
    assert approx(sum(champ.values()), 1.0)

    rA = reach_probabilities(b, odds, "A", adv)
    assert approx(rA["F"], 0.75), rA
    assert approx(rA["champion"], 9 / 16), rA

    # opponent in the final is whoever wins the other semi
    of = opponent_distribution(b, odds, "A", "F", adv)
    assert approx(of.get("C", 0), 0.5) and approx(of.get("D", 0), 0.5), of
    assert approx(sum(of.values()), 1.0)
    # opponent in the semi is the other listed team, with certainty
    os = opponent_distribution(b, odds, "A", "SF", adv)
    assert os == {"B": 1.0}, os
    print("toy 4-team hand-computed reach/champion/opponents: PASS")


def test_no_draw_split():
    odds = StubOdds(draw=0.2)   # equal strengths, 20% draw mass
    adv_a, adv_b = advance_probability(odds, "X", "Y")
    assert approx(adv_a + adv_b, 1.0), (adv_a, adv_b)
    # both teams get a share of the draw mass (0.4 -> 0.5 with 0.5 split)
    assert adv_a > 0.4 and adv_b > 0.4, (adv_a, adv_b)
    print("no-draw split sums to 1, both share p_draw: PASS")


def test_anchoring():
    odds = StubOdds({"A": 3, "B": 1, "C": 1, "D": 1})
    b = toy_bracket()
    b["SF"][0].winner = "A"          # decided tie
    adv = advance_distributions(b, odds)
    assert adv[("SF", 0)] == {"A": 1.0}, adv[("SF", 0)]   # winner -> 1
    assert "B" not in adv[("F", 0)]                       # loser -> 0 upward
    rA = reach_probabilities(b, odds, "A", adv)
    assert approx(rA["F"], 1.0), rA
    rB = reach_probabilities(b, odds, "B", adv)
    assert approx(rB["F"], 0.0), rB
    print("anchoring short-circuits decided ties (loser->0, winner->1): PASS")


# --- full 32-team tree via build_bracket ----------------------------------

def fake_r32():
    """16 R32 fixtures pairing T00..T31, in bracket order."""
    return [
        SimpleNamespace(round="R32", home=f"T{2 * i:02d}", away=f"T{2 * i + 1:02d}",
                        winner=None, kickoff="", order=i)
        for i in range(16)
    ]


def test_full_tree_equal_strength():
    matches = fake_r32()
    valid = {f"T{i:02d}" for i in range(32)}
    b = build_bracket(matches, valid)
    odds = StubOdds()            # all equal -> every tie 50/50
    adv = advance_distributions(b, odds)

    todds = title_odds(b, odds, adv)
    assert len(todds) == 32, len(todds)
    assert approx(sum(todds.values()), 1.0, 1e-6), sum(todds.values())
    for t, p in todds.items():
        assert approx(p, 1 / 32, 1e-9), (t, p)   # symmetric tree

    # monotonicity + opponent distributions sum to ~1 for every team
    keys = ["R16", "QF", "SF", "F", "champion"]
    for t in valid:
        r = reach_probabilities(b, odds, t, adv)   # asserts monotonic internally
        seq = [r[k] for k in keys]
        assert seq == sorted(seq, reverse=True), (t, seq)
        for rnd in ("R16", "QF", "SF", "F"):
            od = opponent_distribution(b, odds, t, rnd, adv)
            assert approx(sum(od.values()), 1.0, 1e-9), (t, rnd, sum(od.values()))
    print("full 32-team tree: title odds sum 1, all champions 1/32, monotonic, opp sums 1: PASS")


def test_build_bracket_filters_placeholders():
    # higher-round competitors with placeholder codes are dropped, winners anchored
    matches = fake_r32()
    matches[0].winner = "T00"     # R32 #1 decided
    matches.append(SimpleNamespace(round="R16", home="T00", away="Round of 32 3 Winner",
                                   winner=None, kickoff="", order=100))
    valid = {f"T{i:02d}" for i in range(32)}
    b = build_bracket(matches, valid)
    leaf = b["R32"][0]
    assert leaf.winner == "T00", leaf
    r16 = b["R16"][0]
    assert r16.team_a == "T00" and r16.team_b is None, r16   # placeholder -> None
    print("build_bracket fills real teams, drops placeholders, records winners: PASS")


if __name__ == "__main__":
    test_toy_hand_computed()
    test_no_draw_split()
    test_anchoring()
    test_full_tree_equal_strength()
    test_build_bracket_filters_placeholders()
    print("\nAll bracket assertions passed.")
