import { kotime } from '../helpers.js'
import { flag } from '../flags.js'

function MatchCard({ m }) {
  if (!m) return null
  const live = m.state === 'in', done = m.state === 'post'
  const show = live || done
  const hs = m.home_score ?? '–', as = m.away_score ?? '–'
  const label = `${m.home_name || m.home} v ${m.away_name || m.away}`
  return (
    <div className="match">
      <div className="lbl">{label}</div>
      <div className="row"><span className="side">{flag(m.home)} {m.home_name || m.home}</span><span className="sc">{show ? hs : ''}</span></div>
      <div className="row"><span className="side">{flag(m.away)} {m.away_name || m.away}</span><span className="sc">{show ? as : ''}</span></div>
      <div className="state">
        {live ? <><span className="dot" />Live</> : done ? 'Full time' : `Kick-off ${kotime(m.kickoff)}`}
      </div>
    </div>
  )
}

export default function Scores({ state }) {
  const { target_match, other_group_match } = state
  if (!target_match && !other_group_match) return null
  return (
    <div className="scores">
      <MatchCard m={target_match} />
      <MatchCard m={other_group_match} />
    </div>
  )
}
