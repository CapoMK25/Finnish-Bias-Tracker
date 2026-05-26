import { Hono } from 'hono';
import { db, schema } from '../db/client.js';
import { desc } from 'drizzle-orm';
export const storiesRouter = new Hono();
/**
 * GET /api/stories
 * List recent story clusters with bias distribution.
 *
 * TODO (M3): Implement once clustering is built.
 */
storiesRouter.get('/', async (c) => {
    const limit = Math.min(Number(c.req.query('limit')) || 20, 100);
    const stories = await db
        .select()
        .from(schema.clusters)
        .orderBy(desc(schema.clusters.lastSeenAt))
        .limit(limit);
    return c.json({
        data: stories,
        meta: {
            count: stories.length,
            limit,
        },
    });
});
/**
 * GET /api/stories/:id
 * Detailed cluster view with all member articles.
 *
 * TODO (M4): Add member article fetching with scores joined.
 */
storiesRouter.get('/:id', async (c) => {
    const id = c.req.param('id');
    // Stub — implement when clustering is in place
    return c.json({ data: null, message: 'Not implemented yet', id }, 501);
});
