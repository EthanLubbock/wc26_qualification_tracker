// Layout constants (px). The bracket is laid out on an absolute canvas so the
// SVG connector layer and the HTML match boxes share one coordinate system.
//
// The diagram is mirrored: the top half of the draw flows left→right and the
// bottom half flows right→left, both converging on the Final in the centre.
// Within each half, R32 ties are ordered by a depth-first walk of the bracket
// tree so a slot's two feeders are always vertically adjacent — that's what
// keeps the connectors nested instead of crossing.
const ROW_H = 44     // vertical band per R32 slot (per side)
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
  const nRounds = rounds.length
  const finalR = nRounds - 1            // round index of the Final
  const finalCol = nRounds - 1          // centre column
  const colCount = 2 * (nRounds - 1) + 1

  const kidsOf = (r, idx) => (children[rounds[r]] || [])[idx] || []
  // R32 slot indices under a slot, in DFS (top→bottom) order.
  const leavesUnder = (r, idx) =>
    r === 0 ? [idx] : kidsOf(r, idx).flatMap(ci => leavesUnder(r - 1, ci))

  const finalKids = kidsOf(finalR, 0)   // [topSF, bottomSF]
  const topSF = finalKids[0], botSF = finalKids[1]
  const topLeaves = topSF != null ? leavesUnder(finalR - 1, topSF) : []
  const botLeaves = botSF != null ? leavesUnder(finalR - 1, botSF) : []

  // Side map: 'L' (left half), 'R' (right half), 'F' (final). Propagated down
  // each Semi-final's subtree.
  const side = {}
  const mark = (r, idx, s) => {
    side[`${r}:${idx}`] = s
    if (r > 0) kidsOf(r, idx).forEach(ci => mark(r - 1, ci, s))
  }
  side[`${finalR}:0`] = 'F'
  if (topSF != null) mark(finalR - 1, topSF, 'L')
  if (botSF != null) mark(finalR - 1, botSF, 'R')
  const sideOf = (r, idx) => side[`${r}:${idx}`] || 'L'
  const colOf = (r, idx) => {
    const s = sideOf(r, idx)
    if (s === 'F') return finalCol
    return s === 'L' ? r : colCount - 1 - r
  }

  // Vertical centre for every slot. R32 leaves are evenly spaced (both halves
  // share the same vertical range); later rounds sit at the midpoint of their
  // two children.
  const yByLeaf = {}
  topLeaves.forEach((idx, k) => { yByLeaf[idx] = PAD + k * ROW_H + ROW_H / 2 })
  botLeaves.forEach((idx, k) => { yByLeaf[idx] = PAD + k * ROW_H + ROW_H / 2 })
  const yCache = {}
  const centerY = (r, idx) => {
    const key = `${r}:${idx}`
    if (key in yCache) return yCache[key]
    let y
    if (r === 0) {
      y = yByLeaf[idx] ?? PAD + idx * ROW_H + ROW_H / 2
    } else {
      const ys = kidsOf(r, idx).map(ci => centerY(r - 1, ci))
      y = ys.length ? ys.reduce((a, b) => a + b, 0) / ys.length : PAD + ROW_H / 2
    }
    yCache[key] = y
    return y
  }

  const xLeft = c => PAD + c * COL_W
  const xRight = c => xLeft(c) + BOX_W

  const rowsPerSide = Math.max(topLeaves.length, botLeaves.length, 1)
  const CHAMP_GAP = 60                  // room for the champion node below the Final
  const height = PAD * 2 + rowsPerSide * ROW_H + CHAMP_GAP
  const width = xLeft(colCount - 1) + BOX_W + PAD

  const onPath = new Set((path || []).map(([rnd, i]) => `${rnd}:${i}`))

  // Connector polylines: each child elbows toward its parent's facing edge —
  // rightward in the left half, leftward in the right half.
  const lines = []
  for (let r = 1; r <= finalR; r++) {
    ;(slots[rounds[r]] || []).forEach((_, i) => {
      const py = centerY(r, i)
      const cP = colOf(r, i)
      kidsOf(r, i).forEach(ci => {
        const cy = centerY(r - 1, ci)
        const cC = colOf(r - 1, ci)
        if (cC < cP) {
          const midX = (xRight(cC) + xLeft(cP)) / 2
          lines.push(`M${xRight(cC)},${cy} H${midX} V${py} H${xLeft(cP)}`)
        } else {
          const midX = (xRight(cP) + xLeft(cC)) / 2
          lines.push(`M${xLeft(cC)},${cy} H${midX} V${py} H${xRight(cP)}`)
        }
      })
    })
  }

  // Champion node, centred below the Final with a short vertical stub.
  const finalSlot = slots[rounds[finalR]]?.[0]
  const champion = finalSlot?.winner
    ? { abbr: finalSlot.winner, name: finalSlot.adv?.find(x => x.abbr === finalSlot.winner)?.name || finalSlot.winner }
    : finalSlot?.adv?.[0] || null
  const finalY = centerY(finalR, 0)
  const champY = finalY + BOX_H / 2 + 24
  if (champion) {
    lines.push(`M${xLeft(finalCol) + BOX_W / 2},${finalY + BOX_H / 2} V${champY - BOX_H / 2}`)
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
            const top = centerY(r, i) - BOX_H / 2
            const lit = onPath.has(`${rnd}:${i}`)
            const mirror = sideOf(r, i) === 'R'
            const rowStyle = mirror ? { flexDirection: 'row-reverse' } : undefined

            // For non-leaf undecided slots, show the most likely participant from
            // each child feeder — "who is likely to play here" rather than "who is
            // most likely to win here," which would repeat a team across boxes.
            // A participant whose feeder tie is already decided is confirmed to be
            // here, so it carries no probability.
            let participants = null
            if (rnd !== rounds[0] && !slot.winner) {
              const cids = kidsOf(r, i)
              const topOf = ci => {
                const cs = slots[rounds[r - 1]]?.[ci]
                if (!cs) return null
                if (cs.winner) {
                  const found = cs.adv?.find(x => x.abbr === cs.winner)
                  return { abbr: cs.winner, name: found?.name || cs.winner, confirmed: true }
                }
                if (cs.adv?.length) return { ...cs.adv[0], confirmed: false }
                // R32 slot with no adv (teams not yet assigned): fall back to team_a/b
                if (cs.team_a) return { abbr: cs.team_a, name: cs.name_a, confirmed: false }
                if (cs.team_b) return { abbr: cs.team_b, name: cs.name_b, confirmed: false }
                return null
              }
              const pctOf = abbr => (slot.adv || []).find(x => x.abbr === abbr)?.p
              participants = cids.map(topOf).filter(Boolean)
                .map(t => ({ ...t, displayP: t.confirmed ? null : pctOf(t.abbr) }))
            }

            return (
              <div
                key={`${rnd}:${i}`}
                className={`br-box ${lit ? 'lit' : ''}`}
                style={{ left: xLeft(colOf(r, i)), top, width: BOX_W }}
              >
                {rnd === rounds[0] ? (
                  <>
                    <div className="br-row" style={rowStyle}>
                      <Name abbr={slot.team_a} name={slot.name_a}
                        cls={slot.winner && slot.winner !== slot.team_a ? 'out' : slot.winner === slot.team_a ? 'adv' : ''} />
                      <span className="br-sc">
                        {slot.home_score != null ? slot.home_score : ''}
                      </span>
                    </div>
                    <div className="br-row" style={rowStyle}>
                      <Name abbr={slot.team_b} name={slot.name_b}
                        cls={slot.winner && slot.winner !== slot.team_b ? 'out' : slot.winner === slot.team_b ? 'adv' : ''} />
                      <span className="br-sc">
                        {slot.away_score != null ? slot.away_score : ''}
                      </span>
                    </div>
                  </>
                ) : slot.winner ? (
                  <div className="br-row" style={rowStyle}>
                    <Name abbr={slot.winner}
                      name={slot.adv?.find(x => x.abbr === slot.winner)?.name || slot.winner}
                      cls="adv" />
                    <span className="br-sc">✓</span>
                  </div>
                ) : (
                  (participants || []).map((t, j) => (
                    <div key={t.abbr || j} className="br-row" style={rowStyle}>
                      <Name abbr={t.abbr} name={t.name} />
                      {t.displayP != null && <span className="br-p">{pct(t.displayP)}</span>}
                    </div>
                  ))
                )}
              </div>
            )
          })
        )}

        {champion && (
          <div className="br-box br-champ" style={{ left: xLeft(finalCol), top: champY - BOX_H / 2, width: BOX_W }}>
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
