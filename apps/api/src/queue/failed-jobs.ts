import type { Job } from 'bullmq';
import { scrapeQueue } from './scrape-queue.js';
import type { ScrapeJobPayload } from './scrape-queue.js';

export interface FailedJobSummary {
  id: string;
  source_slug: string;
  limit: number;
  attempts_made: number;
  failed_reason: string;
  stacktrace: string[];
  failed_at: string | null;
  added_at: string | null;
}

/**
 * List all currently-failed jobs in the scrape queue.
 * Returns up to `limit` jobs, newest-first.
 */
export async function listFailedJobs(limit = 100): Promise<FailedJobSummary[]> {
  // BullMQ's getJobs with the 'failed' state. start=0, end=limit-1, asc=false.
  const jobs: Job<ScrapeJobPayload>[] = await scrapeQueue.getJobs(
    ['failed'],
    0,
    limit - 1,
    false,
  );

  return jobs.map((job) => ({
    id: String(job.id),
    source_slug: job.data?.source_slug ?? 'unknown',
    limit: job.data?.limit ?? 0,
    attempts_made: job.attemptsMade,
    failed_reason: job.failedReason ?? 'no reason recorded',
    stacktrace: job.stacktrace ?? [],
    failed_at: job.finishedOn ? new Date(job.finishedOn).toISOString() : null,
    added_at: job.timestamp ? new Date(job.timestamp).toISOString() : null,
  }));
}

/**
 * Retry one failed job by ID. Throws if the job isn't currently in the failed state.
 */
export async function retryFailedJob(jobId: string): Promise<void> {
  const job = await scrapeQueue.getJob(jobId);
  if (!job) {
    throw new Error(`Job ${jobId} not found`);
  }
  const state = await job.getState();
  if (state !== 'failed') {
    throw new Error(`Job ${jobId} is in state '${state}', not 'failed'`);
  }
  await job.retry();
}

/**
 * Retry every currently-failed job. Returns the count of jobs re-queued.
 */
export async function retryAllFailedJobs(): Promise<{ retried: number; errors: string[] }> {
  const failed = await scrapeQueue.getJobs(['failed'], 0, -1, false);
  const errors: string[] = [];
  let retried = 0;

  for (const job of failed) {
    try {
      await job.retry();
      retried++;
    } catch (err) {
      errors.push(`Job ${job.id}: ${err instanceof Error ? err.message : String(err)}`);
    }
  }

  return { retried, errors };
}