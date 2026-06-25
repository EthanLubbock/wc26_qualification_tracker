import { ord } from '../helpers.js'

const VERDICT_UI = {
  win_group:  { cls: 'win',  pill: 'QUALIFIED',         pillCls: 'qual', big: 'Won group'     },
  runner_up:  { cls: 'win',  pill: 'QUALIFIED',         pillCls: 'qual', big: 'Qualified 2nd' },
  third_in:   { cls: 'draw', pill: 'IN — TOP 8',        pillCls: 'in',   big: '3rd — in'      },
  third_out:  { cls: 'lose', pill: 'OUT',               pillCls: 'out',  big: '3rd — out'     },
  fourth_out: { cls: 'lose', pill: 'OUT',               pillCls: 'out',  big: '4th — out'     },
}

function OutcomePanel({ label, oc }) {
  if (!oc) return null
  const ui = VERDICT_UI[oc.verdict] || { cls: '', pill: oc.verdict, pillCls: '', big: oc.verdict }
  return (
    <div className={`panel ${ui.cls}`}>
      <h3>
        {label}
        <span className={`pill ${ui.pillCls}`}>{ui.pill}</span>
      </h3>
      <div className="big">{ui.big}</div>
      {oc.third_rank && (
        <div className="sub">
          {ord(oc.third_rank)} of 12 thirds
          {oc.assumed && <span className="note"> · assumes 1-goal margin</span>}
        </div>
      )}
      {!oc.third_rank && oc.assumed && (
        <div className="note">Assumes 1-goal margin</div>
      )}
    </div>
  )
}

function FinalPanel({ verdict, third_rank }) {
  const ui = VERDICT_UI[verdict] || { cls: '', pill: verdict, pillCls: '', big: verdict }
  return (
    <div className={`panel ${ui.cls}`} style={{ gridColumn: '1 / -1' }}>
      <h3>Final standing <span className={`pill ${ui.pillCls}`}>{ui.pill}</span></h3>
      <div className="big">{ui.big}</div>
      {third_rank && <div className="sub">{ord(third_rank)} of 12 thirds</div>}
    </div>
  )
}

export default function Scenarios({ scenarios }) {
  if (!scenarios) return null

  if (scenarios.phase === 'final') {
    return (
      <div className="grid3">
        <FinalPanel verdict={scenarios.verdict} third_rank={scenarios.third_rank} />
      </div>
    )
  }

  if (scenarios.clinched) {
    return (
      <div className="panel win" style={{ gridColumn: '1 / -1', textAlign: 'center' }}>
        <div className="big">Already qualified</div>
        <div className="sub">Remaining result only affects group seeding.</div>
      </div>
    )
  }

  if (scenarios.dead) {
    return (
      <div className="panel lose" style={{ gridColumn: '1 / -1', textAlign: 'center' }}>
        <div className="big">Eliminated</div>
        <div className="sub">No path to the Round of 32 remains.</div>
      </div>
    )
  }

  const { win, draw, loss } = scenarios.outcomes || {}
  return (
    <div className="grid3">
      <OutcomePanel label="Win" oc={win} />
      <OutcomePanel label="Draw" oc={draw} />
      <OutcomePanel label="Loss" oc={loss} />
    </div>
  )
}
