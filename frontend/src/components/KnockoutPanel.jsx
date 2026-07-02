import { koDatetime } from '../helpers.js'

function RouteChart({ reach }) {
  const stages = [
    { label: 'R32',    p: 1 },
    { label: 'R16',    p: reach.R16      || 0 },
    { label: 'QF',     p: reach.QF       || 0 },
    { label: 'SF',     p: reach.SF       || 0 },
    { label: 'Final',  p: reach.F        || 0 },
    { label: 'Winner', p: reach.champion || 0 },
  ]

  const W = 560, H = 160
  const padL = 42, padR = 12, padT = 14, padB = 28
  const innerW = W - padL - padR
  const innerH = H - padT - padB
  const yBot = padT + innerH

  const xOf = i => padL + (i / (stages.length - 1)) * innerW
  const yOf = p => padT + (1 - p) * innerH
  const pts = stages.map((s, i) => [xOf(i), yOf(s.p)])

  const smooth = points => {
    let d = `M${points[0][0]},${points[0][1]}`
    for (let i = 0; i < points.length - 1; i++) {
      const [x0, y0] = points[i], [x1, y1] = points[i + 1]
      const cx = (x1 - x0) * 0.4
      d += ` C${x0 + cx},${y0} ${x1 - cx},${y1} ${x1},${y1}`
    }
    return d
  }

  const linePath = smooth(pts)
  const areaPath = `${linePath} L${pts[pts.length - 1][0]},${yBot} L${pts[0][0]},${yBot} Z`
  const dotFill = p => p >= 0.999 ? '#2bd47d' : p >= 0.55 ? '#2bd47d' : p >= 0.25 ? '#f4b740' : '#ef5a6a'
  const labelPct = p => p >= 0.999 ? '100%' : p < 0.005 ? '<1%' : `${Math.round(p * 100)}%`

  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="route-chart" role="img" aria-label="Route to the title probability">
      <defs>
        <linearGradient id="rc-fill" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="#2f80ed" stopOpacity="0.22" />
          <stop offset="100%" stopColor="#2f80ed" stopOpacity="0.02" />
        </linearGradient>
      </defs>

      {[0, 25, 50, 75, 100].map(t => (
        <g key={t}>
          <line x1={padL} y1={yOf(t / 100)} x2={W - padR} y2={yOf(t / 100)}
            stroke="#143257" strokeWidth="1" />
          <text x={padL - 5} y={yOf(t / 100) + 4} textAnchor="end"
            fontSize="10" fill="#8aa6c4" fontFamily="Inter,sans-serif">
            {t}%
          </text>
        </g>
      ))}

      {pts.map(([x], i) => (
        <line key={i} x1={x} y1={padT} x2={x} y2={yBot}
          stroke="#143257" strokeWidth="1" strokeDasharray="2 4" />
      ))}

      <path d={areaPath} fill="url(#rc-fill)" />
      <path d={linePath} fill="none" stroke="#2f80ed" strokeWidth="2.5"
        strokeLinejoin="round" strokeLinecap="round" />

      {stages.map((s, i) => (
        <g key={s.label}>
          <circle cx={pts[i][0]} cy={pts[i][1]} r="4.5"
            fill={dotFill(s.p)} stroke="#0c2440" strokeWidth="1.5">
            <title>{s.label}: {labelPct(s.p)}</title>
          </circle>
          <text x={pts[i][0]} y={H - padB + 14}
            textAnchor={i === 0 ? 'start' : i === stages.length - 1 ? 'end' : 'middle'}
            fontSize="10" fill="#8aa6c4"
            fontFamily="'Saira Condensed',sans-serif" fontWeight="600" letterSpacing="0.08em">
            {s.label.toUpperCase()}
          </text>
        </g>
      ))}
    </svg>
  )
}

const pct = p => {
  const v = (p || 0) * 100
  if (v >= 99.95) return '100%'
  if (v > 0 && v < 1) return '<1%'
  return Math.round(v) + '%'
}

// Returns a CSS class name based on probability magnitude.
const pClass = p => p >= 0.55 ? 'p-high' : p >= 0.25 ? 'p-mid' : 'p-low'

const STAGES = [
  { key: 'R16', label: 'R16' },
  { key: 'QF', label: 'QF' },
  { key: 'SF', label: 'SF' },
  { key: 'F', label: 'Final' },
  { key: 'champion', label: 'Winner' },
]

const OPP_ROUNDS = [
  { key: 'R16', label: 'Round of 16' },
  { key: 'QF', label: 'Quarter-final' },
  { key: 'SF', label: 'Semi-final' },
  { key: 'F', label: 'Final' },
]

const ROUND_LABEL = {
  R32: 'Round of 32', R16: 'Round of 16',
  QF: 'Quarter-final', SF: 'Semi-final', F: 'Final',
}

// One side of a game: a real team (highlighted if it's the target / the winner)
// or a "Winner of A v B" placeholder when the opponent isn't decided yet.
function SideName({ side }) {
  if (side.placeholder) return <span className="ko-tbd">{side.label}</span>
  return <span className={side.is_target ? 'tgt' : ''}>{side.name || side.abbr}</span>
}

