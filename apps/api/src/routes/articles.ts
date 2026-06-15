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
import { and, desc, eq, gte, inArray, lte, sql, arrayOverlaps } from 'drizzle-orm';
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
      topic: schema.articleScores.topics,
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
    filters.push(sql`${latestScores.topic}::text[] && ${q.topic}::text[]`);
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
      scoreTopics: latestScores.topic,
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
            topics: r.scoreTopics ?? ['other'],
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

/**
 * GET /api/articles/:id
 *
 * Returns one article with a full body and a complete score history
 * (all prompt versions, ordered newest first). Used by the frontend
 * article detail page to show "scored +1 under v1.0, +2 under v1.2"
 * version comparisons.
 *
 * Returns 404 if the article doesn't exist, 400 if the id is malformed.
 *
 * Two queries:
 *   1. Article + source (single join)
 *   2. All scores for the article, ordered scored_at desc
 *
 * Could be one query with json_agg() of scores, but two clean queries
 * read better and Postgres handles them in ~1ms each at this scale.
 */
articlesRouter.get('/:id', async (c) => {
  const id = c.req.param('id');

  // UUID format sanity check before hitting the DB. Drizzle will throw
  // on a malformed UUID anyway, but returning a clean 400 is friendlier
  // than letting the DB error bubble up as 500.
  const uuidRegex = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
  if (!uuidRegex.test(id)) {
    return c.json({ error: 'Invalid article id' }, 400);
  }

  // Article + source
  const articleRows = await db
    .select({
      articleId: schema.articles.id,
      url: schema.articles.url,
      title: schema.articles.title,
      body: schema.articles.body,
      publishedAt: schema.articles.publishedAt,
      scrapedAt: schema.articles.scrapedAt,
      language: schema.articles.language,
      articleType: schema.articles.articleType,
      sourceSlug: schema.sources.slug,
      sourceName: schema.sources.name,
      sourceBias: schema.sources.biasScore,
      sourceLanguage: schema.sources.language,
    })
    .from(schema.articles)
    .innerJoin(schema.sources, eq(schema.articles.sourceId, schema.sources.id))
    .where(eq(schema.articles.id, id))
    .limit(1);

  const [article] = articleRows;
    if (!article) {
    return c.json({ error: 'Article not found' }, 404);
    }

  // All scores for this article, newest first.
  const scoreRows = await db
    .select({
      bias: schema.articleScores.biasScore,
      confidence: schema.articleScores.confidence,
      rationale: schema.articleScores.rationale,
      examples: schema.articleScores.examples,
      topics: schema.articleScores.topics,
      summary: schema.articleScores.summary,
      model: schema.articleScores.model,
      promptVersion: schema.articleScores.promptVersion,
      scoredAt: schema.articleScores.scoredAt,
    })
    .from(schema.articleScores)
    .where(eq(schema.articleScores.articleId, id))
    .orderBy(desc(schema.articleScores.scoredAt));

  const scores = scoreRows.map((s) => ({
    bias: s.bias,
    confidence: Number(s.confidence),
    rationale: s.rationale,
    examples: s.examples,
    topics: s.topics ?? ['other'],
    summary: s.summary ?? '',
    article_type: article.articleType,
    model: s.model,
    prompt_version: s.promptVersion,
    provider: s.model.startsWith('gemini')
      ? 'gemini'
      : s.model.startsWith('claude')
        ? 'anthropic'
        : 'unknown',
    scored_at: s.scoredAt.toISOString(),
  }));

  c.header('Cache-Control', 'public, max-age=60');

  return c.json({
    data: {
      id: article.articleId,
      url: article.url,
      title: article.title,
      body: article.body,
      published_at: article.publishedAt?.toISOString() ?? null,
      scraped_at: article.scrapedAt.toISOString(),
      language: article.language,
      article_type: article.articleType,
      source: {
        slug: article.sourceSlug,
        name: article.sourceName,
        bias: article.sourceBias,
        language: article.sourceLanguage,
      },
      scores,
    },
  });
});
