import { error } from '@sveltejs/kit';
import type { PageServerLoad } from './$types';
import { env } from '$env/dynamic/private';

const DEFAULT_TOPIC = 'economic_policy';
const DEFAULT_RANGE = '30d';

const TOPICS = [
  'economic_policy',
  'immigration',
  'climate',
  'foreign_policy',
  'social_policy',
  'health',
  'education',
  'crime',
  'culture',
  'other',
];

/**
 * Server-side load for /compare.
 *
 * Fetches all sources and, for each, the articles in the selected
 * topic + date range. 11 parallel API calls — fine at this scale,
 * cleaner than a new aggregation endpoint.
 *
 * Returns:
 *   - sources: all 11 sources (for empty-coverage cards)
 *   - perSource: Map<slug, articles[]>
 *   - selected: { topic, range }
 *   - topics: hardcoded list for the dropdown
 *
 * Per-source stats (article count, average bias, histogram,
 * sample titles) are computed in the page component, not here.
 * The aggregation is O(n) and small enough to do in the render
 * path rather than pre-computing.
 */
export const load: PageServerLoad = async ({ fetch, url }) => {
  const apiUrl = env.API_URL ?? 'http://localhost:3000';

  // Parse and validate URL params with sensible defaults.
  const topic = url.searchParams.get('topic') || DEFAULT_TOPIC;
  const range = url.searchParams.get('range') || DEFAULT_RANGE;

  if (!TOPICS.includes(topic)) {
    throw error(400, `Unknown topic: ${topic}`);
  }
  if (range !== '7d' && range !== '30d' && range !== '90d' && range !== 'all') {
    throw error(400, `Unknown range: ${range}`);
  }

  // Compute the `from` date for the API call. range='all' means no date filter.
  let fromParam = '';
  if (range !== 'all') {
    const days = range === '7d' ? 7 : range === '30d' ? 30 : 90;
    const d = new Date();
    d.setDate(d.getDate() - days);
    fromParam = `&from=${d.toISOString().split('T')[0]}`;
  }

  try {
    // First: get all sources (the comparison spans every source, including
    // those with zero articles for this query).
    const sourcesRes = await fetch(`${apiUrl}/api/sources`);
    if (!sourcesRes.ok) {
      throw error(sourcesRes.status, `Sources API returned ${sourcesRes.status}`);
    }
    const sourcesJson = await sourcesRes.json();
    const sources = sourcesJson.data;

    // Then: parallel fetch of articles per source for this topic + range.
    // limit=100 is well above what any single source will produce for a
    // single topic in a 30-day window. If a future query hits the cap,
    // the histogram and average could be slightly off; tracked as a
    // follow-up if it becomes a real concern.
    const perSource: Record<string, any[]> = {};
    const fetches = sources.map(async (s: { slug: string }) => {
      const res = await fetch(
        `${apiUrl}/api/articles?source=${s.slug}&topic=${topic}&limit=100${fromParam}`
      );
      if (!res.ok) {
        // Don't fail the whole page if one source's call fails. Just
        // log and treat as empty.
        console.error(`Failed to fetch articles for ${s.slug}: ${res.status}`);
        perSource[s.slug] = [];
        return;
      }
      const json = await res.json();
      perSource[s.slug] = json.data;
    });

    await Promise.all(fetches);

    return {
      sources,
      perSource,
      selected: { topic, range },
      topics: TOPICS,
    };
  } catch (e) {
    if (e instanceof Error && 'status' in e) {
      throw e; // re-throw SvelteKit errors
    }
    console.error('Failed to load comparison data:', e);
    return {
      sources: [],
      perSource: {} as Record<string, any[]>,
      selected: { topic, range },
      topics: TOPICS,
      loadError: true,
    };
  }
};