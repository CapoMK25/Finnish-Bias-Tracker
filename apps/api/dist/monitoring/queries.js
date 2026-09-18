import { sql } from 'drizzle-orm';
import { db } from '../db/client.js';
/**
 * Per-source freshness: when did each source last produce an article
 * and when was the most recent score for that source written?
 */
export async function getSourceHealth() {
    const rows = await db.execute(sql `
  SELECT
    s.slug,
    s.name,
    MAX(a.scraped_at) AS last_article_at,
    MAX(sc.scored_at) AS last_score_at,
    COUNT(DISTINCT a.id) FILTER (WHERE a.scraped_at > NOW() - INTERVAL '24 hours') AS articles_last_24h
  FROM sources s
  LEFT JOIN articles a ON a.source_id = s.id
  LEFT JOIN article_scores sc ON sc.article_id = a.id
  GROUP BY s.slug, s.name
  ORDER BY s.slug;
`);
    return rows.map((r) => ({
        slug: r.slug,
        name: r.name,
        last_article_at: r.last_article_at,
        last_score_at: r.last_score_at,
        articles_last_24h: Number(r.articles_last_24h),
    }));
}
/**
 * Global scoring statistics across all sources.
 */
export async function getScoringStats() {
    const rows = await db.execute(sql `
    WITH score_counts AS (
      SELECT
        COUNT(DISTINCT a.id) AS articles_total,
        COUNT(DISTINCT sc.article_id) AS scored_total,
        COUNT(DISTINCT sc.article_id) FILTER (WHERE sc.scored_at > NOW() - INTERVAL '24 hours') AS scored_last_24h,
        COUNT(DISTINCT sc.article_id) FILTER (WHERE sc.scored_at > NOW() - INTERVAL '1 hour') AS scored_last_1h
      FROM articles a
      LEFT JOIN article_scores sc ON sc.article_id = a.id
    )
    SELECT
      articles_total::text,
      scored_total::text,
      scored_last_24h::text,
      scored_last_1h::text,
      (articles_total - scored_total)::text AS unscored_count
    FROM score_counts;
  `);
    const r = rows[0];
    return {
        articles_total: Number(r?.articles_total ?? 0),
        scored_total: Number(r?.scored_total ?? 0),
        scored_last_24h: Number(r?.scored_last_24h ?? 0),
        scored_last_1h: Number(r?.scored_last_1h ?? 0),
        unscored_count: Number(r?.unscored_count ?? 0),
    };
}
/**
 * Lightweight ping to verify Postgres is reachable.
 * Returns the round-trip time in ms.
 */
export async function pingDatabase() {
    const start = Date.now();
    try {
        await db.execute(sql `SELECT 1`);
        return { reachable: true, latency_ms: Date.now() - start };
    }
    catch {
        return { reachable: false, latency_ms: Date.now() - start };
    }
}
