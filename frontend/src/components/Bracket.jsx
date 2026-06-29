// Layout constants (px). The bracket is laid out on an absolute canvas so the
// SVG connector layer and the HTML match boxes share one coordinate system.
const ROW_H = 44     // vertical band per R32 slot
const BOX_H = 38
const BOX_W = 134
const COL_W = 172    // > BOX_W to leave room for connectors
const PAD = 8

const pct = p => {
  const v = (p || 0) * 100
  if (v >= 99.95) return '100%'
  if (v > 0 && v < 1) return '<1%'
  return Math.round(v) + '%'
}

export default function Bracket({ bracket, path, team, onPickTeam }) {
  if (!bracket?.slots) return null
  const { rounds, children, slots } = bracket

  // Centre y for every slot: R32 evenly spaced, later rounds at the midpoint of
  // their two children (from the fixed wiring the backend sends).
  const centers = {}
  centers[rounds[0]] = (slots[rounds[0]] || []).map((_, i) => PAD + i * ROW_H + ROW_H / 2)
  for (let r = 1; r < rounds.length; r++) {
    const rnd = rounds[r], prev = rounds[r - 1]
    const kids = children[rnd] || []
    centers[rnd] = (slots[rnd] || []).map((_, i) => {
      const [a, b] = kids[i] || [0, 0]
      return (centers[prev][a] + centers[prev][b]) / 2
    })
  }

  const xLeft = r => PAD + r * COL_W
  const xRight = r => xLeft(r) + BOX_W
  const nR32 = (slots[rounds[0]] || []).length
  const height = PAD * 2 + nR32 * ROW_H
  const width = xLeft(rounds.length) + BOX_W + PAD   // room for the champion node

  const onPath = new Set((path || []).map(([rnd, i]) => `${rnd}:${i}`))

  // Connector polylines: each child elbows out to its parent's left edge.
  const lines = []
  for (let r = 1; r < rounds.length; r++) {
    const rnd = rounds[r], prev = rounds[r - 1]
    const kids = children[rnd] || []
    ;(slots[rnd] || []).forEach((_, i) => {
      const py = centers[rnd][i]
      const midX = (xRight(r - 1) + xLeft(r)) / 2
      ;(kids[i] || []).forEach(c => {
        const cy = centers[prev][c]
        lines.push(`M${xRight(r - 1)},${cy} H${midX} V${py} H${xLeft(r)}`)
      })
    })
  }
  // Champion stub off the Final.
  const champY = centers[rounds[rounds.length - 1]]?.[0]
  const finalSlot = slots[rounds[rounds.length - 1]]?.[0]
  const champion = finalSlot?.winner
    ? { abbr: finalSlot.winner }
    : finalSlot?.adv?.[0] || null
  if (champY != null) {
    lines.push(`M${xRight(rounds.length - 1)},${champY} H${xLeft(rounds.length)}`)
  }

  const Name = ({ abbr, name, cls }) =>
    abbr ? (
      <button className={`br-team ${cls || ''}`} onClick={() => onPickTeam(abbr)}>
        {name || abbr}
      </button>
    ) : (
      <span className="br-team br-tbd">—</span>
    )

  return (
    <div className="bracket-scroll">
      <div className="bracket-canvas" style={{ width, height }}>
        <svg className="bracket-lines" width={width} height={height} aria-hidden="true">
          {lines.map((d, i) => (
            <path key={i} d={d} fill="none" stroke="#143257" strokeWidth="1.5" />
          ))}
        </svg>

        {rounds.map((rnd, r) =>
          (slots[rnd] || []).map((slot, i) => {
            const top = centers[rnd][i] - BOX_H / 2
            const lit = onPath.has(`${rnd}:${i}`)

            // For non-leaf undecided slots, show the most likely participant from
            // each child feeder — this correctly represents "who is likely to play
            // here" rather than "who is most likely to win here overall," which
            // would cause the same team to appear in multiple consecutive boxes.
            let participants = null
            if (rnd !== rounds[0] && !slot.winner) {
              const prev = rounds[r - 1]
              const cids = (children[rnd] || [])[i] || []
              const topOf = ci => {
                const cs = slots[prev]?.[ci]
                if (!cs) return null
                if (cs.winner) return cs.adv?.find(x => x.abbr === cs.winner) || { abbr: cs.winner, name: cs.winner }
                if (cs.adv?.length) return cs.adv[0]
                // R32 slot with no adv (teams not yet assigned): fall back to team_a
                if (cs.team_a) return { abbr: cs.team_a, name: cs.name_a }
                if (cs.team_b) return { abbr: cs.team_b, name: cs.name_b }
                return null
              }
              const pctOf = abbr => (slot.adv || []).find(x => x.abbr === abbr)?.p
              participants = [topOf(cids[0]), topOf(cids[1])]
                .filter(Boolean)
                .map(t => ({ ...t, displayP: pctOf(t.abbr) }))
            }

            return (
              <div
                key={`${rnd}:${i}`}
                className={`br-box ${lit ? 'lit' : ''}`}
                style={{ left: xLeft(r), top, width: BOX_W }}
              >
                {rnd === rounds[0] ? (
                  <>
                    <div className="br-row">
                      <Name abbr={slot.team_a} name={slot.name_a}
                        cls={slot.winner && slot.winner !== slot.team_a ? 'out' : slot.winner === slot.team_a ? 'adv' : ''} />
                      <span className="br-sc">
                        {slot.home_score != null ? slot.home_score : ''}
                      </span>
                    </div>
                    <div className="br-row">
                      <Name abbr={slot.team_b} name={slot.name_b}
                        cls={slot.winner && slot.winner !== slot.team_b ? 'out' : slot.winner === slot.team_b ? 'adv' : ''} />
                      <span className="br-sc">
                        {slot.away_score != null ? slot.away_score : ''}
                      </span>
                    </div>
                  </>
                ) : slot.winner ? (
                  <div className="br-row">
                    <Name abbr={slot.winner}
                      name={slot.adv?.find(x => x.abbr === slot.winner)?.name || slot.winner}
                      cls="adv" />
                    <span className="br-sc">✓</span>
                  </div>
                ) : (
                  (participants || []).map((t, j) => (
                    <div key={t.abbr || j} className="br-row">
                      <Name abbr={t.abbr} name={t.name} />
                      {t.displayP != null && <span className="br-p">{pct(t.displayP)}</span>}
                    </div>
                  ))
                )}
              </div>
            )
          })
        )}

        {champion && champY != null && (
          <div className="br-box br-champ" style={{ left: xLeft(rounds.length), top: champY - BOX_H / 2, width: BOX_W }}>
            <div className="br-champ-label">Champion</div>
            <Name abbr={champion.abbr} name={champion.name || champion.abbr} cls="adv" />
            {champion.p != null && champion.p < 0.999 && (
              <span className="br-p">{pct(champion.p)}</span>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
