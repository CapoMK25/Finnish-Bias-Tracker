/**
 * Canonical color tokens for the Finnish Bias Tracker frontend.
 *
 * Two parallel systems:
 *   1. SOURCE_COLOR — party-identity color, used in SourceBadge.
 *      Maps to a Finnish political color convention (red = left,
 *      blue = right, green = centre, yellow = Swedish-speaking,
 *      grey = independent).
 *   2. BIAS_COLOR — position on the -3 to +3 bias scale, used in
 *      BiasIndicator. Independent of source.
 *
 * Hex values are intentionally muted. Pure #ff0000 reads as alarm,
 * not editorial analysis. See design-system.md for the full reasoning.
 */

// Source identity colors. Keys match source slugs in the DB.
export const SOURCE_COLOR: Record<string, { bg: string; fg: string; border: string }> = {
  // Right — Kokoomus / Perussuomalaiset (blue)
  'suomen-uutiset':  { bg: '#234c8e', fg: '#ffffff', border: '#1f4177' },
  'verkkouutiset':   { bg: '#508ce7', fg: '#ffffff', border: '#407edb' },

  // Swedish-speaking minority (yellow)
  'hufvudstadsbladet': { bg: '#e3b341', fg: '#3a2c00', border: '#b88c2a' },
  'svenska-yle':       { bg: '#e3b341', fg: '#3a2c00', border: '#b88c2a' },

  // Centre — Keskusta (green)
  'suomenmaa': { bg: '#3f7d3a', fg: '#ffffff', border: '#2e5e2a' },

  // Left — Vasemmistoliitto / SDP (red)
  'kansan-uutiset': { bg: '#b32d2d', fg: '#ffffff', border: '#8c2424' },
  'demokraatti':    { bg: '#c9544d', fg: '#ffffff', border: '#a04540' },

  // Independent / mainstream (grey)
  'yle':               { bg: '#5b6470', fg: '#ffffff', border: '#454d56' },
  'helsingin-sanomat': { bg: '#5b6470', fg: '#ffffff', border: '#454d56' },
  'iltalehti':         { bg: '#5b6470', fg: '#ffffff', border: '#454d56' },
  'ilta-sanomat':      { bg: '#5b6470', fg: '#ffffff', border: '#454d56' },
};

// Bias scale colors. Index by score (-3 to 3), shifted by +3 for array access.
// score -3 -> index 0, score 0 -> index 3, score 3 -> index 6.
export const BIAS_COLOR: Array<{ bg: string; fg: string; border: string; label: string }> = [
  { bg: '#7d1d1d', fg: '#ffffff', border: '#651414', label: 'far left' },        // -3
  { bg: '#a83434', fg: '#ffffff', border: '#852828', label: 'left' },            // -2
  { bg: '#c97373', fg: '#3a0a0a', border: '#a05a5a', label: 'mild left' },       // -1
  { bg: '#a8a59f', fg: '#1f1d1a', border: '#8a8780', label: 'neutral' },         //  0
  { bg: '#7393c1', fg: '#0a1430', border: '#5878a0', label: 'mild right' },      // +1
  { bg: '#3568b3', fg: '#ffffff', border: '#2a528e', label: 'right' },           // +2
  { bg: '#1c3a6b', fg: '#ffffff', border: '#142b50', label: 'far right' },       // +3
];

export function biasColor(score: number) {
  const idx = Math.max(0, Math.min(6, score + 3));
  return BIAS_COLOR[idx];
}

export function sourceColor(slug: string) {
  return SOURCE_COLOR[slug] ?? SOURCE_COLOR['yle']; // default to grey for unknown sources
}
