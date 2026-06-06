import { error } from '@sveltejs/kit';
import type { PageServerLoad } from './$types';
import { env } from '$env/dynamic/private';

/**
 * Server-side load for the article detail page.
 *
 * Calls /api/articles/:id which returns the article body and complete
 * score history (all prompt versions, ordered scored_at desc). The
 * latest score is scores[0]; older scores form the history section.
 *
 * On 404 from the API, throws error(404, ...) so SvelteKit renders
 * the error page. Other errors (network, 500) bubble as 500s.
 */
export const load: PageServerLoad = async ({ fetch, params }) => {
  const apiUrl = env.API_URL ?? 'http://localhost:3000';
  const { id } = params;

  // Quick sanity check — the API also validates UUIDs and returns 400,
  // but checking here avoids the round trip for obvious nonsense.
  const uuidRegex = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
  if (!uuidRegex.test(id)) {
    throw error(404, 'Article not found');
  }

  const res = await fetch(`${apiUrl}/api/articles/${id}`);

  if (res.status === 404) {
    throw error(404, 'Article not found');
  }
  if (!res.ok) {
    throw error(res.status, `API returned ${res.status}`);
  }

  const json = await res.json();
  return {
    article: json.data,
  };
};