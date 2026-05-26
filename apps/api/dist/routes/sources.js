import { Hono } from 'hono';
import { db, schema } from '../db/client.js';
import { eq, asc } from 'drizzle-orm';
export const sourcesRouter = new Hono();
/**
 * GET /api/sources
 * List all (non-flagged) sources with metadata.
 */
sourcesRouter.get('/', async (c) => {
    const sources = await db
        .select()
        .from(schema.sources)
        .where(eq(schema.sources.flagged, false))
        .orderBy(asc(schema.sources.biasScore), asc(schema.sources.name));
    return c.json({
        data: sources,
        meta: { count: sources.length },
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
    return c.json({ data: source[0] });
});
