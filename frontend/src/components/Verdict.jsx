import { ord, targetLine } from '../helpers.js'

const VERDICT_UI = {
  win_group:  { cls: 'is-good', label: 'Won the group' },
  runner_up:  { cls: 'is-good', label: 'Qualified 2nd' },
  third_in:   { cls: 'is-warn', label: 'Through as best third' },
  third_out:  { cls: 'is-bad',  label: 'Out — 3rd in group' },
  fourth_out: { cls: 'is-bad',  label: 'Out — 4th in group' },
}

function computeVerdict(s) {
  const sc = s.scenarios
  const target = s.target
  const name = s.all_teams?.find(t => t.abbr === target)?.name || target

  if (!sc) return { cls: '', tag: `Group ${s.group}`, dot: false, head: name, sub: '' }

  if (sc.phase === 'final') {
    const ui = VERDICT_UI[sc.verdict] || { cls: '', label: sc.verdict }
    const rankNote = sc.third_rank ? ` · ranked ${ord(sc.third_rank)} of thirds` : ''
    return {
      cls: ui.cls, tag: `Group ${s.group} · complete`, dot: false,
      head: ui.label,
      sub: `${name} have played all their group matches.${rankNote}`,
    }
  }

  if (sc.clinched) {
    return {
      cls: 'is-good', tag: `Group ${s.group} · already through`, dot: false,
      head: 'Qualified — already through',
      sub: `${name} are guaranteed a place in the Round of 32 regardless of their remaining result.`,
    }
  }

  if (sc.dead) {
    return {
      cls: 'is-bad', tag: `Group ${s.group} · eliminated`, dot: false,
      head: 'Eliminated — no path to Round of 32',
      sub: `${name} cannot qualify no matter what happens in their remaining match.`,
    }
  }

  const m = sc.remaining
  const line = targetLine(m, target)
  const live = m && m.state === 'in'
  const opp = line?.opp || 'opponent'

  if (live && line) {
    const diff = (line.targetScore ?? 0) - (line.oppScore ?? 0)
    const drawOc = sc.outcomes?.draw
    if (diff > 0) return {
      cls: 'is-good', tag: `Live vs ${opp}`, dot: true, head: 'On course to qualify',
      sub: `${name} are ahead — a win puts them in the Round of 32.`,
    }
    if (diff === 0) {
      const ui = VERDICT_UI[drawOc?.verdict] || { cls: 'is-warn', label: 'in the third-place race' }
      return {
        cls: ui.cls, tag: `Live vs ${opp}`, dot: true, head: `Drawing — ${ui.label}`,
        sub: drawOc?.third_rank
          ? `As it stands ${name} are ranked ${ord(drawOc.third_rank)} among third-placed teams.`
          : `A draw sends ${name} into the third-place race.`,
      }
    }
    const lossOc = sc.outcomes?.loss
    const lossUi = VERDICT_UI[lossOc?.verdict] || { cls: 'is-bad', label: 'at risk' }
    return {
      cls: lossUi.cls, tag: `Live vs ${opp}`, dot: true, head: `Losing — ${lossUi.label}`,
      sub: `A defeat would leave ${name} relying on the third-place table.`,
    }
  }

  // Pre-match
  const winOc = sc.outcomes?.win
  const drawOc = sc.outcomes?.draw
  const lossOc = sc.outcomes?.loss
  const winUi = VERDICT_UI[winOc?.verdict] || {}
  const drawUi = VERDICT_UI[drawOc?.verdict] || {}
  const lossUi = VERDICT_UI[lossOc?.verdict] || {}
  const tag = `Group ${s.group} · vs ${opp}`
  const winQualifies = ['win_group', 'runner_up'].includes(winOc?.verdict)

  if (winQualifies && (drawUi.cls === 'is-warn' || drawUi.cls === 'is-bad')) {
    return {
      cls: 'is-warn', tag, dot: false,
      head: "Win and you're in",
      sub: `A win qualifies ${name} outright. A draw or loss goes to the third-place race.`,
    }
  }

  return {
    cls: winUi.cls || 'is-warn', tag, dot: false,
    head: `Result matters · Group ${s.group}`,
    sub: `Win → ${winUi.label || winOc?.verdict}. Draw → ${drawUi.label || drawOc?.verdict}. Loss → ${lossUi.label || lossOc?.verdict}.`,
  }
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
