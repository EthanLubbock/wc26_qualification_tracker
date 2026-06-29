// flags.js — map a FIFA/ESPN team code to a flag emoji.
//
// Most nations resolve through a FIFA-3 -> ISO-3166-1 alpha-2 table and are
// rendered as a regional-indicator pair. The UK home nations have no ISO-2
// code of their own, so they use the special tag-sequence flag emoji.

// FIFA (or ESPN) 3-letter code -> ISO-3166-1 alpha-2. Generous coverage so the
// flag shows regardless of which 48 teams end up qualifying.
const FIFA_TO_ISO2 = {
  ARG: 'AR', BRA: 'BR', URU: 'UY', COL: 'CO', ECU: 'EC', PER: 'PE', CHI: 'CL',
  PAR: 'PY', VEN: 'VE', BOL: 'BO',
  FRA: 'FR', ESP: 'ES', GER: 'DE', POR: 'PT', NED: 'NL', BEL: 'BE', ITA: 'IT',
  CRO: 'HR', SUI: 'CH', DEN: 'DK', POL: 'PL', SRB: 'RS', AUT: 'AT', SWE: 'SE',
  NOR: 'NO', TUR: 'TR', UKR: 'UA', CZE: 'CZ', SVK: 'SK', HUN: 'HU', ROU: 'RO',
  GRE: 'GR', IRL: 'IE', ISL: 'IS', FIN: 'FI', SVN: 'SI', ALB: 'AL', GEO: 'GE',
  KVX: 'XK', RUS: 'RU',
  MEX: 'MX', USA: 'US', CAN: 'CA', CRC: 'CR', PAN: 'PA', HON: 'HN', JAM: 'JM',
  SLV: 'SV', GUA: 'GT', TRI: 'TT', HAI: 'HT', SUR: 'SR', CUW: 'CW', NCA: 'NI',
  JPN: 'JP', KOR: 'KR', AUS: 'AU', IRN: 'IR', KSA: 'SA', QAT: 'QA', IRQ: 'IQ',
  UAE: 'AE', UZB: 'UZ', JOR: 'JO', OMA: 'OM', BHR: 'BH', CHN: 'CN', IND: 'IN',
  THA: 'TH', VIE: 'VN', NZL: 'NZ', NCL: 'NC',
  SEN: 'SN', MAR: 'MA', GHA: 'GH', CMR: 'CM', TUN: 'TN', NGA: 'NG', EGY: 'EG',
  ALG: 'DZ', CIV: 'CI', RSA: 'ZA', MLI: 'ML', CPV: 'CV', ANG: 'AO', COD: 'CD',
  GAB: 'GA', BFA: 'BF', ZAM: 'ZM', GUI: 'GN', BEN: 'BJ', UGA: 'UG', KEN: 'KE',
  TAN: 'TZ', LBY: 'LY', SUD: 'SD', MTN: 'MR', NAM: 'NA', MOZ: 'MZ', TOG: 'TG',
  ZIM: 'ZW', MWI: 'MW', MAD: 'MG',
}

// Home nations: ISO has no entry, so use the GB-subdivision tag sequences.
const SPECIAL = {
  SCO: '\u{1F3F4}\u{E0067}\u{E0062}\u{E0073}\u{E0063}\u{E0074}\u{E007F}', // 🏴 scotland
  ENG: '\u{1F3F4}\u{E0067}\u{E0062}\u{E0065}\u{E006E}\u{E0067}\u{E007F}', // 🏴 england
  WAL: '\u{1F3F4}\u{E0067}\u{E0062}\u{E0077}\u{E006C}\u{E0073}\u{E007F}', // 🏴 wales
}

const iso2ToEmoji = iso2 =>
  String.fromCodePoint(...[...iso2.toUpperCase()].map(c => 0x1f1e6 + c.charCodeAt(0) - 65))

export const flag = abbr => {
  if (!abbr) return ''
  if (SPECIAL[abbr]) return SPECIAL[abbr]
  const iso2 = FIFA_TO_ISO2[abbr]
  return iso2 ? iso2ToEmoji(iso2) : ''
}
