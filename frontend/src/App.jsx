import { useEffect, useState, useRef } from 'react'
import { signed } from './helpers.js'
import Verdict from './components/Verdict.jsx'
import Scores from './components/Scores.jsx'
import Scenarios from './components/Scenarios.jsx'
import Ladder from './components/Ladder.jsx'
import Likelihood from './components/Likelihood.jsx'
import Requirements from './components/Requirements.jsx'

const POLL_MS = 25000

function GroupTable({ rows, target }) {
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
          <tr key={t.abbr} className={t.abbr === target ? 'sco' : ''}>
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

function TeamSelect({ allTeams, team, onChange }) {
  if (!allTeams || allTeams.length === 0) return null
  const byGroup = {}
  for (const t of allTeams) {
    if (!byGroup[t.group]) byGroup[t.group] = []
    byGroup[t.group].push(t)
  }
  return (
    <select value={team} onChange={e => onChange(e.target.value)} className="team-select">
      {Object.entries(byGroup).sort().map(([g, teams]) => (
        <optgroup key={g} label={`Group ${g}`}>
          {teams.map(t => (
            <option key={t.abbr} value={t.abbr}>{t.name || t.abbr}</option>
          ))}
        </optgroup>
      ))}
    </select>
  )
}

export default function App() {
  const [team, setTeam] = useState('SCO')
  const [state, setState] = useState(null)
  const [connErr, setConnErr] = useState(false)
  const [loading, setLoading] = useState(true)
  const cacheRef = useRef(new Map())

  useEffect(() => {
    let alive = true
    let isFirst = true

    if (cacheRef.current.has(team)) {
      setState(cacheRef.current.get(team))
    }
    setLoading(true)

    const tick = async () => {
      try {
        const res = await fetch(`/api/state?team=${team}`, { cache: 'no-store' })
        const s = await res.json()
        if (alive) {
          cacheRef.current.set(team, s)
          setState(s)
          setConnErr(false)
          if (isFirst) { setLoading(false); isFirst = false }
        }
      } catch {
        if (alive) {
          setConnErr(true)
          if (isFirst) { setLoading(false); isFirst = false }
        }
      }
    }
    tick()
    const id = setInterval(tick, POLL_MS)
    return () => { alive = false; clearInterval(id) }
  }, [team])

  const stamp = loading && !state ? 'loading…'
    : connErr ? 'connection error'
    : state ? (state.stale ? '⚠ cached · ' : '') + 'updated ' + (state.generated || '')
    : 'loading…'

  const targetName = state?.all_teams?.find(t => t.abbr === team)?.name || team

  return (
    <div className="wrap">
      <div className="eyebrow">
        <TeamSelect allTeams={state?.all_teams} team={team} onChange={setTeam} />
        <span className={`stamp ${(connErr || state?.stale) ? 'stale' : ''}`}>
          {loading && state && <span className="spinner" aria-hidden="true" />}
          {stamp}
        </span>
      </div>

      {state?.stale && (
        <div className="err">Live feed didn't answer — showing the last good data.</div>
      )}

      {!state ? (
        <div className="verdict"><h1>Loading…</h1></div>
      ) : (
        <>
          <Verdict state={state} />
          <Likelihood qualification={state.qualification} />
          <Requirements requirements={state.qualification?.requirements} scenarios={state.scenarios} />
          <Scores state={state} />

          <h2 className="section">
            {state.scenarios?.phase === 'pending' ? `If ${targetName}…` : `${targetName} · Final`}
          </h2>
          <Scenarios scenarios={state.scenarios} target={team} cutoff={state.cutoff} />

          <h2 className="section">Best third-placed teams · top 8 advance</h2>
          <Ladder thirds={state.live_thirds} cutoff={state.cutoff} target={team} />

          <h2 className="section" style={{ marginTop: 26 }}>Group {state.group}</h2>
          <GroupTable rows={state.group_table} target={team} />

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
