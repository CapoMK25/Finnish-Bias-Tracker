import { eq, desc, not } from 'drizzle-orm';
import { db } from '../client.js';
import { clusters, articles, sources } from '../schema';
export async function getRecentClusters(limit = 50) {
    return await db
        .select()
        .from(clusters)
        .where(not(eq(clusters.title, 'Pending Title Assignment')))
        .orderBy(desc(clusters.lastSeenAt))
        .limit(limit);
}
export async function getClusterWithArticles(clusterId) {
    const clusterMetadata = await db
        .select()
        .from(clusters)
        .where(eq(clusters.id, clusterId))
        .limit(1);
    if (clusterMetadata.length === 0) {
        return null;
    }
    const clusterArticles = await db
        .select({
        id: articles.id,
        title: articles.title,
        url: articles.url,
        publishedAt: articles.publishedAt,
        sourceName: sources.name,
        sourceBias: sources.biasScore,
    })
        .from(articles)
        .innerJoin(sources, eq(articles.sourceId, sources.id))
        .where(eq(articles.clusterId, clusterId));
    return {
        ...clusterMetadata[0],
        articles: clusterArticles,
    };
}
