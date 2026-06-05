import { error } from '@sveltejs/kit';
import type { PageServerLoad } from './$types';
import { env } from '$env/dynamic/private';

/**
 * Server-side load for the landing page.
 *
 * Fetches the first page of articles from the Hono API.
 * Subsequent pages (via "Load more") are fetched client-side
 * through Vite's /api proxy.
 *
 * Uses $env/dynamic/private rather than $env/static/private so
 * the API_URL can change between dev/staging/prod without
 * rebuilding. Reads at runtime from process.env on the server.
 */

const PAGE_SIZE = 20;

export const load: PageServerLoad = async ({ fetch }) => {
  const apiUrl = env.API_URL ?? 'http://localhost:3000';

  try {
    const res = await fetch(`${apiUrl}/api/articles?limit=${PAGE_SIZE}&offset=0`);

    if (!res.ok) {
      throw error(res.status, `API returned ${res.status}`);
    }

    const json = await res.json();
    return {
      articles: json.data,
      total: json.meta.total,
      pageSize: PAGE_SIZE,
    };
  } catch (e) {
    // Network errors or unreachable API. Render the page with empty
    // state rather than a hard error — visitors see something useful
    // even if the backend is briefly down.
    console.error('Failed to load articles:', e);
    return {
      articles: [],
      total: 0,
      pageSize: PAGE_SIZE,
      loadError: true,
    };
  }
};
