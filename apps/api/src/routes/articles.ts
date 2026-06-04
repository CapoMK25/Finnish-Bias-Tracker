/**
 * GET /api/articles
 *
 * Article list with optional filters. Each article includes
 * source metadata and the latest score under the current prompt version.
 *
 * Design notes:
 *   - "Latest score per article" uses Postgres DISTINCT ON in a subquery,
 *     scanning article_scores via its (article_id, scored_at) index.
 *   - LEFT JOIN to the latest-score subquery so unscored articles can
 *     appear with score: null. Score-based filters (bias, topic)
 *     naturally exclude null-score rows via NULL comparison semantics.
 *   - Two queries per request: page + count. COUNT(*) OVER() in a single
 *     query is possible but tends to hurt performance at scale.
 *   - confidence (numeric(3,2)) returns as string from Drizzle; coerced
 *     to number in the response shape.
 *
 * Note: introduces zod + @hono/zod-validator for query parameter validation.
 * Existing routes (sources, stories) parse manually; this should be addressed in the future. 
 */

import { Hono } from 'hono';
import { zValidator } from '@hono/zod-validator';
import { z } from 'zod';
import { and, desc, eq, gte, inArray, lte, sql } from 'drizzle-orm';
import { db, schema } from '../db/client.js';

// Matches PROMPT_VERSION in apps/scrapers/src/prompts/bias_scoring.py.
// Should be incremented when the scoring prompt changes. 
const PROMPT_VERSION = 'v1.2';

// Comma-separated string to a deduplicated array; undefined if empty.
const csvSchema = z
  .string()
  .optional()
  .transform((s) => {
    if (!s) return undefined;
    const parts = s.split(',').map((p) => p.trim()).filter(Boolean);
    return parts.length === 0 ? undefined : Array.from(new Set(parts));
  });

const querySchema = z.object({
  source: csvSchema,
  bias_min: z.coerce.number().int().min(-3).max(3).optional(),
  bias_max: z.coerce.number().int().min(-3).max(3).optional(),
  topic: csvSchema,
  language: csvSchema,
  from: z.coerce.date().optional(),
  to: z.coerce.date().optional(),
  limit: z.coerce.number().int().min(1).max(200).default(50),
  offset: z.coerce.number().int().min(0).default(0),
  order: z
    .enum(['published_desc', 'published_asc', 'bias_asc', 'bias_desc'])
    .default('published_desc'),
});

export const articlesRouter = new Hono();

articlesRouter.get('/', zValidator('query', querySchema), async (c) => {
  const q = c.req.valid('query');

  // Latest score per article for the current prompt version.
  const latestScores = db
    .selectDistinctOn([schema.articleScores.articleId], {
      articleId: schema.articleScores.articleId,
      bias: schema.articleScores.biasScore,
      confidence: schema.articleScores.confidence,
      topic: schema.articleScores.topic,
      summary: schema.articleScores.summary,
      promptVersion: schema.articleScores.promptVersion,
      scoredAt: schema.articleScores.scoredAt,
    })
    .from(schema.articleScores)
    .where(eq(schema.articleScores.promptVersion, PROMPT_VERSION))
    .orderBy(schema.articleScores.articleId, desc(schema.articleScores.scoredAt))
    .as('latest_scores');

  // Build WHERE clause from optional filters.
  const filters = [];

  if (q.source && q.source.length > 0) {
    filters.push(inArray(schema.sources.slug, q.source));
  }
  if (q.language && q.language.length > 0) {
    filters.push(inArray(schema.articles.language, q.language));
  }
  if (q.from) {
    filters.push(gte(schema.articles.publishedAt, q.from));
  }
  if (q.to) {
    filters.push(lte(schema.articles.publishedAt, q.to));
  }
  if (q.bias_min !== undefined) {
    filters.push(gte(latestScores.bias, q.bias_min));
  }
  if (q.bias_max !== undefined) {
    filters.push(lte(latestScores.bias, q.bias_max));
  }
  if (q.topic && q.topic.length > 0) {
    filters.push(inArray(latestScores.topic, q.topic));
  }

  const whereClause = filters.length > 0 ? and(...filters) : undefined;

  // Ordering. published_at and bias are both nullable, so NULLS LAST
  // for both directions to keep unscored/unpublished rows at the bottom.
  let orderClause;
  switch (q.order) {
    case 'published_asc':
      orderClause = sql`${schema.articles.publishedAt} ASC NULLS LAST`;
      break;
    case 'bias_asc':
      orderClause = sql`${latestScores.bias} ASC NULLS LAST`;
      break;
    case 'bias_desc':
      orderClause = sql`${latestScores.bias} DESC NULLS LAST`;
      break;
    case 'published_desc':
    default:
      orderClause = sql`${schema.articles.publishedAt} DESC NULLS LAST`;
      break;
  }

  // Main paginated query.
  const rows = await db
    .select({
      articleId: schema.articles.id,
      url: schema.articles.url,
      title: schema.articles.title,
      publishedAt: schema.articles.publishedAt,
      language: schema.articles.language,
      articleType: schema.articles.articleType,
      sourceSlug: schema.sources.slug,
      sourceName: schema.sources.name,
      sourceBias: schema.sources.biasScore,
      sourceLanguage: schema.sources.language,
      scoreBias: latestScores.bias,
      scoreConfidence: latestScores.confidence,
      scoreTopic: latestScores.topic,
      scoreSummary: latestScores.summary,
      scorePromptVersion: latestScores.promptVersion,
      scoreScoredAt: latestScores.scoredAt,
    })
    .from(schema.articles)
    .innerJoin(schema.sources, eq(schema.articles.sourceId, schema.sources.id))
    .leftJoin(latestScores, eq(schema.articles.id, latestScores.articleId))
    .where(whereClause)
    .orderBy(orderClause)
    .limit(q.limit)
    .offset(q.offset);

  // Total count for pagination metadata.
  const totalResult = await db
    .select({ count: sql<number>`COUNT(DISTINCT ${schema.articles.id})::int` })
    .from(schema.articles)
    .innerJoin(schema.sources, eq(schema.articles.sourceId, schema.sources.id))
    .leftJoin(latestScores, eq(schema.articles.id, latestScores.articleId))
    .where(whereClause);

  const total = totalResult[0]?.count ?? 0;

  // Reshape to documented response.
  const articles = rows.map((r) => ({
    id: r.articleId,
    url: r.url,
    title: r.title,
    published_at: r.publishedAt?.toISOString() ?? null,
    language: r.language,
    article_type: r.articleType,
    source: {
      slug: r.sourceSlug,
      name: r.sourceName,
      bias: r.sourceBias,
      language: r.sourceLanguage,
    },
    score:
      r.scoreBias !== null && r.scoreBias !== undefined
        ? {
            bias: r.scoreBias,
            confidence: Number(r.scoreConfidence),
            topic: r.scoreTopic ?? 'other',
            summary: r.scoreSummary ?? '',
            prompt_version: r.scorePromptVersion as string,
            scored_at: (r.scoreScoredAt as Date).toISOString(),
          }
        : null,
  }));

  c.header('Cache-Control', 'public, max-age=60');

  return c.json({
    data: articles,
    meta: {
      total,
      limit: q.limit,
      offset: q.offset,
    },
  });
});
