# Scotland · Road to the Round of 32

A small self-hosted app that watches Scotland's 2026 World Cup qualification.
One glance tells you whether they're through; if not, it shows exactly which
results still have to fall their way. **FastAPI backend, React (Vite) frontend.**
Built to run on the Pi and be reachable from your phone (and your mates') via
Tailscale.

The brief, in football terms:

- **Win vs Brazil → qualified.** Scotland finish top two in Group C, no other
  results matter.
- **Draw → 3rd on 4 points.** Morocco hold the head-to-head, so a draw can't
  lift Scotland above them. It goes to the third-place race.
- **Lose → 3rd on 3 points.** Still alive, because **8 of the 12 third-placed
  teams advance** — only the bottom four thirds are eliminated.

The app computes the full 12-team third-place table live and shows where
Scotland sit under each outcome, updating as the other groups finish (to 27 June).

## Layout

```
scotland-wc/
  backend/         FastAPI + the tracker logic (stdlib only)
    main.py        /api/state, /healthz, serves the built frontend
    tracker.py     fetch, standings, FIFA tie-breakers, Scotland scenarios
    test_tracker.py
    requirements.txt
  frontend/        Vite + React
    src/           App.jsx, components/, helpers.js, styles.css
    dist/          prebuilt (so you can run the backend without Node)
  scotland-wc.service
```

The backend serves the React app's `dist/` itself, so in production it's all one
origin on port 8080. In dev you run Vite separately and it proxies `/api` to the
backend.

---

## 1. Set up Tailscale first (remote access)

Do this on the Pi. It gives every device a stable name on your private tailnet
and, optionally, a public HTTPS URL for friends who don't have Tailscale.

```bash
# Install on the Pi (Raspberry Pi OS / Debian / Ubuntu)
curl -fsSL https://tailscale.com/install.sh | sh
sudo tailscale up                 # opens an auth URL
tailscale status                  # confirm the Pi's tailnet name, e.g. "sandbox"
```

Enable **MagicDNS** and **HTTPS certificates** in the Tailscale admin console
(DNS page), then expose the app:

```bash
# Private: serve to YOUR tailnet only, over HTTPS, no open ports
sudo tailscale serve --bg 8080
#   -> https://sandbox.<your-tailnet>.ts.net   (your devices only)

# Public: let friends in without installing Tailscale
#   (first enable Funnel for this node in admin console > Access Controls)
sudo tailscale funnel --bg 8080
#   -> same link, now reachable by anyone who has it (treat it as semi-secret)
```

Turn it off again with `sudo tailscale funnel --bg off` /
`sudo tailscale serve --bg off`. If you only want it on your own tailnet, skip
`serve`/`funnel` and just hit `http://sandbox:8080` from any logged-in device.

## 2. Run it

### Production (one process, what the Pi runs)

Build the frontend once, then run the backend — it serves the built app and the
API together.

```bash
# build the UI (skip if you're using the prebuilt dist/ that ships here)
cd frontend && npm install && npm run build && cd ..

# run the backend
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8080
```

Open `http://sandbox.local:8080`.

To keep it running and start on boot (mirrors your Morning Brief setup), edit the
`User`/paths in `scotland-wc.service`, then:

```bash
sudo cp scotland-wc.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now scotland-wc
journalctl -u scotland-wc -f
```

### Dev (hot-reload, two terminals)

```bash
# terminal 1 — backend with reload
cd backend && source .venv/bin/activate
uvicorn main:app --reload --port 8080

# terminal 2 — Vite dev server (proxies /api to :8080)
cd frontend && npm run dev      # http://localhost:5173
```

## 3. Where to open it

| From | URL |
|------|-----|
| The Pi / your LAN | `http://sandbox.local:8080` (or `http://<pi-ip>:8080`) |
| Any of your devices on the tailnet | `http://sandbox:8080` |
| After `tailscale serve` | `https://sandbox.<tailnet>.ts.net` |
| Friends, after `tailscale funnel` | same `https://…ts.net` link |
| Dev (Vite) | `http://localhost:5173` |

`sandbox.local` uses mDNS (Avahi), which Raspberry Pi OS ships with — the
easy-to-remember LAN address.

---

## How it decides things

Scotland's current Group C line: **3 pts, GD 0, 1 goal for** (beat Haiti 1–0,
lost to Morocco 0–1).

- **Win** → 6 pts, finish 1st or 2nd. The only team that can pass 6 is Morocco
  (beating Haiti to reach 7); Brazil are stuck on 4 after losing. So Scotland are
  top-two in every case → through.
- **Draw** → 4 pts. A draw doesn't change goal difference, so Scotland stay on
  GD 0 and are ranked against the other groups' thirds by **points → goal
  difference → goals scored**.
- **Lose** → 3 pts; goal difference drops by the losing margin. The "Lose" panel
  assumes a one-goal defeat (best realistic case) and flags that a heavier loss
  lowers the ranking.

Qualification rule (2026): top two of each of the 12 groups, plus the **8 best
third-placed teams**, ranked by points, goal difference, goals scored, then
fair-play score, then world ranking. The last two aren't in the free feed and
only matter on an exact tie — the app notes this.

## Data source and reliability

Pulls from ESPN's public, key-free scoreboard endpoint
(`site.api.espn.com/apis/site/v2/sports/soccer/fifa.world/scoreboard`). It's
undocumented and unofficial, so the app:

- caches each finished day to `espn_cache.json` and only re-polls *today's*
  fixtures — light on the Pi and on ESPN;
- keeps serving the last good copy if a fetch fails, with a "cached" badge;
- refreshes every ~90s, dropping to ~20s while Scotland are actually playing.

If ESPN ever changes the feed, the drop-in alternative is **API-Football**'s free
tier (`league=1, season=2026`, 100 req/day, needs a free key) — swap the
`Fetcher` class in `tracker.py`.

## Overhead on the Pi

Negligible. A single uvicorn worker wakes only to serve a page load and refresh a
cached JSON blob each minute or so — a few MB of RAM, effectively no CPU between
refreshes. Morning Brief runs as periodic timer bursts, not constant load, so the
two don't compete. The Pi 3B+ is fine for a tournament-length toy; the EliteDesk
would be the tidier permanent home once it's provisioned, but no need to wait.

(Node is only needed to *build* the frontend. If you don't want Node on the Pi,
build `dist/` on your workstation and copy it over — or use the prebuilt `dist/`
that ships in this folder.)
