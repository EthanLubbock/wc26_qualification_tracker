function stepText(step) {
  if (step.is_target) {
    return step.outcome.charAt(0).toUpperCase() + step.outcome.slice(1)
  }
  const prefix = `Group ${step.group}: `
  if (step.outcome === 'draw') {
    return `${prefix}${step.home_name} and ${step.away_name} draw`
  }
  return `${prefix}${step.outcome}`
}

function stepClass(step) {
  if (!step.is_target) return ''
  if (step.outcome === 'win') return 'path-win'
  if (step.outcome === 'draw') return 'path-draw'
  return 'path-lose'
}

export default function Paths({ paths, scenarios }) {
  if (!paths || paths.length === 0) return null
  if (!scenarios) return null

  if (scenarios.phase === 'pending') {
    if (scenarios.clinched || scenarios.dead) return null
  } else if (scenarios.phase === 'final') {
    // Only show for third-placed teams whose fate is still uncertain
    const v = scenarios.verdict
    if (v !== 'third_in' && v !== 'third_out') return null
  } else {
    return null
  }

  const hasOwnMatch = paths.some(p => p.steps.some(s => s.is_target))
  const heading = hasOwnMatch ? 'How to qualify' : 'Results needed to qualify'

  return (
    <>
      <h2 className="section">{heading}</h2>
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
