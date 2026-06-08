/**
 * BullMQ queue for scrape jobs.
 *
 * One queue handles all 11 sources. Jobs carry a source_slug payload;
 * the Python worker (#22) consumes them and runs the appropriate scraper.
 *
 * Two ways jobs land in this queue:
 *   1. Repeatable jobs auto-scheduled by the scheduler module on a cron
 *      sequence (one per source).
 *   2. One-shot jobs added programmatically via the admin endpoint
 *      (POST /api/admin/scrape) for ad-hoc runs.
 *
 * Per-source rate limiting (#23) and dead-letter handling (#24) are
 * separate issues. This module is intentionally minimal.
 */

import { Queue } from 'bullmq';
import IORedis from 'ioredis';

const REDIS_URL = process.env.REDIS_URL ?? 'redis://localhost:6379';

// BullMQ requires maxRetriesPerRequest=null for blocking commands
// (workers use blocking reads on the queue).
export const redisConnection = new IORedis(REDIS_URL, {
  maxRetriesPerRequest: null,
});

export const QUEUE_NAME = 'scrape-jobs';

export interface ScrapeJobPayload {
  source_slug: string;
  limit?: number; // optional override; defaults applied by the worker
}

export const scrapeQueue = new Queue<ScrapeJobPayload>(QUEUE_NAME, {
  connection: redisConnection,
  defaultJobOptions: {
    // Retain completed/failed for inspection; cleanup happens via
    // removeOnComplete/removeOnFail counts to avoid unbounded growth.
    removeOnComplete: { count: 100 },
    removeOnFail: { count: 500 }, // keep failed jobs longer for debugging
    attempts: 3,
    backoff: {
      type: 'exponential',
      delay: 30_000, // 30s, 60s, 120s
    },
  },
});

/**
 * Graceful shutdown helper. Call this from API shutdown hooks.
 */
export async function closeQueue(): Promise<void> {
  await scrapeQueue.close();
  await redisConnection.quit();
}
