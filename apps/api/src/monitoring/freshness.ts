export type Freshness = 'fresh' | 'stale' | 'critical' | 'never';

export interface FreshnessResult {
  freshness: Freshness;
  minutes_since_last_score: number | null;
}

export function classifyFreshness(lastScoreAt: string | null): FreshnessResult {
  if (!lastScoreAt) {
    return { freshness: 'never', minutes_since_last_score: null };
  }

  const lastMs = new Date(lastScoreAt).getTime();
  const nowMs = Date.now();
  const minutes = Math.floor((nowMs - lastMs) / 60_000);

  let freshness: Freshness;
  if (minutes < 120) {
    freshness = 'fresh';
  } else if (minutes < 360) {
    freshness = 'stale';
  } else {
    freshness = 'critical';
  }

  return { freshness, minutes_since_last_score: minutes };
}