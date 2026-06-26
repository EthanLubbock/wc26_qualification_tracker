# World Cup 2026 Group Stage Tracker

A self-hosted app that follows any team's path through the 2026 FIFA World Cup group stage. Pick a team from the dropdown and get a live view of their qualification status, what each possible result means, where they sit in the third-place race, and a Monte Carlo probability of reaching the Round of 32.

**FastAPI backend · React (Vite) frontend · runs on a Raspberry Pi**

---

## Features

- **Any team, any group** — dropdown lists all 48 teams organised by group letter; switching teams triggers an immediate update
- **Live score integration** — polls ESPN's public scoreboard feed; refreshes every 90 s, drops to 20 s while the selected team's match is live
- **Scenario analysis** — shows win / draw / loss verdicts for the next match, including where the team lands in the 12-group third-place table under each outcome
- **Qualification probability** — exact calculation (no Monte Carlo) using Elo-based win/draw/loss probabilities and Poisson goal modelling, displayed as an overall percentage and a stacked breakdown by finishing position
- **Important-games requirements** — for a third-place path, names only the games whose result actually decides the team's fate and how many of them must go its way (e.g. "need at least 4 of these"), with goal-margin detail where a group has a single deciding match
- **Third-place tracker** — live ranking of all 12 groups' third-placed teams; the top 8 advance to the Round of 32
- **Offline resilience** — serves the last good fetch with a "cached" badge if ESPN is unreachable

---

## Project layout

```
wc2026-tracker/
  backend/
    main.py          FastAPI app — /api/state, /healthz, serves built frontend
    tracker.py       Standings, tiebreakers, scenario logic (stdlib only)
    odds.py          OddsProvider, NeutralOdds, EloOdds (worldcupelo.com)
    qualify.py       Exact qualification_probability + requirements engine
    test_tracker.py  Offline test suite (no network)
    requirements.txt
  frontend/
    src/
      App.jsx                 Team dropdown, polling loop, layout
      components/
        Verdict.jsx           Qualification status heading
        Likelihood.jsx        Probability bar and percentage
        Scenarios.jsx         Win/draw/loss outcome panels
        Scores.jsx            Live/upcoming match cards
        Ladder.jsx            Third-place table
      helpers.js
      styles.css
    index.html
    package.json
    vite.config.js
  wc26.service        systemd unit (template — edit paths before use)
```

The backend serves `frontend/dist/` directly, so in production it is one process on one port. In development Vite's dev server runs separately and proxies `/api` calls to the backend.

---

## How qualification works (2026 format)

The 2026 World Cup has 12 groups of 4. **The top two teams in every group qualify automatically.** In addition, **the eight best third-placed teams** (ranked by points → goal difference → goals scored → fair play → FIFA ranking) also advance, giving 32 teams in total.

The app implements the full FIFA tiebreaker chain — head-to-head record, overall goal difference, goals scored — and computes the live third-place table across all groups simultaneously.

---

## Probability model

Group-stage groups are independent (no cross-group matches), so qualification is computed **exactly** rather than sampled:

```
P(qualify) = P(win group) + P(runner-up) + P(3rd AND among the best 8 thirds)
```

1. For each unplayed match, fetch win/draw/loss probabilities and expected goal supremacy from [worldcupelo.com](https://worldcupelo.com) (keyless API), and turn the supremacy into a Poisson scoreline distribution.
2. Enumerate each group's remaining matches to get the exact distribution of that group's finishing positions and records (the full FIFA tiebreaker/thirds logic is applied per group).
3. To finish among the best 8 thirds the team needs at least *k* of the other 11 groups to produce a third with a worse record. Each such group is an independent event; "at least *k* of them" is a **Poisson-binomial** tail, computed exactly.

The result is shown as a percentage chance of qualification with a colour-coded breakdown by finishing path (win group / runner-up / via thirds / eliminated), plus the **list of games that actually decide the third-place path** and how many must go the team's way.

Set `ODDS=neutral` to use flat 40/20/40 probabilities instead of Elo (useful for testing or if worldcupelo.com is unreachable).

---

## Setup

### Requirements

- Python 3.11+
- Node 18+ (only needed to build the frontend — not needed to run a pre-built `dist/`)

### Development (two terminals)

```bash
# Backend — auto-reloads on file changes
cd backend
python3 -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8080

# Frontend — Vite dev server, proxies /api to :8080
cd frontend
npm install
npm run dev
# → open http://localhost:5173
```

### Production (single process)

Build the frontend once, then run the backend — it serves the built app and the API together.

```bash
cd frontend
npm install && npm run build
cd ..

cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8080
# → open http://localhost:8080
```

If you don't have Node available on the production machine, build `dist/` on a dev machine and copy the folder across.

### Running as a systemd service (Linux / Raspberry Pi)

Edit `wc26.service` (update `User`, `WorkingDirectory`, and `ExecStart` paths to match your setup), then:

```bash
sudo cp wc26.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now wc26.service
journalctl -u wc26.service -f
```

---

## Environment variables

| Variable | Default | Description |
|----------|---------|-------------|
| `ODDS` | `elo` | Set to `neutral` to use flat 40/20/40 probabilities instead of Elo |

---

## API

`GET /api/state?team=SCO` returns a JSON object with:

| Field | Description |
|-------|-------------|
| `target` | Selected team abbreviation |
| `group` | Group letter |
| `group_table` | Standings for the group (ordered by tiebreaker) |
| `scenarios` | Phase (`pending`/`final`), outcomes for next match, `clinched`/`dead` flags |
| `qualification` | Monte Carlo result: per-outcome fractions, `qualify`, `samples` |
| `live_thirds` | Live third-place ranking across all 12 groups |
| `cutoff` | Number of thirds that advance (8) |
| `all_teams` | Full list of teams with group (used to populate the dropdown) |
| `live` | True if the target team's match is currently in progress |
| `stale` | True if the payload is from a cached response (ESPN unreachable) |

Unknown team abbreviations return HTTP 422. Valid abbreviations are in the `all_teams` list from any successful response.

---

## Testing

```bash
cd backend
python test_tracker.py
```

The test suite runs entirely offline — no network, no API keys. It covers standings tiebreakers, `team_qualifies` edge cases (clinched early, eliminated, third-place boundary), `with_result` model cloning, odds normalisation, the Poisson-binomial tail, scoreline distributions, exact qualification bucket sums, and that the requirements engine lists only the genuinely pivotal groups.

---

## Data sources

- **Match data:** ESPN's public scoreboard feed (`site.api.espn.com/apis/site/v2/sports/soccer/fifa.world/scoreboard`) — no API key required. Completed match days are cached to `espn_cache.json` to avoid redundant requests.
- **Elo probabilities:** [worldcupelo.com](https://worldcupelo.com) `/api/match/{A}/{B}` — no API key required. Responses are cached to `elo_cache.json` for 3 hours.

Both APIs are unofficial and undocumented. If ESPN changes its feed format, the `Fetcher` class in `tracker.py` is the only place to update.

---

## Remote access (Tailscale)

If you're self-hosting on a Raspberry Pi and want to reach it from other devices:

```bash
# Install Tailscale on the Pi
curl -fsSL https://tailscale.com/install.sh | sh
sudo tailscale up

# Serve to your tailnet only (private)
sudo tailscale serve --bg 8080
# → https://<device-name>.<tailnet>.ts.net

# Or expose publicly with Funnel (enable in admin console first)
sudo tailscale funnel --bg 8080
```

---

## Licence

MIT — see [LICENSE](LICENSE).
