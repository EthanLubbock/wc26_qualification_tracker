// Shows the genuinely pivotal other-group games for a third-place qualification
// path, and how many of them must go the target's way (BBC-style). Backend has
// already filtered out results that don't change the target's fate.

export default function Requirements({ requirements, scenarios }) {
  if (!requirements) return null
  if (!scenarios) return null

  // Only show while a third-place decision is genuinely live.
  if (scenarios.phase === 'pending') {
    if (scenarios.clinched || scenarios.dead) return null
  } else if (scenarios.phase === 'final') {
    const v = scenarios.verdict
    if (v !== 'third_in' && v !== 'third_out') return null
  } else {
    return null
  }

  const { need, settled_favourable, groups, conditional, tie_warning } = requirements
  if (!groups || groups.length === 0) {
    // No contested groups left: fate already decided among thirds.
    return null
  }

  return (
    <>
      <h2 className="section">
        {conditional ? 'If you finish 3rd — results you need' : 'Results needed to qualify'}
      </h2>

      <div className="req-need">
        Need at least <strong>{need}</strong> of the {groups.length} game
        {groups.length === 1 ? '' : 's'} below to go your way
        {settled_favourable > 0 && (
          <span className="req-settled">
            {' '}· {settled_favourable} already in your favour
          </span>
        )}
      </div>

      <div className="paths">
        {groups.map((g) => (
          <div key={g.group} className="path-row">
            <span className="path-rank">{g.group}</span>
            <div className="path-steps">
              <span className="path-outcome">{g.description}</span>
            </div>
            <span className="path-pct">{Math.round(g.probability * 100)}%</span>
          </div>
        ))}
      </div>

      {tie_warning && (
        <div className="req-note">
          Some outcomes could come down to the FIFA fair-play / ranking tiebreak,
          which isn't in the live feed.
        </div>
      )}
    </>
  )
}
