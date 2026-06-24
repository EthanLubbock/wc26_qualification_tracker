import { ord, scoLine } from '../helpers.js'

// Works out the headline state from phase + live score + third-place table.
function computeVerdict(s) {
  const sco = scoLine(s.sco_match)
  const draw = s.scenarios.draw, lose = s.scenarios.lose

  if (s.phase === 'pre') {
    return {
      cls: draw.in_top8 ? 'is-warn' : 'is-bad',
      tag: 'Group C · Matchday 3', dot: false,
      head: "Win and you're in",
      sub: `Beat Brazil and Scotland qualify outright. A draw or defeat sends it to ` +
        `the third-place race — a draw currently ranks ${ord(draw.third_rank)} of ` +
        `${draw.field_size} (${draw.in_top8 ? 'inside' : 'outside'} the top 8), a narrow ` +
        `loss ${ord(lose.third_rank)} of ${lose.field_size} (${lose.in_top8 ? 'in' : 'out'}).`
    }
  }

  if (sco) {
    const diff = (sco.scoScore ?? 0) - (sco.oppScore ?? 0)

    if (s.phase === 'live') {
      if (diff > 0) return {
        cls: 'is-good', tag: 'Live vs Brazil', dot: true, head: 'On course to qualify',
        sub: 'Scotland are ahead — a win means top two and the Round of 32, no other results needed.'
      }
      if (diff === 0) return {
        cls: draw.in_top8 ? 'is-warn' : 'is-bad', tag: 'Live vs Brazil', dot: true,
        head: 'Drawing — 3rd place',
        sub: `As it stands Scotland finish 3rd on 4 points and sit ${ord(draw.third_rank)} of ` +
          `${draw.field_size} among the thirds (${draw.in_top8 ? 'inside' : 'outside'} the top 8).`
      }
      return {
        cls: lose.in_top8 ? 'is-warn' : 'is-bad', tag: 'Live vs Brazil', dot: true,
        head: 'Losing — 3rd place',
        sub: 'A defeat leaves Scotland 3rd on 3 points; the third-place table below is what counts.'
      }
    }

    // post
    if (diff > 0) return {
      cls: 'is-good', tag: 'Full time · qualified', dot: false, head: 'Scotland are through',
      sub: 'Beat Brazil, finished top two in Group C, into the Round of 32.'
    }
    const me = s.live_thirds.find(t => t.abbr === 'SCO')
    const rank = me ? s.live_thirds.indexOf(me) + 1 : null
    const inTop = rank !== null && rank <= s.cutoff
    if (rank === null) return {
      cls: 'is-warn', tag: 'Full time · 3rd in Group C', dot: false,
      head: '3rd place — awaiting groups',
      sub: 'Scotland finished 3rd. The remaining groups decide the eight best third-placed teams.'
    }
    return {
      cls: inTop ? 'is-good' : 'is-bad', tag: 'Full time · 3rd in Group C', dot: false,
      head: inTop ? 'Holding a qualifying spot' : 'Below the line — for now',
      sub: `Scotland are the ${ord(rank)} best third-placed team. Top ${s.cutoff} go through; ` +
        `this can still move as other groups finish.`
    }
  }

  return { cls: '', tag: 'Group C', dot: false, head: 'Scotland', sub: '' }
}

export default function Verdict({ state }) {
  const v = computeVerdict(state)
  return (
    <div className={`verdict ${v.cls}`}>
      <div className="tag">{v.dot && <span className="dot" />}{v.tag}</div>
      <h1>{v.head}</h1>
      <p>{v.sub}</p>
    </div>
  )
}
