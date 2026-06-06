import type { PageServerLoad } from './$types';
import { env } from '$env/dynamic/private';

/**
 * Server-side load for /methodology.
 *
 * Fetches the source inventory from /api/sources so the methodology
 * page's source table stays in sync with the DB. The prompt itself
 * is hardcoded in the page component — when the prompt version bumps
 * in apps/scrapers/src/prompts/bias_scoring.py, also update the
 * page's prompt code block. This is documented in the bias_scoring.py
 * header comment.
 *
 * Future improvement: serve the prompt via /api/methodology/prompt
 * to remove the manual-sync step.
 */
export const load: PageServerLoad = async ({ fetch }) => {
  const apiUrl = env.API_URL ?? 'http://localhost:3000';

  try {
    const res = await fetch(`${apiUrl}/api/sources`);
    if (!res.ok) {
      console.error(`Sources API returned ${res.status}`);
      return { sources: [], loadError: true };
    }
    const json = await res.json();
    return { sources: json.data };
  } catch (e) {
    console.error('Failed to load sources for the methodology page:', e);
    return { sources: [], loadError: true };
  }
};