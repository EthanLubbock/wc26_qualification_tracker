"""Offline checks for the standings, classifier, and scenario maths (no network)."""
from tracker import (
    Match, WorldCupModel, analyse, team_qualifies, with_result,
    QUALIFY_OUTCOMES, THIRDS_ADVANCING, target_scenarios,
)


def M(group, h, a, hs, as_, finished=True, state="post"):
    return Match(
        group=group, home=h, away=a, home_score=hs, away_score=as_,
        state=state if finished else "pre", completed=finished,
        kickoff="", home_name=h, away_name=a,
    )


# ---------------------------------------------------------------------------
# Fixture A: Group C — rounds 1 & 2 played, round 3 (SCO-BRA, MAR-HAI) TBD.
# ---------------------------------------------------------------------------

matches_a = [
    M("C", "HAI", "SCO", 0, 1), M("C", "BRA", "MAR", 1, 1),
    M("C", "BRA", "HAI", 3, 0), M("C", "MAR", "SCO", 1, 0),
    M("C", "SCO", "BRA", None, None, finished=False),
    M("C", "MAR", "HAI", None, None, finished=False),
]
# Four other finished groups whose 3rd-placed teams sit around Scotland's range.
matches_a += [
    # Group D third on 4 pts, GD +1
    M("D", "USA", "AUS", 2, 0), M("D", "PAR", "TUR", 2, 1), M("D", "USA", "PAR", 1, 0),
    M("D", "AUS", "TUR", 3, 1), M("D", "USA", "TUR", 2, 1), M("D", "AUS", "PAR", 1, 2),
    # Group E third on 3 pts, GD -1
    M("E", "GER", "CIV", 2, 0), M("E", "ECU", "CUW", 1, 1), M("E", "GER", "ECU", 2, 1),
    M("E", "CIV", "CUW", 2, 1), M("E", "GER", "CUW", 3, 0), M("E", "CIV", "ECU", 1, 0),
    # Group F third on 4 pts, GD 0
    M("F", "NED", "JPN", 1, 1), M("F", "SWE", "TUN", 2, 1), M("F", "NED", "SWE", 2, 1),
    M("F", "JPN", "TUN", 1, 0), M("F", "NED", "TUN", 2, 0), M("F", "JPN", "SWE", 0, 1),
    # Group G third on 2 pts
    M("G", "EGY", "IRN", 1, 1), M("G", "BEL", "NZL", 1, 1), M("G", "EGY", "BEL", 1, 0),
    M("G", "IRN", "NZL", 0, 0), M("G", "EGY", "NZL", 2, 0), M("G", "IRN", "BEL", 1, 1),
]

model_a = WorldCupModel(matches_a)
state_a = analyse(model_a, "SCO")

order_a = [t["abbr"] for t in state_a["group_table"]]
assert order_a[:3] == ["BRA", "MAR", "SCO"], order_a
print("Group C order:", order_a)

sco_now = model_a.teams["SCO"]
assert sco_now.points == 3 and sco_now.gd == 0, (sco_now.points, sco_now.gd)
print("Scotland now:", sco_now.points, "pts, GD", sco_now.gd)

assert state_a["scenarios"]["phase"] == "pending"
# With only 5 groups in the fixture (< 8 advancing), all thirds qualify; clinched is expected True.
assert state_a["scenarios"]["clinched"], state_a["scenarios"]
assert not state_a["scenarios"]["dead"]

sc_a = state_a["scenarios"]["outcomes"]
assert sc_a["win"]["verdict"] == "win_group", sc_a["win"]
# Draw / loss both resolve to 3rd (only 5 groups, so always third_in)
assert sc_a["draw"]["verdict"] == "third_in", sc_a["draw"]
assert sc_a["loss"]["verdict"] == "third_in", sc_a["loss"]

print(f"WIN : {sc_a['win']['verdict']}")
print(f"DRAW: {sc_a['draw']['verdict']} (rank {sc_a['draw']['third_rank']})")
print(f"LOSS: {sc_a['loss']['verdict']} (rank {sc_a['loss']['third_rank']})")

print("Fixture A: PASS\n")


# ---------------------------------------------------------------------------
# Fixture B: team_qualifies — clinched early (BRA 6 pts, pending match).
# ---------------------------------------------------------------------------

matches_b = [
    M("X", "BRA", "ARG", 2, 0),
    M("X", "POR", "URU", 1, 1),
    M("X", "BRA", "POR", 3, 1),
    M("X", "ARG", "URU", 2, 0),
    M("X", "BRA", "URU", None, None, finished=False),
    M("X", "ARG", "POR", None, None, finished=False),
]
matches_b += [
    M("Y", "A1", "A2", 1, 0), M("Y", "A3", "A4", 0, 0),
    M("Y", "A1", "A3", 2, 1), M("Y", "A2", "A4", 1, 0),
    M("Y", "A1", "A4", 1, 1), M("Y", "A2", "A3", 0, 1),
]
model_b = WorldCupModel(matches_b)
bra_result = team_qualifies(model_b, "BRA")
assert bra_result in ("win_group", "runner_up"), bra_result
print(f"Fixture B — BRA clinched (pending match): {bra_result}")

