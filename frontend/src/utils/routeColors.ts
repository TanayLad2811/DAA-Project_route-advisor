/**
 * Visible Spectrum color palette for evacuation routes.
 *
 * Route 0 (Primary Evacuation Route) uses the universal life-safety Emerald Green (#10b981).
 * Alternative evacuation routes (1, 2, 3...) traverse the full visible electromagnetic spectrum:
 * Red -> Orange -> Yellow -> Green -> Cyan -> Blue -> Indigo -> Violet -> Magenta.
 */

export const VISIBLE_SPECTRUM_PALETTE = [
  '#10b981', // 0: Emerald Green (Primary Route)
  '#f97316', // 1: Vibrant Orange (~600 nm)
  '#eab308', // 2: Golden Yellow (~580 nm)
  '#06b6d4', // 3: Vivid Cyan (~500 nm)
  '#3b82f6', // 4: Royal Blue (~470 nm)
  '#6366f1', // 5: Deep Indigo (~440 nm)
  '#a855f7', // 6: Electric Violet (~410 nm)
  '#ec4899', // 7: Bright Magenta (~390 nm)
  '#ef4444', // 8: Crimson Red (~660 nm)
  '#84cc16', // 9: Radiant Lime (~540 nm)
  '#14b8a6', // 10: Aqua Teal (~510 nm)
  '#f43f5e', // 11: Vibrant Rose (~640 nm)
]

export const VISIBLE_SPECTRUM_NAMES = [
  'Emerald (Primary)',
  'Orange',
  'Yellow',
  'Cyan',
  'Blue',
  'Indigo',
  'Violet',
  'Magenta',
  'Red',
  'Lime',
  'Teal',
  'Rose',
]

/**
 * Returns a high-contrast visible spectrum hex or hsl color for a given route index.
 */
export function getRouteColor(routeIndex: number, totalRoutes: number = 1): string {
  if (routeIndex === 0) {
    return '#10b981' // Primary route always gets emerald green
  }

  if (routeIndex < VISIBLE_SPECTRUM_PALETTE.length) {
    return VISIBLE_SPECTRUM_PALETTE[routeIndex]
  }

  // Spreads remaining routes evenly across the visible hue wheel
  const hue = Math.round(((routeIndex - 1) * 360) / Math.max(1, totalRoutes - 1)) % 360
  return `hsl(${hue}, 90%, 55%)`
}

export function getRouteSpectrumName(routeIndex: number): string {
  if (routeIndex < VISIBLE_SPECTRUM_NAMES.length) {
    return VISIBLE_SPECTRUM_NAMES[routeIndex]
  }
  return `Spectrum #${routeIndex}`
}

