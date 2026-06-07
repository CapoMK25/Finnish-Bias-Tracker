/**
 * Threshold for showing a "still loading..." hint during slow client
 * fetches. State must live in the component (Svelte 5 runes are
 * compile-time and only work in .svelte / .svelte.ts files).
 */
export const SLOW_THRESHOLD_MS = 3000;