sc_b = target_scenarios(model_b, "BRA")
assert sc_b["phase"] == "pending"
assert sc_b["clinched"], sc_b
print("BRA scenarios.clinched:", sc_b["clinched"])
print("Fixture B: PASS\n")


# ---------------------------------------------------------------------------
# Fixture C: team_qualifies — mathematically eliminated (4th, 0 pts, all played).
# ---------------------------------------------------------------------------

matches_c = [
    M("Z", "ESP", "GER", 2, 0), M("Z", "FRA", "ARG", 1, 1),
    M("Z", "ESP", "FRA", 2, 1), M("Z", "GER", "ARG", 3, 0),
    M("Z", "ESP", "ARG", 3, 0), M("Z", "GER", "FRA", 1, 0),
]
model_c = WorldCupModel(matches_c)
arg_result = team_qualifies(model_c, "ARG")
assert arg_result == "fourth_out", arg_result

sc_c = target_scenarios(model_c, "ARG")
assert sc_c["phase"] == "final"
assert sc_c["verdict"] == "fourth_out"
print(f"Fixture C — ARG (0 pts, fully played): {arg_result}")
print("Fixture C: PASS\n")


# ---------------------------------------------------------------------------
# Fixture D: with_result boundary — draw => third_in, loss => third_out.
#
# TGT group (P) after R1+R2:
#   R1: CHAMP 2-1 A,  TGT 2-1 WEAK
#   R2: A 2-0 WEAK,   CHAMP 2-1 TGT
#   → CHAMP 6pts, A 3pts GD+1, TGT 3pts GD 0, WEAK 0pts
#   → H2H A vs TGT not yet played; A ranks 2nd on overall GD, TGT 3rd.
# Pending R3: A vs TGT (A home, TGT away), CHAMP vs WEAK.
#
# After draw (A 1-1 TGT):
#   TGT 4pts GD 0 GF 4; A 4pts GD+1; H2H draw → overall GD decides → A 2nd, TGT 3rd.
# After loss (A 1-0 TGT):
#   TGT 3pts GD -1; A 6pts; CHAMP 6pts (H2H: CHAMP beat A R1) → CHAMP 1st, A 2nd, TGT 3rd.
#
# Other 11 groups' thirds:
#   7 at (4pts, GD 0, GF 5)  → all better than TGT-draw (4pts GD 0 GF 4)
#   4 at (3pts, GD 0, GF 2)  → all better than TGT-loss  (3pts GD-1 GF 3)
#
# Thirds table on draw:  7 above + TGT = rank 8 → third_in  (rank ≤ 8)
# Thirds table on loss:  7 above + 4 above + TGT = rank 12 → third_out (rank > 8)
# ---------------------------------------------------------------------------

def _strong_third(g):
    """Group where 3rd finishes 4pts, GD 0, GF 5: W 4-1 L, D 1-1 R, L 0-3 W."""
    return [
        M(g, f"{g}W", f"{g}R", 3, 0), M(g, f"{g}T", f"{g}L", 4, 1),
        M(g, f"{g}W", f"{g}T", 3, 0), M(g, f"{g}R", f"{g}L", 2, 0),
        M(g, f"{g}T", f"{g}R", 1, 1), M(g, f"{g}W", f"{g}L", 2, 0),
    ]

def _moderate_third(g):
    """Group where 3rd finishes 3pts, GD 0, GF 2: W 2-0 L, L 0-1 W, L 0-1 R."""
    return [
        M(g, f"{g}W", f"{g}R", 3, 0), M(g, f"{g}T", f"{g}L", 2, 0),
        M(g, f"{g}W", f"{g}T", 1, 0), M(g, f"{g}R", f"{g}L", 2, 0),
        M(g, f"{g}T", f"{g}R", 0, 1), M(g, f"{g}W", f"{g}L", 2, 0),
    ]

matches_d = [
    # Group P — TGT's group
    M("P", "CHAMP", "A",    2, 1),   # R1
    M("P", "TGT",   "WEAK", 2, 1),   # R1
    M("P", "A",     "WEAK", 2, 0),   # R2
    M("P", "CHAMP", "TGT",  2, 1),   # R2 — TGT 3pts GD 0
    M("P", "A",     "TGT",  None, None, finished=False),   # R3 pending — A home, TGT away
    M("P", "CHAMP", "WEAK", None, None, finished=False),   # R3 pending
]
for i in range(1, 8):
    matches_d += _strong_third(f"S{i}")    # 7 strong thirds at 4pts GD 0 GF 5
for i in range(1, 5):
    matches_d += _moderate_third(f"M{i}") # 4 moderate thirds at 3pts GD 0 GF 2
# Total: P + S1..S7 + M1..M4 = 12 groups ✓

model_d = WorldCupModel(matches_d)

# Verify TGT is 3rd after R1+R2
order_p = [t.abbr for t in model_d.groups()["P"]]
assert order_p[2] == "TGT", f"Expected TGT 3rd, got {order_p}"

pending_d = next(m for m in model_d.matches
                 if not m.finished and "TGT" in (m.home, m.away))
