"""
odds.py — Per-match outcome probabilities and expected goal supremacy.

Fetches from worldcupelo.com (keyless). Falls back to NeutralOdds on any
network or lookup failure so the app stays functional offline.

No network calls at import time.
"""

from __future__ import annotations

import json
import time
import urllib.request

# ESPN abbreviation -> worldcupelo code, for known mismatches only.
# Verified 2026-06-25: all 48 WC2026 ESPN codes match worldcupelo exactly —
# ESPN uses HAI for Haiti (not HTI). Add entries here if future ESPN feed
# updates introduce a divergence.
ABBR_TO_ELO: dict[str, str] = {}

ELO_BASE_URL = "https://worldcupelo.com/api/match"
ELO_CACHE_PATH = "elo_cache.json"
ELO_TTL_SECONDS = 3 * 3600   # 3 hours — Elo barely moves intra-day
HTTP_TIMEOUT = 8


class OddsProvider:
    """Per-fixture probabilities and expected goal supremacy."""

    def match_probabilities(self, home: str, away: str) -> dict:
        """Return {"p_a": float, "p_draw": float, "p_b": float, "supremacy": float}.

        p_a + p_draw + p_b == 1.0 (normalised). p_a is the home team's win probability.
        supremacy is home team's expected goal margin (lambda_home - lambda_away).
        """
        raise NotImplementedError


class NeutralOdds(OddsProvider):
    """Offline fallback — flat probabilities, no goal supremacy."""

    def match_probabilities(self, home: str, away: str) -> dict:
        return {"p_a": 0.4, "p_draw": 0.2, "p_b": 0.4, "supremacy": 0.0}


class EloOdds(OddsProvider):
    """Fetches Elo-based probabilities from worldcupelo.com with disk caching."""

    def __init__(self, cache_path: str = ELO_CACHE_PATH, ttl: int = ELO_TTL_SECONDS):
        self._cache_path = cache_path
        self._ttl = ttl
        self._cache: dict[str, dict] = {}
        self._load()

    def _load(self) -> None:
        try:
            with open(self._cache_path) as fh:
                self._cache = json.load(fh)
        except (FileNotFoundError, json.JSONDecodeError):
            self._cache = {}

    def _save(self) -> None:
        try:
            with open(self._cache_path, "w") as fh:
                json.dump(self._cache, fh)
        except OSError:
            pass

    def _resolve(self, abbr: str) -> str:
        return ABBR_TO_ELO.get(abbr, abbr)

    @staticmethod
    def _oriented(data: dict, swapped: bool) -> dict:
        """``data`` is always stored for the canonical (sorted) team order. Flip
        it back to the caller's requested (home, away) order when that's the
        reverse of canonical — p_a/p_b swap and supremacy (home's expected goal
        margin) negates; p_draw is symmetric."""
        if not swapped:
            return dict(data)
        return {
            "p_a": data["p_b"], "p_b": data["p_a"],
            "p_draw": data["p_draw"], "supremacy": -data["supremacy"],
        }

    def match_probabilities(self, home: str, away: str) -> dict:
        code_a = self._resolve(home)
        code_b = self._resolve(away)
        canon_a, canon_b = sorted([code_a, code_b])
        key = f"{canon_a}_{canon_b}"
        swapped = code_a != canon_a   # requested order is the reverse of canonical

        entry = self._cache.get(key)
        if entry and (time.time() - entry.get("ts", 0)) < self._ttl:
            return self._oriented(entry["data"], swapped)

        try:
            # Always fetch in canonical order so a later call for the same pair
            # in the opposite order can reuse this entry (re-oriented on read)
            # instead of triggering a second, redundant fetch.
            url = f"{ELO_BASE_URL}/{canon_a}/{canon_b}"
            req = urllib.request.Request(url, headers={"User-Agent": "wc-tracker/1.0"})
            with urllib.request.urlopen(req, timeout=HTTP_TIMEOUT) as resp:
                raw = json.loads(resp.read().decode("utf-8"))

            probs = raw["probabilities"]
            p_a = probs["teamAWin"]
            p_draw = probs["draw"]
            p_b = probs["teamBWin"]
            total = p_a + p_draw + p_b
            if total <= 0:
                raise ValueError("zero total probability")

            result = {
                "p_a": p_a / total,
                "p_draw": p_draw / total,
                "p_b": p_b / total,
                "supremacy": raw["expectedSupremacy"],
            }
            self._cache[key] = {"data": result, "ts": time.time()}
            self._save()
            return self._oriented(result, swapped)

        except Exception as exc:
            import warnings
            warnings.warn(f"EloOdds: falling back to neutral for {home} v {away}: {exc}")
            return NeutralOdds().match_probabilities(home, away)
