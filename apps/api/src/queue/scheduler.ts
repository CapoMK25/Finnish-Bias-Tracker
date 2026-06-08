/**
 * Scrape scheduler — registers one repeatable job per source.
 *
 * Runs once on API startup. Uses BullMQ's repeatable job feature with
 * a cron-like spec. Each repeatable job has a deterministic key
 * (source slug) so re-running this function on restart is idempotent —
 * the existing schedule isn't duplicated.
 *
 * Cadence: hourly for all sources in v1. Some sources have higher
 * publication volume (Iltalehti, Helsingin Sanomat) and could justify
 * 30-minute cadence later. Some sources publish 1-2 articles/day
 * (Suomen Uutiset) and could move to 4-hour cadence to save quota.
 * Tune after observing real volumes.
 */

import { db, schema } from '../db/client.js';
import { scrapeQueue, type ScrapeJobPayload } from './scrape-queue';

const DEFAULT_CRON = '0 * * * *'; // every hour, on the hour
const DEFAULT_LIMIT = 30; // articles per scrape run

export async function registerRepeatableJobs(): Promise<void> {
  const allSources = await db.select().from(schema.sources);

  if (allSources.length === 0) {
    console.warn('scheduler_no_sources_found');
    return;
  }

  console.log('scheduler_registering_jobs', { source_count: allSources.length });

  for (const source of allSources) {
    const jobName = `scrape:${source.slug}`;
    const jobData: ScrapeJobPayload = {
      source_slug: source.slug,
      limit: DEFAULT_LIMIT,
    };

    // jobId scoping ensures repeatable jobs aren't duplicated across restarts.
    await scrapeQueue.add(jobName, jobData, {
      repeat: {
        pattern: DEFAULT_CRON,
        // Spread sources across the hour so we don't fire 11 jobs at :00
        // simultaneously. Stagger by source position.
        offset: 0,
      },
      jobId: `repeat:${source.slug}`,
    });

    console.log('scheduler_job_registered', {
      source_slug: source.slug,
      cron: DEFAULT_CRON,
      limit: DEFAULT_LIMIT,
    });
  }
}

/**
 * Remove all repeatable jobs. Used by the admin endpoint and shutdown logic.
 * Useful in dev when iterating on cron patterns.
 */
export async function removeAllRepeatableJobs(): Promise<void> {
  const repeatables = await scrapeQueue.getRepeatableJobs();
  for (const job of repeatables) {
    await scrapeQueue.removeRepeatableByKey(job.key);
    console.log('scheduler_repeatable_removed', { key: job.key });
  }
}
