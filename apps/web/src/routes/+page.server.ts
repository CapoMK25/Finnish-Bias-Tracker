import { error } from '@sveltejs/kit';
import type { PageServerLoad } from './$types';
import { env } from '$env/dynamic/private';

const PAGE_SIZE = 20;

/**
 * Server-side load for the landing page.
 *
 * Reads filter state from URL query params and forwards to the
 * Hono API. Filter param shape matches the API endpoint's contract
 * directly — no translation layer, so URLs are debuggable and the
 * frontend doesn't accumulate filter abstractions the API doesn't
 * have.
 *
 * The exception is `range` (7d / 30d / unset for all time). The
 * shortcut keeps the URL clean; we compute the corresponding
 * `from` date here before calling the API.
 */
export const load: PageServerLoad = async ({ fetch, url }) => {
  const apiUrl = env.API_URL ?? 'http://localhost:3000';

  // Build the API request URL by forwarding relevant params verbatim.
  // The API validates everything it receives via zod, so we don't
  // need to validate twice — pass through and let the API reject
  // bad input with 400.
  const apiParams = new URLSearchParams();
  apiParams.set('limit', String(PAGE_SIZE));
  apiParams.set('offset', '0');

  const passthrough = ['source', 'bias_min', 'bias_max', 'topic', 'language'];
  for (const key of passthrough) {
    const value = url.searchParams.get(key);
    if (value && value.length > 0) {
      apiParams.set(key, value);
    }
  }

  // Date range shortcut → from date.
  const range = url.searchParams.get('range');
  if (range === '7d') {
    const d = new Date();
    d.setDate(d.getDate() - 7);
    apiParams.set('from', d.toISOString().split('T')[0]);
  } else if (range === '30d') {
    const d = new Date();
    d.setDate(d.getDate() - 30);
    apiParams.set('from', d.toISOString().split('T')[0]);
  }

  try {
    const [articlesRes, sourcesRes] = await Promise.all([
      fetch(`${apiUrl}/api/articles?${apiParams.toString()}`),
      fetch(`${apiUrl}/api/sources`),
    ]);

    if (!articlesRes.ok) {
      throw error(articlesRes.status, `Articles API returned ${articlesRes.status}`);
    }
    if (!sourcesRes.ok) {
      throw error(sourcesRes.status, `Sources API returned ${sourcesRes.status}`);
    }

    const articlesJson = await articlesRes.json();
    const sourcesJson = await sourcesRes.json();

    return {
      articles: articlesJson.data,
      total: articlesJson.meta.total,
      pageSize: PAGE_SIZE,
      sources: sourcesJson.data,
      filters: {
        source: url.searchParams.get('source')?.split(',').filter(Boolean) ?? [],
        biasMin: url.searchParams.get('bias_min'),
        biasMax: url.searchParams.get('bias_max'),
        topic: url.searchParams.get('topic')?.split(',').filter(Boolean) ?? [],
        language: url.searchParams.get('language') ?? '',
        range: url.searchParams.get('range') ?? '',
      },
    };
  } catch (e) {
    console.error('Failed to load articles:', e);
    return {
      articles: [],
      total: 0,
      pageSize: PAGE_SIZE,
      sources: [],
      loadError: true,
      filters: {
        source: [],
        biasMin: null,
        biasMax: null,
        topic: [],
        language: '',
        range: '',
      },
    };
  }
};