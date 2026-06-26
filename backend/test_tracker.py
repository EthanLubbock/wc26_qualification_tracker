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
# Qualification engine tests (exact, deterministic — no Monte Carlo).
# ---------------------------------------------------------------------------

from qualify import (
    qualification_probability, _pb_at_least, _match_scoreline_dist,
    QUALIFY_OUTCOMES as SIM_OUTCOMES,
)


# Poisson-binomial tail: known small cases.
assert _pb_at_least([], 0) == 1.0
assert _pb_at_least([0.5, 0.5], 0) == 1.0
assert abs(_pb_at_least([0.5, 0.5], 1) - 0.75) < 1e-12       # P(>=1) = 1 - .25
assert abs(_pb_at_least([0.5, 0.5], 2) - 0.25) < 1e-12       # both succeed
assert _pb_at_least([0.5, 0.5], 3) == 0.0                    # k > n
assert abs(_pb_at_least([0.2, 0.3, 0.4], 1)
           - (1 - 0.8 * 0.7 * 0.6)) < 1e-12
print("Poisson-binomial tail: PASS")


# Per-match scoreline distribution sums to 1; supremacy shifts the expected margin.
class _StubOdds:
    def __init__(self, sup):
        self.sup = sup
    def match_probabilities(self, home, away):
        return {"p_a": 0.4, "p_draw": 0.2, "p_b": 0.4, "supremacy": self.sup}

_m = M("Z", "HH", "AA", None, None, finished=False)
d_even = _match_scoreline_dist(_StubOdds(0.0), _m)
d_home = _match_scoreline_dist(_StubOdds(1.5), _m)
assert abs(sum(d_even.values()) - 1.0) < 1e-9
assert abs(sum(d_home.values()) - 1.0) < 1e-9
exp_margin = lambda d: sum((hg - ag) * p for (hg, ag), p in d.items())
assert abs(exp_margin(d_even)) < 1e-6, exp_margin(d_even)
assert exp_margin(d_home) > 0.9, exp_margin(d_home)   # home supremacy → positive margin
print("Scoreline distribution: PASS")


# Team already qualified (won group, no unplayed) — deterministic, exact.
q_eng = qualification_probability(model_e, "ENG", NeutralOdds())
assert q_eng["qualify"] == 1.0, q_eng
assert q_eng["win_group"] == 1.0, q_eng
assert abs(sum(q_eng[k] for k in SIM_OUTCOMES) - 1.0) < 1e-9, q_eng
assert q_eng["requirements"] is None, q_eng       # no third-place decision
print(f"Qualify: ENG (won group) qualify={q_eng['qualify']}, requirements=None: PASS")


# Eliminated team — qualify 0, no requirements.
q_arg = qualification_probability(model_c, "ARG", NeutralOdds())
assert q_arg["qualify"] == 0.0, q_arg
assert q_arg["fourth_out"] == 1.0, q_arg
print(f"Qualify: ARG (eliminated) qualify={q_arg['qualify']}: PASS")


# Buckets sum to 1 with unplayed matches (SCO pending).
q_sco = qualification_probability(model_a, "SCO", NeutralOdds())
assert abs(sum(q_sco[k] for k in SIM_OUTCOMES) - 1.0) < 1e-9, q_sco
assert abs(q_sco["qualify"]
           - (q_sco["win_group"] + q_sco["runner_up"] + q_sco["third_in"])) < 1e-12
assert 0.0 <= q_sco["qualify"] <= 1.0
# Only 5 groups in fixture A → fewer than THIRDS_ADVANCING thirds, so any 3rd is in.
assert q_sco["third_out"] < 1e-9, q_sco
print(f"Qualify: SCO (pending) qualify={q_sco['qualify']:.3f}, buckets sum to 1: PASS")


# ---------------------------------------------------------------------------
# Fixture F: third-place requirements name only the pivotal group.
#
# TGT has finished 3rd in group P3 on 3 pts, GD 0, GF 2. Of the other 11 groups
# (12 total), 10 are complete with thirds already BELOW TGT (settled-favourable),
# and ONE group still has its final match to play and decides whether its third
# finishes above or below TGT. With cutoff 8 and 11 other groups, k = 4. Ten
# settled-below leaves need = 0 here — but the contested group must still appear
# in requirements.groups, while the settled groups must NOT.
# ---------------------------------------------------------------------------

def _weak_complete_third(g):
    """Complete group whose 3rd finishes 1 pt, GD -3, GF 1 (well below TGT)."""
    return [
        M(g, f"{g}W", f"{g}R", 3, 0), M(g, f"{g}T", f"{g}L", 1, 1),
        M(g, f"{g}W", f"{g}T", 2, 0), M(g, f"{g}R", f"{g}L", 2, 0),
        M(g, f"{g}T", f"{g}R", 0, 2), M(g, f"{g}W", f"{g}L", 2, 0),
    ]

matches_f = [
    # Group P3 — TGT finished 3rd on 3 pts, GD 0, GF 2.
    M("P3", "WIN", "TGT", 2, 1), M("P3", "TWO", "LOW", 1, 0),
    M("P3", "WIN", "TWO", 1, 0), M("P3", "TGT", "LOW", 1, 0),
    M("P3", "WIN", "LOW", 3, 0), M("P3", "TWO", "TGT", 1, 0),
    # One contested group Q3 — final match CON vs DEC still to play; its third's
    # fate vs TGT depends on that result.
    M("Q3", "QA", "QB", 2, 0), M("Q3", "QC", "QD", 0, 0),
    M("Q3", "QA", "QC", 1, 0), M("Q3", "QB", "QD", 2, 0),
    M("Q3", "QA", "QD", 2, 0),
    M("Q3", "QB", "QC", None, None, finished=False),
]
for i in range(1, 11):
    matches_f += _weak_complete_third(f"W{i}")   # 10 settled-below thirds

model_f = WorldCupModel(matches_f)
assert [t.abbr for t in model_f.groups()["P3"]][2] == "TGT", model_f.groups()["P3"]

q_tgt = qualification_probability(model_f, "TGT", NeutralOdds())
req = q_tgt["requirements"]
assert req is not None, q_tgt
contested = {g["group"] for g in req["groups"]}
assert contested == {"Q3"}, contested            # only the live group is listed
assert all(not g["group"].startswith("W") for g in req["groups"])  # settled groups excluded
assert req["conditional"] is False, req          # TGT has finished playing
assert req["settled_favourable"] >= 1, req
print(f"Requirements: only contested group listed ({contested}), "
      f"settled_favourable={req['settled_favourable']}: PASS")


print("\nAll assertions passed.")
