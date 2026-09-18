import { Hono } from 'hono';
import { db, schema } from '../db/client.js';
import { eq, asc, sql } from 'drizzle-orm';
export const sourcesRouter = new Hono();
/**
 * GET /api/sources
 *
 * List all (non-flagged) sources with article counts. Used by the
 * frontend for source filter dropdowns and the source comparison page.
 * Sorted by bias ascending so left-leaning sources appear first.
 *
 * `article_count` is the total number of articles per source in the DB,
 * regardless of whether they've been scored. Frontend uses this as a
 * UI hint (e.g., "Suomenmaa (12 articles)" in a dropdown).
 *
 * All sources are Finland-based publications (including Swedish-language
 * outlets like HBL and Svenska Yle), so no country field is exposed.
 * The project is Finnish-only by design; if non-Finnish sources are
 * added later, the sources schema will need a country column first.
 * For now, the language field is sufficient to distinguish Swedish-language sources.
 */
sourcesRouter.get('/', async (c) => {
    const rows = await db
        .select({
        slug: schema.sources.slug,
        name: schema.sources.name,
        bias: schema.sources.biasScore,
        language: schema.sources.language,
        article_count: sql `COUNT(${schema.articles.id})::int`,
    })
        .from(schema.sources)
        .leftJoin(schema.articles, eq(schema.articles.sourceId, schema.sources.id))
        .where(eq(schema.sources.flagged, false))
        .groupBy(schema.sources.id, schema.sources.slug, schema.sources.name, schema.sources.biasScore, schema.sources.language)
        .orderBy(asc(schema.sources.biasScore), asc(schema.sources.name));
    c.header('Cache-Control', 'public, max-age=60');
    return c.json({
        data: rows,
        meta: { count: rows.length },
    });
});
/**
 * GET /api/sources/:slug
 * Source profile.
 */
sourcesRouter.get('/:slug', async (c) => {
    const slug = c.req.param('slug');
    const source = await db
        .select()
        .from(schema.sources)
        .where(eq(schema.sources.slug, slug))
        .limit(1);
    if (source.length === 0) {
        return c.json({ error: 'Source not found' }, 404);
    }
    c.header('Cache-Control', 'public, max-age=60');
    return c.json({ data: source[0] });
});
