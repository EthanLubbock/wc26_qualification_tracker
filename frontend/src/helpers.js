// Shared formatting helpers.

export function ord(n) {
  const s = ['th', 'st', 'nd', 'rd'], v = n % 100
  return n + (s[(v - 20) % 10] || s[v] || s[0])
}

export function kotime(iso) {
  try {
    return new Date(iso).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
  } catch {
    return ''
  }
}

// Normalise a match into Scotland's perspective.
export function scoLine(m) {
  if (!m) return null
  const scoHome = m.home === 'SCO'
  return {
    opp: scoHome ? m.away : m.home,
    scoScore: scoHome ? m.home_score : m.away_score,
    oppScore: scoHome ? m.away_score : m.home_score,
    state: m.state,
    kickoff: m.kickoff
  }
}

export const signed = n => (n >= 0 ? '+' : '') + n
