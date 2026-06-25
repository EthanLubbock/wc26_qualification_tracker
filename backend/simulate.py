"""
simulate.py — Monte Carlo qualification probability.

Simulates unplayed group-stage matches using Poisson-distributed scorelines
derived from Elo supremacy. Calls tracker.team_qualifies() on each simulated
world to tally outcome frequencies for the target team.

Performance note: each iteration rebuilds a WorldCupModel from scratch. This
is acceptable for n=2000-5000 on modern hardware; for a Raspberry Pi 3B+ run
the Pi performance check (Checkpoint 2) and reduce DEFAULT_SAMPLES if needed.
A dict-based scorer that avoids rebuilding the model would be the next
optimisation step if latency becomes a problem.
"""

from __future__ import annotations

import math
import random
from collections import Counter

from tracker import Match, WorldCupModel, team_qualifies, QUALIFY_OUTCOMES

MEAN_TOTAL_GOALS = 2.6   # tournament average; tunable
DEFAULT_SAMPLES = 5000


def _poisson_sample(lam: float) -> int:
    """Sample from Poisson(lam) using Knuth's algorithm. Pure stdlib."""
    l = math.exp(-lam)
    k = 0
    p = 1.0
    while p > l:
        p *= random.random()
        k += 1
    return k - 1


def _sample_scoreline(p: dict) -> tuple[int, int]:
    """Return (home_goals, away_goals) sampled from Poisson means implied by supremacy."""
    S = p["supremacy"]
    lam_home = max(0.05, (MEAN_TOTAL_GOALS + S) / 2)
    lam_away = max(0.05, (MEAN_TOTAL_GOALS - S) / 2)
    return _poisson_sample(lam_home), _poisson_sample(lam_away)


def _apply_all(
    model: WorldCupModel,
    unplayed: list[Match],
    results: dict[int, tuple[int, int]],
) -> WorldCupModel:
    """Return a new WorldCupModel with all unplayed matches resolved to sampled scores."""
    unplayed_ids = {id(m) for m in unplayed}
    new_matches = []
    for m in model.matches:
        if id(m) in unplayed_ids:
            hg, ag = results[id(m)]
            new_matches.append(Match(
                group=m.group, home=m.home, away=m.away,
                home_score=hg, away_score=ag,
                state="post", completed=True,
                kickoff=m.kickoff, home_name=m.home_name, away_name=m.away_name,
            ))
        else:
            new_matches.append(m)
    return WorldCupModel(new_matches)


def qualification_probability(
    model: WorldCupModel,
    target: str,
    odds,
    n: int = DEFAULT_SAMPLES,
    collect=None,
) -> dict:
    """Estimate P(qualify) and bucket probabilities for target via Monte Carlo.

    Args:
        model:   Current WorldCupModel (finished + unplayed matches).
        target:  Team abbreviation to classify.
        odds:    OddsProvider instance (pre-warmed; never hits network inside the loop).
        n:       Number of simulations.
        collect: Optional callback(sim_model, target) called each iteration.
                 Reserved for future R32 opponent-prediction extension; pass None.

    Returns dict with QUALIFY_OUTCOMES keys + "qualify" (overall) + "samples".
    """
    unplayed = [m for m in model.matches if not m.finished]
    # Pre-fetch all odds ONCE outside the loop — must never hit network inside.
    probs = {id(m): odds.match_probabilities(m.home, m.away) for m in unplayed}

    counts: Counter = Counter()
    for _ in range(n):
        results = {id(m): _sample_scoreline(probs[id(m)]) for m in unplayed}
        sim = _apply_all(model, unplayed, results)
        outcome = team_qualifies(sim, target)
        counts[outcome] += 1
        if collect is not None:
            collect(sim, target)

    total = n
    buckets = {k: counts.get(k, 0) / total for k in QUALIFY_OUTCOMES}
    buckets["qualify"] = (
        counts.get("win_group", 0) +
        counts.get("runner_up", 0) +
        counts.get("third_in", 0)
    ) / total
    buckets["samples"] = total
    return buckets