assert pending_d.home == "A" and pending_d.away == "TGT", pending_d

# Draw: A 1-1 TGT (home_goals=1, away_goals=1 from with_result perspective)
draw_model_d = with_result(model_d, pending_d, 1, 1)
# Loss: A 1-0 TGT (ASSUMED_MARGIN=1, A wins as home team)
loss_model_d = with_result(model_d, pending_d, 1, 0)

draw_v = team_qualifies(draw_model_d, "TGT")
loss_v = team_qualifies(loss_model_d, "TGT")
print(f"Fixture D — TGT: draw={draw_v}, loss={loss_v}")
assert draw_v == "third_in",  f"Expected third_in, got {draw_v}"
assert loss_v == "third_out", f"Expected third_out, got {loss_v}"
print("Fixture D: PASS\n")


# ---------------------------------------------------------------------------
# Fixture E: fully played group — phase=="final" for all four teams.
# ---------------------------------------------------------------------------

matches_e = [
    M("F2", "ENG", "ITA", 2, 1), M("F2", "NED", "BEL", 1, 1),
    M("F2", "ENG", "NED", 1, 0), M("F2", "ITA", "BEL", 2, 0),
    M("F2", "ENG", "BEL", 3, 0), M("F2", "ITA", "NED", 0, 1),
]
model_e = WorldCupModel(matches_e)
sc_eng = target_scenarios(model_e, "ENG")
sc_bel = target_scenarios(model_e, "BEL")
assert sc_eng["phase"] == "final"
assert sc_bel["phase"] == "final"
assert sc_eng["verdict"] == "win_group", sc_eng
assert sc_bel["verdict"] == "fourth_out", sc_bel
print(f"Fixture E — ENG: {sc_eng['verdict']}, BEL: {sc_bel['verdict']}")

for abbr in ("ENG", "ITA", "NED", "BEL"):
    v = team_qualifies(model_e, abbr)
    assert v in QUALIFY_OUTCOMES, (abbr, v)
print("Fixture E: PASS\n")


# ---------------------------------------------------------------------------
# Odds tests (no network — use a stub / NeutralOdds).
# ---------------------------------------------------------------------------

from odds import NeutralOdds, EloOdds

neutral = NeutralOdds()
p = neutral.match_probabilities("SCO", "BRA")
assert abs(p["p_a"] + p["p_draw"] + p["p_b"] - 1.0) < 1e-9, p
assert p["supremacy"] == 0.0
print("NeutralOdds probs sum to 1: PASS")

# Stub EloOdds with a pre-populated cache (no real network call needed).
import tempfile, os
elo = EloOdds(cache_path=os.path.join(tempfile.gettempdir(), "test_elo_cache.json"))
# Inject a fake cache entry directly.
elo._cache["ESP_GER"] = {
    "data": {"p_a": 0.6, "p_draw": 0.2, "p_b": 0.2, "supremacy": 0.8},
    "ts": 9999999999.0,   # far future — won't expire
}
p2 = elo.match_probabilities("ESP", "GER")   # canonical key = ESP_GER
assert abs(p2["p_a"] + p2["p_draw"] + p2["p_b"] - 1.0) < 1e-9, p2
assert p2["supremacy"] == 0.8
print("EloOdds cache hit works: PASS")

# Unknown code falls back to NeutralOdds (no crash).
p3 = elo.match_probabilities("FAKE1", "FAKE2")
assert abs(p3["p_a"] + p3["p_draw"] + p3["p_b"] - 1.0) < 1e-9, p3
print("EloOdds unknown code falls back gracefully: PASS")


# ---------------------------------------------------------------------------
# Simulate tests (fixed seed, small n).
# ---------------------------------------------------------------------------

import random as _random
from simulate import qualification_probability, QUALIFY_OUTCOMES as SIM_OUTCOMES

_random.seed(42)

# Team that has already qualified (no unplayed matches) — deterministic result.
sim_result = qualification_probability(model_e, "ENG", NeutralOdds(), n=100)
assert sim_result["qualify"] == 1.0, sim_result
assert abs(sum(sim_result[k] for k in SIM_OUTCOMES) - 1.0) < 1e-9, sim_result
assert sim_result["samples"] == 100
print(f"Simulate: ENG (won group, no unplayed) qualify={sim_result['qualify']}: PASS")

# Buckets sum to 1 with unplayed matches.
_random.seed(42)
sim_sco = qualification_probability(model_a, "SCO", NeutralOdds(), n=200)
assert abs(sum(sim_sco[k] for k in SIM_OUTCOMES) - 1.0) < 1e-9, sim_sco
assert 0.0 <= sim_sco["qualify"] <= 1.0
print(f"Simulate: SCO (pending) qualify~={sim_sco['qualify']:.2f}, buckets sum to 1: PASS")

# collect callback is invoked.
collected = []
_random.seed(42)
qualification_probability(model_a, "SCO", NeutralOdds(), n=10,
                          collect=lambda sim, t: collected.append(t))
assert len(collected) == 10
print("Simulate: collect callback invoked 10 times: PASS")


print("\nAll assertions passed.")
