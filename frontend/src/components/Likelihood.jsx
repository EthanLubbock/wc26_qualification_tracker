function pct(v) {
  return v == null ? '—' : `${Math.round(v * 100)}%`
}

const SEGMENTS = [
  { key: 'win_group',  label: 'Win group',   color: 'var(--green)' },
  { key: 'runner_up',  label: 'Runner-up',   color: '#22c55e' },
  { key: 'third_in',   label: 'Via thirds',  color: 'var(--amber)' },
  { key: 'third_out',  label: '3rd (out)',   color: '#f97316' },
  { key: 'fourth_out', label: '4th (out)',   color: 'var(--red)' },
]

export default function Likelihood({ qualification }) {
  if (!qualification) return null

  const q = qualification
  const qualifyPct = Math.round((q.qualify ?? 0) * 100)

  return (
    <div className="likelihood">
      <div className="likelihood-head">
        <span className="likelihood-big">{pct(q.qualify)}</span>
        <span className="likelihood-label">chance of qualification</span>
      </div>

      <div className="likelihood-bar" title="Probability breakdown">
        {SEGMENTS.map(s => {
          const w = (q[s.key] ?? 0) * 100
          if (w < 0.5) return null
          return (
            <div
              key={s.key}
              style={{ width: `${w}%`, background: s.color }}
              title={`${s.label}: ${pct(q[s.key])}`}
            />
          )
        })}
      </div>

      <div className="likelihood-legend">
        {SEGMENTS.map(s => (
          (q[s.key] ?? 0) >= 0.005 ? (
            <span key={s.key} className="likelihood-seg">
              <span className="likelihood-swatch" style={{ background: s.color }} />
              {s.label} {pct(q[s.key])}
            </span>
          ) : null
        ))}
      </div>

      <div className="likelihood-note">
        Exact calculation · Elo strength model
      </div>
    </div>
  )
}
