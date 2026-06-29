const pct = p => {
  const v = (p || 0) * 100
  if (v > 0 && v < 1) return '<1%'
  return Math.round(v) + '%'
}

// Color the percentage text based on how meaningful the odds are.
const pClass = p => p >= 0.15 ? 'p-high' : p >= 0.07 ? 'p-mid' : ''

export default function TitleOdds({ titleOdds, target }) {
  if (!titleOdds || titleOdds.length === 0) return null
  const max = titleOdds[0]?.p || 1
  return (
    <table className="title-odds">
      <thead>
        <tr><th className="rk">#</th><th>Team</th><th>Title odds</th></tr>
      </thead>
      <tbody>
        {titleOdds.map((t, i) => (
          <tr key={t.abbr} className={t.abbr === target ? 'sco' : ''}>
            <td className={`rk ${i === 0 ? 'rk-gold' : ''}`}>{i + 1}</td>
            <td className="team">{t.name || t.abbr}</td>
            <td className="to-cell">
              <div className="to-track">
                <div
                  className="to-bar"
                  style={{ width: `${Math.max(4, (t.p / max) * 100)}%` }}
                />
              </div>
              <span className="to-pct">{pct(t.p)}</span>
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  )
}
