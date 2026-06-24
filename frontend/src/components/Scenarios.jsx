import { ord, signed } from '../helpers.js'

function WinPanel({ win }) {
  return (
    <div className="panel win">
      <h3>Win <span className="pill qual">QUALIFIED</span></h3>
      <div className="big" style={{ color: 'var(--green)' }}>Top 2</div>
      <div className="sub">Round of 32 secured</div>
      <div className="note">{win.detail}</div>
    </div>
  )
}

function ScenarioPanel({ sc, cls }) {
  return (
    <div className={`panel ${cls}`}>
      <h3>
        {sc.label}
        <span className={`pill ${sc.in_top8 ? 'in' : 'out'}`}>
          {sc.in_top8 ? 'IN — TOP 8' : 'OUT'}
        </span>
      </h3>
      <div className="big">3rd · {sc.sco_points} pts</div>
      <div className="sub">
        Projected {ord(sc.third_rank)} of {sc.field_size} thirds · GD {signed(sc.sco_gd)}
      </div>
      <div className="note">{sc.note}</div>
    </div>
  )
}

export default function Scenarios({ scenarios }) {
  return (
    <div className="grid3">
      <WinPanel win={scenarios.win} />
      <ScenarioPanel sc={scenarios.draw} cls="draw" />
      <ScenarioPanel sc={scenarios.lose} cls="lose" />
    </div>
  )
}
