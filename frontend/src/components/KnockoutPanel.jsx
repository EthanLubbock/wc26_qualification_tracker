import { kotime } from '../helpers.js'

const pct = p => {
  const v = (p || 0) * 100
  if (v >= 99.95) return '100%'
  if (v > 0 && v < 1) return '<1%'
  return Math.round(v) + '%'
}

// Stages of the route after the opening R32 tie.
const STAGES = [
  { key: 'R16', label: 'R16' },
  { key: 'QF', label: 'QF' },
  { key: 'SF', label: 'SF' },
  { key: 'F', label: 'Final' },
  { key: 'champion', label: '🏆' },
]

const OPP_ROUNDS = [
  { key: 'R16', label: 'Round of 16' },
  { key: 'QF', label: 'Quarter-final' },
  { key: 'SF', label: 'Semi-final' },
  { key: 'F', label: 'Final' },
]

function R32Tie({ tie, target }) {
  if (!tie) return null
  const decided = tie.winner != null
  const live = tie.state === 'in'
  const hasScore = tie.home_score != null && tie.away_score != null
  const status = live ? 'Live' : decided ? 'Full time' : `Kick-off ${kotime(tie.kickoff)}`
  const won = decided && tie.winner === target
  return (
    <div className={`ko-tie ${decided ? (won ? 'win' : 'lose') : ''}`}>
      <div className="ko-tie-label">Round of 32 {live && <span className="dot" />}{status}</div>
      <div className="ko-tie-teams">
        <span className={tie.winner === tie.home ? 'adv' : ''}>{tie.home_name || tie.home}</span>
        <span className="ko-sc">{hasScore ? `${tie.home_score}–${tie.away_score}` : 'v'}</span>
        <span className={tie.winner === tie.away ? 'adv' : ''}>{tie.away_name || tie.away}</span>
      </div>
    </div>
  )
}

export default function KnockoutPanel({ knockout, team, targetName, allTeams, onPickTeam }) {
  if (!knockout) return null

  if (!knockout.in_bracket) {
    const def = knockout.default_team
    const defName = allTeams?.find(t => t.abbr === def)?.name || def
    return (
      <div className="panel ko-out">
        <h3>{targetName} didn't reach the knockouts</h3>
        <p className="sub">They finished outside the Round of 32 places in the group stage.</p>
        {def && (
          <button className="ko-cta" onClick={() => onPickTeam(def)}>
            View {defName} →
          </button>
        )}
      </div>
    )
  }

  const reach = knockout.reach || {}
  const tie = knockout.r32_tie
  const r32Secured = tie?.winner && reach.R16 >= 0.999
  const eliminated = tie?.winner && reach.R16 <= 1e-9

  return (
    <>
      <div className="route">
        <div className={`route-cell ${r32Secured ? 'secured' : eliminated ? 'dead' : ''}`}>
          <div className="route-stage">R32</div>
          <div className="route-pct">{eliminated ? 'out' : r32Secured ? '✓' : 'in'}</div>
        </div>
        {STAGES.map(s => {
          const p = reach[s.key] || 0
          const secured = p >= 0.999
          const dead = p <= 1e-9
          return (
            <div key={s.key} className={`route-cell ${secured ? 'secured' : dead ? 'dead' : ''}`}>
              <div className="route-stage">{s.label}</div>
              <div className="route-pct">{secured ? '✓' : pct(p)}</div>
            </div>
          )
        })}
      </div>

      <R32Tie tie={tie} target={team} />

      {OPP_ROUNDS.some(r => (knockout.opponents?.[r.key] || []).length) && (
        <div className="ko-opps">
          <h3 className="section">Likely opponents</h3>
          <div className="grid3">
            {OPP_ROUNDS.filter(r => (knockout.opponents?.[r.key] || []).length).map(r => (
              <div key={r.key} className="panel ko-opp">
                <div className="ko-opp-round">{r.label}</div>
                {(knockout.opponents[r.key] || []).map(o => (
                  <div key={o.abbr} className="ko-opp-row">
                    <span className="ko-opp-team">{o.name || o.abbr}</span>
                    <span className="ko-opp-p">{pct(o.p)}</span>
                  </div>
                ))}
              </div>
            ))}
          </div>
        </div>
      )}
    </>
  )
}
