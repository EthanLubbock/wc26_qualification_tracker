import { useEffect, useState } from 'react'
import { signed } from './helpers.js'
import Verdict from './components/Verdict.jsx'
import Scores from './components/Scores.jsx'
import Scenarios from './components/Scenarios.jsx'
import Ladder from './components/Ladder.jsx'

const POLL_MS = 25000

function GroupC({ rows }) {
  return (
    <table>
      <thead>
        <tr>
          <th className="rk">#</th><th>Team</th><th>Pl</th>
          <th>Pts</th><th>GD</th><th>GF</th>
        </tr>
      </thead>
      <tbody>
        {(rows || []).map((t, i) => (
          <tr key={t.abbr} className={t.abbr === 'SCO' ? 'sco' : ''}>
            <td className="rk">{i + 1}</td>
            <td className="team">{t.name || t.abbr}</td>
            <td>{t.played}</td>
            <td>{t.points}</td>
            <td>{signed(t.gd)}</td>
            <td>{t.gf}</td>
          </tr>
        ))}
      </tbody>
    </table>
  )
}

export default function App() {
  const [state, setState] = useState(null)
  const [connErr, setConnErr] = useState(false)

  useEffect(() => {
    let alive = true
    const tick = async () => {
      try {
        const res = await fetch('/api/state', { cache: 'no-store' })
        const s = await res.json()
        if (alive) { setState(s); setConnErr(false) }
      } catch {
        if (alive) setConnErr(true)
      }
    }
    tick()
    const id = setInterval(tick, POLL_MS)
    return () => { alive = false; clearInterval(id) }
  }, [])

  const stamp = connErr ? 'connection error'
    : state ? (state.stale ? '⚠ cached · ' : '') + 'updated ' + (state.generated || '')
    : 'loading…'

  return (
    <div className="wrap">
      <div className="eyebrow">
        <span>Scotland · Road to the Round of 32</span>
        <span className={`stamp ${(connErr || state?.stale) ? 'stale' : ''}`}>{stamp}</span>
      </div>

      {state?.stale && (
        <div className="err">Live feed didn't answer — showing the last good data.</div>
      )}

      {!state ? (
        <div className="verdict"><h1>Loading…</h1></div>
      ) : (
        <>
          <Verdict state={state} />
          <Scores state={state} />

          <h2 className="section">If Scotland…</h2>
          <Scenarios scenarios={state.scenarios} />

          <h2 className="section">Best third-placed teams · top 8 advance</h2>
          <Ladder thirds={state.live_thirds} cutoff={state.cutoff} />

          <h2 className="section" style={{ marginTop: 26 }}>Group C</h2>
          <GroupC rows={state.group_c} />

          <footer>
            Top two in every group plus the eight best third-placed teams reach the
            Round of 32. {state.note_tiebreak}<br />
            Data: ESPN public feed · auto-refreshes every {POLL_MS / 1000}s.
          </footer>
        </>
      )}
    </div>
  )
}
