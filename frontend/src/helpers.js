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

// Normalise a match into the target team's perspective.
export function targetLine(m, target) {
  if (!m) return null
  const targetHome = m.home === target
  return {
    opp: targetHome ? m.away_name || m.away : m.home_name || m.home,
    targetScore: targetHome ? m.home_score : m.away_score,
    oppScore: targetHome ? m.away_score : m.home_score,
    state: m.state,
    kickoff: m.kickoff,
  }
}

export const signed = n => (n >= 0 ? '+' : '') + n
