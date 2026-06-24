import { kotime } from '../helpers.js'

function MatchCard({ m, label }) {
  if (!m) {
    return (
      <div className="match">
        <div className="lbl">{label}</div>
        <div className="state">No fixture</div>
      </div>
    )
  }
  const live = m.state === 'in', done = m.state === 'post'
  const show = live || done
  const hs = m.home_score ?? '–', as = m.away_score ?? '–'
  return (
    <div className="match">
      <div className="lbl">{label}</div>
      <div className="row"><span className="side">{m.home}</span><span className="sc">{show ? hs : ''}</span></div>
      <div className="row"><span className="side">{m.away}</span><span className="sc">{show ? as : ''}</span></div>
      <div className="state">
        {live ? <><span className="dot" />Live</> : done ? 'Full time' : `Kick-off ${kotime(m.kickoff)}`}
      </div>
    </div>
  )
}

export default function Scores({ state }) {
  return (
    <div className="scores">
      <MatchCard m={state.sco_match} label="Scotland v Brazil" />
      <MatchCard m={state.other_c_match} label="Morocco v Haiti" />
    </div>
  )
}
