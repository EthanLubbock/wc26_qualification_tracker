import { signed } from '../helpers.js'

export default function Ladder({ thirds, cutoff, target }) {
  return (
    <>
      <table className="ladder">
        <thead>
          <tr>
            <th className="rk">#</th><th>Team</th><th>Grp</th>
            <th>Pts</th><th>GD</th><th>GF</th>
          </tr>
        </thead>
        <tbody>
          {thirds.map((t, i) => {
            const rank = i + 1
            const cls = [
              rank <= cutoff ? 'in' : '',
              rank === cutoff ? 'cut' : '',
              t.abbr === target ? 'sco' : ''
            ].join(' ').trim()
            return (
              <tr key={`${t.abbr}-${i}`} className={cls}>
                <td className="rk">{rank}</td>
                <td className="team">
                  {t.name || t.abbr}
                  {!t.group_complete && <span className="prov">prov.</span>}
                </td>
                <td>{t.group}</td>
                <td>{t.points}</td>
                <td>{signed(t.gd)}</td>
                <td>{t.gf}</td>
              </tr>
            )
          })}
        </tbody>
      </table>
      <div className="cutnote">
        {thirds.length
          ? 'Dashed line = top-8 cut-off. "prov." = group not finished, so that row can still change.'
          : 'No third-placed teams yet — table fills in as groups play their final games.'}
      </div>
    </>
  )
}
