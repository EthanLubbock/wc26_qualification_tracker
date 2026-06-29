import { useEffect, useState, useRef } from 'react'
import { signed } from './helpers.js'
import { flag } from './flags.js'
import Verdict from './components/Verdict.jsx'
import Scores from './components/Scores.jsx'
import Scenarios from './components/Scenarios.jsx'
import Ladder from './components/Ladder.jsx'
import Likelihood from './components/Likelihood.jsx'
import Requirements from './components/Requirements.jsx'
import KnockoutPanel from './components/KnockoutPanel.jsx'
import TitleOdds from './components/TitleOdds.jsx'
import Bracket from './components/Bracket.jsx'

const POLL_MS = 25000
const INITIAL_TEAM = 'SCO'
const TEAM_KEY = 'wc-team'

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
            <td className="team">{flag(t.abbr)} {t.name || t.abbr}</td>
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
            <option key={t.abbr} value={t.abbr}>{flag(t.abbr)} {t.name || t.abbr}</option>
          ))}
        </optgroup>
      ))}
    </select>
  )
}

export default function App() {
  const [team, setTeam] = useState(() => localStorage.getItem(TEAM_KEY) || INITIAL_TEAM)
  const [whatif, setWhatif] = useState(null)   // null | 'win' | 'lose'
  const [state, setState] = useState(null)
  const [connErr, setConnErr] = useState(false)
  const [loading, setLoading] = useState(true)
  const [view, setView] = useState('group')
  const cacheRef = useRef(new Map())
  const firstStateRef = useRef(false)
  const hadStored = useRef(localStorage.getItem(TEAM_KEY) != null)

  // Remember the chosen team across reloads; a fresh pick is never a what-if.
  useEffect(() => {
    localStorage.setItem(TEAM_KEY, team)
    setWhatif(null)
  }, [team])

  useEffect(() => {
    let alive = true
    let isFirst = true
    const cacheKey = team + '|' + (whatif || '')

    if (cacheRef.current.has(cacheKey)) {
      setState(cacheRef.current.get(cacheKey))
    }
    setLoading(true)

    const tick = async () => {
      try {
        const url = `/api/state?team=${team}` + (whatif ? `&whatif=${whatif}` : '')
        const res = await fetch(url, { cache: 'no-store' })
        const s = await res.json()
        if (alive) {
          cacheRef.current.set(cacheKey, s)
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
  }, [team, whatif])

  // Once the first payload arrives during the knockout phase, focus the
  // Knockout tab and, if the default team (SCO) didn't make it, switch to a
  // live team so the view loads populated. Runs once; a stored preference or a
  // manual pick is respected over the auto-switch.
  useEffect(() => {
    if (firstStateRef.current || !state) return
    if (state.phase === 'knockout') {
      setView('knockout')
      const ko = state.knockout
      if (team === INITIAL_TEAM && !hadStored.current && ko && !ko.in_bracket && ko.default_team) {
        setTeam(ko.default_team)
      }
    }
    firstStateRef.current = true
  }, [state, team])

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
          <div className="tabs">
            <button className={`tab ${view === 'group' ? 'is-active' : ''}`}
                    onClick={() => setView('group')}>Group stage</button>
            <button className={`tab ${view === 'knockout' ? 'is-active' : ''}`}
                    onClick={() => setView('knockout')}>Knockouts</button>
          </div>

          {view === 'group' ? (
            <>
              {state.group_stage_complete && (
                <div className="banner">Group stage complete — final standings.</div>
              )}
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
            </>
          ) : (
            <>
              {!state.group_stage_complete ? (
                <div className="panel ko-placeholder">
                  <h3>Knockouts</h3>
                  <p className="sub">Come back when the group stage is complete.</p>
                </div>
              ) : (
                <>
                  <h2 className="section">{targetName} · route to the title</h2>
                  <KnockoutPanel
                    knockout={state.knockout}
                    team={team}
                    targetName={targetName}
                    allTeams={state.all_teams}
                    onPickTeam={setTeam}
                    whatif={whatif}
                    onWhatif={setWhatif}
                  />
                  <h2 className="section" style={{ marginTop: 26 }}>Title race</h2>
                  <TitleOdds titleOdds={state.title_odds} target={team} />

                  {state.bracket && (
                    <>
                      <h2 className="section" style={{ marginTop: 26 }}>Full bracket</h2>
                      <Bracket
                        bracket={state.bracket}
                        path={state.knockout?.path}
                        team={team}
                        onPickTeam={setTeam}
                      />
                    </>
                  )}
                </>
              )}
            </>
          )}

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