function GameCard({ game, target }) {
  const [home, away] = game.sides
  const decided = game.winner != null
  const live = game.state === 'in'
  const played = live || game.state === 'post'
  const won = decided && game.winner === target
  const status = live ? 'Live' : decided ? 'Full time' : `Kick-off ${koDatetime(game.kickoff)}`
  // Score only for games actually under way / finished — ESPN reports 0–0 for
  // upcoming ties, which we show as "v" instead.
  const showScore = played && home.score != null && away.score != null
  const showOdds = game.state === 'pre' && home.win_pct != null && away.win_pct != null
  const advClass = side => (decided && !side.placeholder && game.winner === side.abbr ? 'adv' : '')
  return (
    <div className={`ko-tie ${decided ? (won ? 'win' : 'lose') : ''}`}>
      <div className="ko-tie-label">
        {ROUND_LABEL[game.round] || game.round}
        {live && <span className="dot" />}
        <span>{status}</span>
      </div>
      <div className="ko-tie-teams">
        <span className={advClass(home)}><SideName side={home} /></span>
        <span className="ko-sc">{showScore ? `${home.score}–${away.score}` : 'v'}</span>
        <span className={advClass(away)}><SideName side={away} /></span>
      </div>
      {showOdds && (
        <div className="ko-odds-bar">
          <span className={`ko-odds-pct ${pClass(home.win_pct)}`}>{pct(home.win_pct)}</span>
          <div className="ko-odds-track">
            <div className={`ko-odds-seg ${pClass(home.win_pct)}`} style={{ width: `${home.win_pct * 100}%` }} />
            <div className={`ko-odds-seg ${pClass(away.win_pct)}`} style={{ width: `${away.win_pct * 100}%` }} />
          </div>
          <span className={`ko-odds-pct ${pClass(away.win_pct)}`}>{pct(away.win_pct)}</span>
        </div>
      )}
    </div>
  )
}

function NextGames({ games, target }) {
  if (!games || !games.length) return null
  return (
    <div className="ko-games">
      {games.map((g, i) => <GameCard key={`${g.round}-${i}`} game={g} target={target} />)}
    </div>
  )
}

function WhatIf({ tie, target, targetName, whatif, onWhatif }) {
  if (!tie || tie.winner != null) return null
  const opp = tie.home === target ? tie.away_name || tie.away : tie.home_name || tie.home
  const opts = [
    { key: null, label: 'Live odds' },
    { key: 'win', label: 'If win' },
    { key: 'lose', label: 'If lose' },
  ]
  return (
    <div className="whatif">
      <span className="whatif-label">What if…</span>
      <div className="whatif-pills">
        {opts.map(o => (
          <button
            key={o.label}
            className={`whatif-pill ${whatif === o.key ? 'is-active' : ''}`}
            onClick={() => onWhatif(o.key)}
          >
            {o.label}
          </button>
        ))}
      </div>
      {whatif && (
        <div className="whatif-note">
          Hypothetical — odds below assume {targetName} {whatif === 'win' ? 'beats' : 'loses to'} {opp}.
        </div>
      )}
    </div>
  )
}

export default function KnockoutPanel({ knockout, team, targetName, allTeams, onPickTeam, whatif, onWhatif }) {
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
      <RouteChart reach={reach} />
      <div className="route">
        <div className={`route-cell ${r32Secured ? 'secured' : eliminated ? 'dead' : ''}`}>
          <div className="route-stage">R32</div>
          <div className="route-pct">{eliminated ? 'out' : r32Secured ? '✓' : 'in'}</div>
        </div>
        {STAGES.map(s => {
          const p = reach[s.key] || 0
          const secured = p >= 0.999
          const dead = p <= 1e-9
          const pc = !secured && !dead ? pClass(p) : ''
          return (
            <div key={s.key} className={`route-cell ${secured ? 'secured' : dead ? 'dead' : pc}`}>
              <div className="route-stage">{s.label}</div>
              <div className={`route-pct ${pc}`}>{secured ? '✓' : pct(p)}</div>
            </div>
          )
        })}
      </div>

      <NextGames games={knockout.games} target={team} />

      <WhatIf tie={tie} target={team} targetName={targetName}
        whatif={whatif} onWhatif={onWhatif} />

      {OPP_ROUNDS.some(r => (knockout.opponents?.[r.key] || []).length) && (
        <div className="ko-opps">
          <h2 className="section">Likely opponents</h2>
          <div className="grid3">
            {OPP_ROUNDS.filter(r => (knockout.opponents?.[r.key] || []).length).map(r => {
              const opps = knockout.opponents[r.key] || []
              const maxP = opps[0]?.p || 1
              return (
                <div key={r.key} className="panel ko-opp">
                  <div className="ko-opp-round">{r.label}</div>
                  {opps.map(o => (
                    <div key={o.abbr} className="ko-opp-row">
                      <span className="ko-opp-team">{o.name || o.abbr}</span>
                      <div className="ko-opp-track">
                        <div
                          className={`ko-opp-bar ${pClass(o.p)}`}
                          style={{ width: `${Math.max(6, (o.p / maxP) * 100)}%` }}
                        />
                      </div>
                      <span className={`ko-opp-p ${pClass(o.p)}`}>{pct(o.p)}</span>
                    </div>
                  ))}
                </div>
              )
            })}
          </div>
        </div>
      )}
    </>
  )
}
