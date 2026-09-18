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
const DEFAULT_LIMIT = 10; // articles per scrape run

export async function registerRepeatableJobs(): Promise<void> {
  console.log('[Scheduler] Checking for existing automated scraping schedules...');
  const allSources = await db.select().from(schema.sources);

  if (allSources.length === 0) {
    console.warn('scheduler_no_sources_found');
    return;
  }

  console.log('scheduler_registering_jobs', { source_count: allSources.length });

  // MODIFICATION: Swapped out for..of loop for a destructured for..of loop containing entries().
  // WHY: Access to the loop index 'i' to implement the staggered execution offset.
  for (const [i, source] of allSources.entries()) {
    const jobName = `scrape:${source.slug}`;
    const jobData: ScrapeJobPayload = {
      source_slug: source.slug,
      limit: DEFAULT_LIMIT,
    };

    // ADDITION: Added mathematical staggering interval using the loop index.
    // WHY: Spacing each job deployment 2 minutes apart (e.g., 0ms, 120000ms, 240000ms) directly 
    // satisfies the comment block intent. This prevents resource spikes when processing elements synchronously.
    const staggeredOffsetMs = i * 2 * 60 * 1000;

    // jobId scoping ensures repeatable jobs aren't duplicated across restarts.
    await scrapeQueue.add(jobName, jobData, {
      repeat: {
        pattern: DEFAULT_CRON,
        // MODIFICATION: Swapped out static 0 for the dynamically computed time shift variable.
        offset: staggeredOffsetMs,
      },
      jobId: `repeat:${source.slug}`,
    });

    console.log('scheduler_job_registered', {
      source_slug: source.slug,
      cron: DEFAULT_CRON,
      limit: DEFAULT_LIMIT,
      offset_ms: staggeredOffsetMs,
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
