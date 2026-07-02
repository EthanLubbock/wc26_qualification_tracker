"""
test_bracket.py — offline tests for the knockout probability engine.

Run: python3 test_bracket.py  (no network; stub odds only)
"""

from types import SimpleNamespace

import bracket
from bracket import (
    Slot, build_bracket, advance_probability, advance_distributions,
    reach_probabilities, opponent_distribution, title_odds,
    current_knockout_round, next_games,
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


# --- fixture metadata + rolling "next games" window -----------------------

def test_build_bracket_carries_fixture_metadata():
    m = SimpleNamespace(round="R32", home="T00", away="T01", winner=None,
                        kickoff="2026-06-28T19:00Z", order=0,
                        state="post", home_score=2, away_score=1)
    b = build_bracket([m], {"T00", "T01"})
    slot = b["R32"][0]
    assert slot.state == "post" and slot.kickoff == "2026-06-28T19:00Z", slot
    assert slot.home_score == 2 and slot.away_score == 1, slot
    print("build_bracket carries kickoff/state/score onto slots: PASS")


def _wired(valid):
    """Fully wired but empty bracket (feeds_into set, all slots blank)."""
    return build_bracket([], valid)


VALID = {"ENG", "COD", "MEX", "ECU", "AAA", "BBB"}


def test_current_knockout_round():
    b = _wired(VALID)
    b["R32"][7].team_a, b["R32"][7].team_b = "ENG", "COD"     # undecided R32 tie
    assert current_knockout_round(b) == "R32", current_knockout_round(b)
    b["R32"][7].winner = "ENG"                                # now decided
    assert current_knockout_round(b) == "F", current_knockout_round(b)  # nothing else live
    # a live R16 tie now becomes the current round
    b["R16"][3].team_a, b["R16"][3].team_b = "ENG", "MEX"
    assert current_knockout_round(b) == "R16", current_knockout_round(b)
    print("current_knockout_round tracks earliest undecided real tie: PASS")


def test_next_games_concrete_and_known_opponent():
    odds = StubOdds({"ENG": 3, "COD": 1, "MEX": 1})
    b = _wired(VALID)
    b["R32"][7].team_a, b["R32"][7].team_b, b["R32"][7].state = "ENG", "COD", "pre"
    b["R32"][6].team_a, b["R32"][6].team_b = "MEX", "ECU"
    b["R32"][6].winner, b["R32"][6].state = "MEX", "post"     # sibling decided
    b["R16"][3].state = "pre"                                 # R16 placeholder fixture exists

    games = next_games(b, odds, "ENG")
    assert len(games) == 2, games
    g1, g2 = games
    # current-round game: concrete ENG v COD, upcoming -> odds present, summing ~1
    assert g1["round"] == "R32" and g1["winner"] is None
    a, c = g1["sides"]
    assert {a["abbr"], c["abbr"]} == {"ENG", "COD"}
    assert approx(a["win_pct"] + c["win_pct"], 1.0), g1
    assert next(s for s in g1["sides"] if s["abbr"] == "ENG")["is_target"]
    # next-round game: opponent known (MEX won its tie), upcoming -> odds present
    assert g2["round"] == "R16"
    abbrs = {s["abbr"] for s in g2["sides"]}
    assert abbrs == {"ENG", "MEX"}, g2
    assert all(s["win_pct"] is not None for s in g2["sides"]), g2
    print("next_games: concrete current tie + known next opponent, both with odds: PASS")


def test_next_games_placeholder_opponent():
    odds = StubOdds({"ENG": 2, "COD": 1})
    b = _wired(VALID)
    b["R32"][7].team_a, b["R32"][7].team_b, b["R32"][7].state = "ENG", "COD", "pre"
    b["R32"][6].team_a, b["R32"][6].team_b, b["R32"][6].state = "MEX", "ECU", "pre"  # sibling open
    b["R16"][3].state = "pre"

    games = next_games(b, odds, "ENG")
    assert len(games) == 2, games
    g2 = games[1]
    tgt = next(s for s in g2["sides"] if not s.get("placeholder"))
    ph = next(s for s in g2["sides"] if s.get("placeholder"))
    assert tgt["abbr"] == "ENG" and tgt["is_target"], g2
    assert sorted(ph["candidates"]) == ["ECU", "MEX"], ph
    assert ph["win_pct"] is None and tgt["win_pct"] is None, g2   # no odds vs unknown side
    print("next_games: undecided next opponent -> placeholder with feeding teams, no odds: PASS")


def test_next_games_elimination_guard():
    odds = StubOdds()
    b = _wired(VALID)
    b["R32"][0].team_a, b["R32"][0].team_b, b["R32"][0].state = "AAA", "BBB", "pre"  # keeps round live
    b["R32"][7].team_a, b["R32"][7].team_b = "ENG", "COD"
    b["R32"][7].winner, b["R32"][7].state = "COD", "post"     # ENG lost its current tie
    b["R32"][7].home_score, b["R32"][7].away_score = 0, 1

    games = next_games(b, odds, "ENG")
    assert len(games) == 1, games                            # no next game once out
    assert games[0]["round"] == "R32" and games[0]["winner"] == "COD", games
    print("next_games: eliminated in current round -> single (losing) game only: PASS")


if __name__ == "__main__":
    test_toy_hand_computed()
    test_no_draw_split()
    test_anchoring()
    test_full_tree_equal_strength()
    test_build_bracket_filters_placeholders()
    test_build_bracket_carries_fixture_metadata()
    test_current_knockout_round()
    test_next_games_concrete_and_known_opponent()
    test_next_games_placeholder_opponent()
    test_next_games_elimination_guard()
    print("\nAll bracket assertions passed.")
