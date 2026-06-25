function stepText(step) {
  if (step.is_target) {
    return step.outcome.charAt(0).toUpperCase() + step.outcome.slice(1)
  }
  if (step.outcome === 'draw') {
    return `${step.home_name} and ${step.away_name} draw`
  }
  return step.outcome  // "{Team} win" already includes team name
}

function stepClass(step) {
  if (!step.is_target) return ''
  if (step.outcome === 'win') return 'path-win'
  if (step.outcome === 'draw') return 'path-draw'
  return 'path-lose'
}

export default function Paths({ paths, scenarios }) {
  if (!paths || paths.length === 0) return null
  if (!scenarios || scenarios.phase === 'final' || scenarios.clinched || scenarios.dead) return null

  return (
    <>
      <h2 className="section">How to qualify</h2>
      <div className="paths">
        {paths.map((path, i) => (
          <div key={i} className="path-row">
            <span className="path-rank">{i + 1}</span>
            <div className="path-steps">
              {path.steps.map((step, j) => (
                <span key={j} className="path-step">
                  {j > 0 && <span className="path-sep">·</span>}
                  <span className={`path-outcome ${stepClass(step)}`}>
                    {stepText(step)}
                  </span>
                </span>
              ))}
            </div>
            <span className="path-pct">{Math.round(path.probability * 100)}%</span>
          </div>
        ))}
      </div>
    </>
  )
}
