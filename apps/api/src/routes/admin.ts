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
import { scrapeQueue, type ScrapeJobPayload } from '../queue/scrape-queue';
import { db, schema } from '../db/client.js';
import { eq } from 'drizzle-orm';

export const adminRoutes = new Hono();

/**
 * POST /api/admin/scrape
 * Body: { source_slug: string, limit?: number }
 *
 * Adds a one-shot scrape job to the queue. Returns the BullMQ job ID
 * so the caller can track it (when #25 monitoring endpoint lands).
 */
adminRoutes.post('/scrape', async (c) => {
  const body = await c.req.json<ScrapeJobPayload>();

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
    return c.json(
      { error: `Unknown source: ${body.source_slug}` },
      404,
    );
  }

  const job = await scrapeQueue.add(
    `scrape:${body.source_slug}:adhoc`,
    {
      source_slug: body.source_slug,
      limit: body.limit ?? 20,
    },
    {
      // Ad-hoc jobs don't need the repeatable's deterministic ID
      jobId: undefined,
    },
  );

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
  const counts = await scrapeQueue.getJobCounts(
    'waiting',
    'active',
    'completed',
    'failed',
    'delayed',
  );

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
