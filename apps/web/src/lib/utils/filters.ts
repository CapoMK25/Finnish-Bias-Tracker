/**
 * Filter URL helpers.
 *
 * Filters are URL-driven. These helpers build new URLs by mutating
 * search params off the current URL, preserving the rest. The
 * SvelteKit `goto()` call then triggers a server re-render via
 * the load function.
 */

import { goto } from '$app/navigation';
import { page } from '$app/state';

export function updateFilter(key: string, value: string | string[] | null) {
  const url = new URL(page.url);

  if (value === null || value === '' || (Array.isArray(value) && value.length === 0)) {
    url.searchParams.delete(key);
  } else if (Array.isArray(value)) {
    url.searchParams.set(key, value.join(','));
  } else {
    url.searchParams.set(key, value);
  }

  goto(url.pathname + url.search, {
    invalidateAll: true,
    replaceState: false,
    keepFocus: true,
    noScroll: true,
  });
}

export function clearAllFilters() {
  goto('/', {
    invalidateAll: true,
    replaceState: false,
    keepFocus: false,
    noScroll: true,
  });
}

export function countActiveFilters(filters: {
  source: string[];
  biasMin: string | null;
  biasMax: string | null;
  topic: string[];
  language: string;
  range: string;
}): number {
  let count = 0;
  if (filters.source.length > 0) count++;
  if (filters.biasMin !== null || filters.biasMax !== null) count++;
  if (filters.topic.length > 0) count++;
  if (filters.language !== '') count++;
  if (filters.range !== '') count++;
  return count;
}