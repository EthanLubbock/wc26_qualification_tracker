"""Offline checks for the standings + scenario maths (no network)."""
from tracker import Match, WorldCupModel, analyse

def M(group, h, a, hs, as_, finished=True, state="post"):
    return Match(group=group, home=h, away=a, home_score=hs, away_score=as_,
                 state=state if finished else "pre", completed=finished,
                 kickoff="", home_name=h, away_name=a)

# Group C — rounds 1 & 2 played, round 3 (SCO-BRA, MAR-HTI) still to come.
matches = [
    M("C", "HTI", "SCO", 0, 1), M("C", "BRA", "MAR", 1, 1),
    M("C", "BRA", "HTI", 3, 0), M("C", "MAR", "SCO", 1, 0),
    M("C", "SCO", "BRA", None, None, finished=False),
    M("C", "MAR", "HTI", None, None, finished=False),
]
# Four other finished groups whose 3rd-placed teams sit around Scotland's range.
matches += [
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

model = WorldCupModel(matches)
state = analyse(model)

# Group C order check
order = [t["abbr"] for t in state["group_c"]]
assert order[:3] == ["BRA", "MAR", "SCO"], order        # Brazil top on GD, Scotland 3rd
print("Group C order:", order)

now = state["scotland_now"]
assert now["points"] == 3 and now["gd"] == 0, now
print("Scotland now:", now["points"], "pts, GD", now["gd"])

assert state["phase"] == "pre", state["phase"]
assert state["scenarios"]["win"]["outcome"] == "QUALIFIED"

draw = state["scenarios"]["draw"]
lose = state["scenarios"]["lose"]
assert draw["sco_points"] == 4 and draw["sco_gd"] == 0, draw
assert lose["sco_points"] == 3 and lose["sco_gd"] == -1, lose
print(f"DRAW : 4 pts, GD 0  -> rank {draw['third_rank']}/{draw['field_size']} "
      f"({'IN' if draw['in_top8'] else 'OUT'})")
print(f"LOSE : 3 pts, GD -1 -> rank {lose['third_rank']}/{lose['field_size']} "
      f"({'IN' if lose['in_top8'] else 'OUT'})")

print("\nThird-place table (draw scenario):")
for i, t in enumerate(draw["table"], 1):
    star = " <-- SCO" if t.get("is_scotland") else ""
    print(f"  {i}. {t['abbr']:>3}  {t['points']}pts  GD {t['gd']:+d}  GF {t['gf']}{star}")

print("\nAll assertions passed.")
