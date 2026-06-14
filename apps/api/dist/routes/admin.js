/**
 * Admin endpoints — manual queue management.
 *
 * v1 scope (this PR): ad-hoc scrape trigger.
 * #25 adds the full health endpoint (queue depth, last successful scrape
 * per source, etc.).
 *
 * These endpoints should be authenticated in production. For local dev
 * they're unprotected. When deploying (#M6), wrap with auth middleware
 * before exposing publicly.
 */
import { Hono } from 'hono';
import { pingQueue, scrapeQueue } from '../queue/scrape-queue';
import { db, schema } from '../db/client.js';
import { eq } from 'drizzle-orm';
import { listFailedJobs, retryFailedJob, retryAllFailedJobs, } from '../queue/failed-jobs.js';
import { getScoringStats, getSourceHealth, pingDatabase, } from '../monitoring/queries.js';
import { classifyFreshness } from '../monitoring/freshness.js';
// Cache the process start time once at module load
const PROCESS_START_MS = Date.now();
export const adminRoutes = new Hono();
/**
 * POST /api/admin/scrape
 * Body: { source_slug: string, limit?: number }
 *
 * Adds a one-shot scrape job to the queue. Returns the BullMQ job ID
 * so the caller can track it (when #25 monitoring endpoint lands).
 */
adminRoutes.post('/scrape', async (c) => {
    const body = await c.req.json();
    if (!body.source_slug) {
        return c.json({ error: 'source_slug is required' }, 400);
    }
    // Validate the source exists in the DB
    const [source] = await db
        .select()
        .from(schema.sources)
        .where(eq(schema.sources.slug, body.source_slug))
        .limit(1);
    if (!source) {
        return c.json({ error: `Unknown source: ${body.source_slug}` }, 404);
    }
    const job = await scrapeQueue.add(`scrape:${body.source_slug}:adhoc`, {
        source_slug: body.source_slug,
        limit: body.limit ?? 20,
    }, {
        // Ad-hoc jobs don't need the repeatable's deterministic ID
        jobId: undefined,
    });
    console.log('admin_scrape_triggered', {
        source_slug: body.source_slug,
        limit: body.limit ?? 20,
        job_id: job.id,
    });
    return c.json({
        job_id: job.id,
        source_slug: body.source_slug,
        queued_at: new Date().toISOString(),
    });
});
/**
 * GET /api/admin/queue/stats
 * Quick view of queue state. Useful for verifying jobs are landing.
 * #25 expands this into the full monitoring endpoint.
 */
adminRoutes.get('/queue/stats', async (c) => {
    const counts = await scrapeQueue.getJobCounts('waiting', 'active', 'completed', 'failed', 'delayed');
    const repeatables = await scrapeQueue.getRepeatableJobs();
    return c.json({
        queue_name: 'scrape-jobs',
        counts,
        repeatable_jobs: repeatables.map((j) => ({
            name: j.name,
            pattern: j.pattern,
            next_run: j.next ? new Date(j.next).toISOString() : null,
        })),
    });
});
/**
 * DELETE /api/admin/queue/repeatables
 * Clears all repeatable jobs. Useful when iterating on cron patterns
 * in dev. Don't expose in production.
 */
adminRoutes.delete('/queue/repeatables', async (c) => {
    const { removeAllRepeatableJobs } = await import('../queue/scheduler');
    await removeAllRepeatableJobs();
    return c.json({ status: 'cleared' });
});
/**
 * List failed jobs in the scrape queue, with details for debugging.
 * Useful for verifying failure modes and testing retry logic. Returns up to `limit`
 * jobs, newest first. Default limit is 50;
 */
adminRoutes.get('/queue/failed', async (c) => {
    const limit = Number(c.req.query('limit') ?? '50');
    if (Number.isNaN(limit) || limit < 1 || limit > 500) {
        return c.json({ error: 'limit must be between 1 and 500' }, 400);
    }
    try {
        const jobs = await listFailedJobs(limit);
        return c.json({
            data: jobs,
            meta: { count: jobs.length, limit },
        });
    }
    catch (err) {
        console.error('list_failed_jobs_error', err);
        return c.json({ error: err instanceof Error ? err.message : 'unknown error' }, 500);
    }
});
/**
 * Retry a specific failed job by ID.
 * Returns 404 if the job isn't found, 409 if it's not in the failed state.
 */
adminRoutes.post('/queue/failed/:jobId/retry', async (c) => {
    const jobId = c.req.param('jobId');
    if (!jobId) {
        return c.json({ error: 'jobId is required' }, 400);
    }
    try {
        await retryFailedJob(jobId);
        return c.json({ retried: jobId });
    }
    catch (err) {
        const msg = err instanceof Error ? err.message : 'unknown error';
        if (msg.includes('not found')) {
            return c.json({ error: msg }, 404);
        }
        if (msg.includes('not')) {
            return c.json({ error: msg }, 409); // wrong state
        }
        console.error('retry_failed_job_error', err);
        return c.json({ error: msg }, 500);
    }
});
/**
 * Retry all failed jobs.
 * Returns the count of jobs re-queued and any errors encountered.
 */
adminRoutes.post('/queue/failed/retry-all', async (c) => {
    try {
        const result = await retryAllFailedJobs();
        return c.json(result);
    }
    catch (err) {
        console.error('retry_all_failed_jobs_error', err);
        return c.json({ error: err instanceof Error ? err.message : 'unknown error' }, 500);
    }
});
/**
 * Monitoring endpoint: quick health check for the API and its dependencies.
 * Used by uptime monitoring services and for manual checks. The full /api/monitoring
 * endpoint (#25) expands on this with more detailed metrics and per-source health.
 */
adminRoutes.get('/health', async (c) => {
    const now = new Date();
    // Run the parallel checks in parallel
    const [db_health, queue_health, queue_counts, repeatable, scoring, source_rows] = await Promise.all([
        pingDatabase(),
        pingQueue(),
        scrapeQueue.getJobCounts('waiting', 'active', 'completed', 'failed', 'delayed', 'paused'),
        scrapeQueue.getRepeatableJobs(),
        getScoringStats(),
        getSourceHealth(),
    ]);
    const sources = source_rows.map((s) => {
        const { freshness, minutes_since_last_score } = classifyFreshness(s.last_score_at);
        return {
            slug: s.slug,
            name: s.name,
            last_article_at: s.last_article_at,
            last_score_at: s.last_score_at,
            articles_last_24h: s.articles_last_24h,
            minutes_since_last_score,
            freshness,
        };
    });
    const status = db_health.reachable && queue_health.reachable ? 'ok' : 'degraded';
    const uptime_seconds = Math.floor((Date.now() - PROCESS_START_MS) / 1000);
    return c.json({
        status,
        checked_at: now.toISOString(),
        uptime_seconds,
        database: db_health,
        queue: {
            reachable: queue_health.reachable,
            latency_ms: queue_health.latency_ms,
            counts: queue_counts,
            repeatable_jobs: repeatable.length,
        },
        scoring,
        sources,
    }, status === 'ok' ? 200 : 503);
});
