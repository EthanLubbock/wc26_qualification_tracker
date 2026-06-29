# World Cup 2026 Tracker

A self-hosted app that follows any team's path through the entire 2026 FIFA World Cup, from the group stage through to the Final. Pick a team from the dropdown and get a live view of their qualification status, match scenarios, knockout bracket probabilities, and whole-field title odds.

**FastAPI backend · React (Vite) frontend · runs on a Raspberry Pi**

---

## Features

### Group stage
- **Any team, any group** -- dropdown lists all 48 teams organised by group letter
- **Live score integration** -- polls ESPN's public scoreboard feed; refreshes every 90s, drops to 20s while the selected team's match is live
- **Scenario analysis** -- win / draw / loss verdicts for the next match, including where the team lands in the 12-group third-place table under each outcome
- **Qualification probability** -- exact calculation using Elo-based win/draw/loss probabilities and Poisson goal modelling, as an overall percentage with a stacked breakdown by finishing position
- **Third-place tracker** -- live ranking of all 12 groups' third-placed teams; the top 8 advance

### Knockout stage (Round of 32 onwards)
- **Route strip** -- R32 through Final, showing reach probability at each stage and a tick for already-secured rounds
- **R32 tie card** -- opponent, kickoff time or live score
- **Likely opponents** -- top 3 probable opponents per upcoming round, with percentages
- **Title odds leaderboard** -- whole-field champion probabilities for the top teams
- **Auto-switch** -- if the selected team didn't reach the knockouts, the view automatically switches to the current title favourite

---

## How it works

### Group stage qualification

The 2026 World Cup has 12 groups of 4. The top two teams per group qualify automatically. The eight best third-placed teams also advance, giving 32 in total. The app implements the full FIFA tiebreaker chain (head-to-head record, goal difference, goals scored) and computes the live third-place table across all groups simultaneously.

Qualification probability is computed exactly, not sampled:

```
P(qualify) = P(win group) + P(runner-up) + P(3rd AND among the best 8 thirds)
```

For the third-place path, "at least k of the other 11 groups must produce a worse third" is a Poisson-binomial tail computed exactly. The app also lists only the specific out-of-group games whose results actually matter and how many need to go the team's way.

### Knockout bracket

Once the group stage is complete the app switches to an exact recursive probability engine (no Monte Carlo):

- The fixed 2026 bracket tree is hardcoded from the ESPN fixture feed (which R32 ties feed which R16 tie, and so on up to the Final)
- Advance distributions are computed bottom-up: `P(team in parent slot) = P(team wins child) x sum over opponents of P(opponent in sibling) x P(team beats opponent)`
- Draws are impossible in knockout ties; the 90-minute draw probability mass is split 50/50 between the two teams (representing extra time and penalties)
- Decided ties anchor to their real-world winner (probability 1 for the winner, 0 for the loser), so displayed numbers track reality as the tournament progresses
- The same pass yields reach probabilities, opponent distributions, and title odds for every team in the field

Set `ODDS=neutral` to use flat 40/20/40 probabilities instead of Elo.

---

## Project layout

```
wc2026-tracker/
  backend/
    main.py          FastAPI app -- /api/state, /healthz, serves built frontend
    tracker.py       Standings, tiebreakers, scenario logic, knockout fixture parsing
    bracket.py       Exact knockout probability engine (pure, no network)
    odds.py          OddsProvider, NeutralOdds, EloOdds (worldcupelo.com)
    qualify.py       Exact qualification_probability + requirements engine
    test_tracker.py  Offline test suite (group stage + knockout parsing)
    test_bracket.py  Offline test suite (bracket engine)
    requirements.txt
  frontend/
    src/
      App.jsx                 Team dropdown, tab switcher, polling loop
      components/
        Verdict.jsx           Qualification status heading
        Likelihood.jsx        Probability bar and percentage
        Scenarios.jsx         Win/draw/loss outcome panels
        Scores.jsx            Live/upcoming match cards
        Ladder.jsx            Third-place table
        KnockoutPanel.jsx     Route strip, R32 tie, likely opponents
        TitleOdds.jsx         Whole-field title odds leaderboard
      helpers.js
      styles.css
    index.html
    package.json
    vite.config.js
  wc26.service        systemd unit (template -- edit paths before use)
```

The backend serves `frontend/dist/` directly, so in production it is one process on one port. In development Vite's dev server runs separately and proxies `/api` calls to the backend.

---

## Setup

### Requirements

- Python 3.11+
- Node 18+ (only needed to build the frontend -- not needed to run a pre-built `dist/`)

### Development (two terminals)

```bash
# Backend -- auto-reloads on file changes
cd backend
python3 -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8080

# Frontend -- Vite dev server, proxies /api to :8080
cd frontend
npm install
npm run dev
# open http://localhost:5173
```

### Production (single process)

Build the frontend once, then run the backend -- it serves the built app and the API together.

```bash
cd frontend
npm install && npm run build
cd ..

cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8080
# open http://localhost:8080
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
| `phase` | `"group"` or `"knockout"` |
| `group_stage_complete` | Boolean -- true once all 12 groups are finished |
| `group` | Group letter |
| `group_table` | Standings for the group (ordered by tiebreaker) |
| `scenarios` | Phase (`pending`/`final`), outcomes for next match, `clinched`/`dead` flags |
| `qualification` | Per-outcome fractions, overall `qualify` probability |
| `live_thirds` | Live third-place ranking across all 12 groups |
| `cutoff` | Number of thirds that advance (8) |
| `knockout` | `in_bracket`, `r32_tie`, `reach` (per round), `opponents` (top 3 per round), `default_team` |
| `title_odds` | Top teams by champion probability: `[{abbr, name, p}]` |
| `all_teams` | Full team list with group (populates the dropdown) |
| `live` | True if the target team's match is currently in progress |
| `stale` | True if the payload is from a cached response (ESPN unreachable) |

Unknown team abbreviations return HTTP 422. Valid abbreviations are in the `all_teams` list from any successful response.

---

## Testing

```bash
cd backend
python test_tracker.py   # group stage: standings, tiebreakers, qualification, knockout parsing
python test_bracket.py   # bracket engine: reach, opponents, title odds, anchoring
```

Both suites run entirely offline -- no network, no API keys.

---

## Data sources

- **Match data:** ESPN's public scoreboard feed (`site.api.espn.com/apis/site/v2/sports/soccer/fifa.world/scoreboard`) -- no API key required. Completed match days are cached to `espn_cache.json` to avoid redundant requests.
- **Elo probabilities:** [worldcupelo.com](https://worldcupelo.com) `/api/match/{A}/{B}` -- no API key required. Responses are cached to `elo_cache.json` for 3 hours.

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
# https://<device-name>.<tailnet>.ts.net

# Or expose publicly with Funnel (enable in admin console first)
sudo tailscale funnel --bg 8080
```

---

## Licence

MIT -- see [LICENSE](LICENSE).
