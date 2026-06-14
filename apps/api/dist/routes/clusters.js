import { Hono } from 'hono';
import { db, schema } from '../db/client.js';
import { eq, desc, not } from 'drizzle-orm';
export const clustersRouter = new Hono();
/**
 * GET /api/clusters
 *
 * List recent story clusters. Filters out clusters that are currently
 * in the background pipeline (missing an AI-generated title).
 */
clustersRouter.get('/', async (c) => {
    // 50 query limit here for now, might adjust in the future
    const limitParam = c.req.query('limit');
    const limit = limitParam ? parseInt(limitParam, 10) : 50;
    const rows = await db
        .select()
        .from(schema.clusters)
        .where(not(eq(schema.clusters.title, 'Pending Title Assignment')))
        .orderBy(desc(schema.clusters.lastSeenAt))
        .limit(limit);
    c.header('Cache-Control', 'public, max-age=60');
    return c.json({
        data: rows,
        meta: { count: rows.length },
    });
});
/**
 * GET /api/clusters/:id
 * * Fetch a specific cluster's metadata along with an array of all its
 * associated articles (and the bias scores of the sources that published them).
 */
clustersRouter.get('/:id', async (c) => {
    const id = c.req.param('id');
    // Basic UUID validation to prevent database query crashes on malformed strings
    const uuidRegex = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
    if (!uuidRegex.test(id)) {
        return c.json({ error: 'Invalid cluster ID format' }, 400);
    }
    // 1. Fetch the parent cluster metadata
    const clusterMetadata = await db
        .select()
        .from(schema.clusters)
        .where(eq(schema.clusters.id, id))
        .limit(1);
    if (clusterMetadata.length === 0) {
        return c.json({ error: 'Cluster not found' }, 404);
    }
    // 2. Fetch all articles in this cluster, joining sources to get the bias leaning
    const clusterArticles = await db
        .select({
        id: schema.articles.id,
        title: schema.articles.title,
        url: schema.articles.url,
        publishedAt: schema.articles.publishedAt,
        sourceName: schema.sources.name,
        sourceBias: schema.sources.biasScore,
    })
        .from(schema.articles)
        .innerJoin(schema.sources, eq(schema.articles.sourceId, schema.sources.id))
        .where(eq(schema.articles.clusterId, id));
    c.header('Cache-Control', 'public, max-age=60');
    // Combine metadata and articles into a single payload
    return c.json({
        data: {
            ...clusterMetadata[0],
            articles: clusterArticles,
        }
    });
});
