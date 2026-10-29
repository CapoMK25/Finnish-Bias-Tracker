/**
 * Scrape scheduler — enqueues one scrape job per source at the top of every hour.
 *
 * Why this is not a BullMQ "repeatable" job: repeatable jobs only keep
 * rescheduling themselves when a Node.js Worker picks them up. Our worker is
 * Python, which never books the next iteration, so the old schedule fired once
 * per API restart and then went quiet (it stopped for days at a time). Here the
 * API process itself enqueues the jobs instead.
 *
 * Guarantees:
 *  - Every job has a deterministic id per (source, hour). BullMQ ignores `add`
 *    when that id exists, so restarting the API mid-hour, or two overlapping
 *    ticks, never duplicate work.
 *  - The next hourly tick is booked *before* the current one runs, so a slow
 *    or hung Redis call can never stop the chain.
 *  - A failed tick (for example Redis restarting during a deploy) is retried
 *    after a minute instead of waiting for the next hour.
 *  - getSchedulerStatus() feeds /api/admin/health, so a stalled scheduler
 *    shows up as "degraded" instead of silently doing nothing.
 *
 * The single Python worker (concurrency 1) takes the jobs one by one, so the
 * sources are scraped in sequence and appear as each job finishes.
 */

import { scrapeQueue } from './scrape-queue.js';

/**
 * Sources that have a scraper in the Python worker. Keep in sync with
 * apps/scrapers/src/worker/dispatch.py. Sources without a scraper must not be
 * scheduled: their jobs can only fail ("unknown source").
 */
export const SCRAPED_SOURCES = [
  'yle',
  'helsingin-sanomat',
  'iltalehti',
  'ilta-sanomat',
  'demokraatti',
  'kansan-uutiset',
  'suomen-uutiset',
  'suomenmaa',
  'verkkouutiset',
  'hufvudstadsbladet',
  'svenska-yle',
] as const;

const HOUR_MS = 60 * 60 * 1000;
const ARTICLES_PER_JOB = 10;
/** Fire a moment after the top of the hour so the clock has definitely rolled over. */
const TICK_OFFSET_MS = 1_000;
/** After a failed tick, try again this soon. */
const RETRY_AFTER_FAILURE_MS = 60_000;
/** No successful tick for this long means the scheduler is unhealthy (an hour plus slack). */
const STALE_AFTER_MS = 75 * 60 * 1000;
/** Right after boot the first tick is still in flight; don't report unhealthy yet. */
const STARTUP_GRACE_MS = 2 * 60 * 1000;

let timer: NodeJS.Timeout | undefined;
let retryTimer: NodeJS.Timeout | undefined;

const state: {
  running: boolean;
  startedAt?: number;
  lastSuccessAt?: number;
  lastSlot?: number;
  lastCreated?: number;
  lastError?: string;
  lastErrorAt?: number;
  nextTickAt?: number;
} = { running: false };

/** Start of the hour (UTC, in ms) that `now` falls in. */
function hourSlot(now: number): number {
  return Math.floor(now / HOUR_MS) * HOUR_MS;
}

function iso(ms: number | undefined): string | null {
  return ms === undefined ? null : new Date(ms).toISOString();
}

/**
 * Enqueue one scrape job per source for the given hour. Returns how many jobs
 * were newly created (already-existing ids are skipped by BullMQ).
 */
export async function enqueueHourlyScrapes(slot: number = hourSlot(Date.now())): Promise<number> {
  let created = 0;
  for (const slug of SCRAPED_SOURCES) {
    const jobId = `scrape-${slug}-${slot}`; // no ':' - BullMQ rejects it in custom ids
    const existing = await scrapeQueue.getJob(jobId);
    if (existing) continue;

    await scrapeQueue.add(
      `scrape:${slug}`,
      { source_slug: slug, limit: ARTICLES_PER_JOB },
      { jobId },
    );
    created++;
  }
  return created;
}

async function tick(): Promise<void> {
  const slot = hourSlot(Date.now());
  try {
    const created = await enqueueHourlyScrapes(slot);
    state.lastSuccessAt = Date.now();
    state.lastSlot = slot;
    state.lastCreated = created;
    state.lastError = undefined;
    // Single-line JSON so scripts/check-ingestion.sh can parse it reliably.
    console.log(
      'hourly_scrapes_enqueued',
      JSON.stringify({
        slot: new Date(slot).toISOString(),
        created,
        sources: SCRAPED_SOURCES.length,
      }),
    );
  } catch (err) {
    state.lastError = err instanceof Error ? err.message : String(err);
    state.lastErrorAt = Date.now();
    console.error('hourly_scrape_enqueue_failed', state.lastError);
    // Redis can be briefly unavailable (for example during a deploy). Never
    // crash the API over it; try again soon instead of waiting an hour.
    if (state.running) {
      if (retryTimer) clearTimeout(retryTimer);
      retryTimer = setTimeout(() => void tick(), RETRY_AFTER_FAILURE_MS);
      retryTimer.unref();
    }
  }
}

function scheduleNextTick(): void {
  const now = Date.now();
  const at = hourSlot(now) + HOUR_MS + TICK_OFFSET_MS;
  state.nextTickAt = at;
  timer = setTimeout(() => {
    scheduleNextTick(); // book the following hour first: a slow tick must never stop the chain
    void tick();
  }, at - now);
  timer.unref(); // don't keep the process alive just for this timer
}

/**
 * Call once when the API boots. Enqueues the current hour immediately (a no-op
 * if it was already enqueued), then every hour on the hour.
 */
export function startHourlyScheduler(): void {
  if (state.running) return;
  // Fresh start: forget the previous run's results so the startup grace applies.
  state.lastSuccessAt = undefined;
  state.lastSlot = undefined;
  state.lastCreated = undefined;
  state.lastError = undefined;
  state.lastErrorAt = undefined;
  state.running = true;
  state.startedAt = Date.now();
  void tick();
  scheduleNextTick();
}

/** For graceful shutdown. */
export function stopHourlyScheduler(): void {
  if (timer) clearTimeout(timer);
  if (retryTimer) clearTimeout(retryTimer);
  timer = undefined;
  retryTimer = undefined;
  state.running = false;
}

/** Snapshot for the admin endpoints. `healthy` drives /api/admin/health. */
export function getSchedulerStatus() {
  const now = Date.now();
  const sinceSuccess = state.lastSuccessAt === undefined ? undefined : now - state.lastSuccessAt;
  const sinceStart = state.startedAt === undefined ? undefined : now - state.startedAt;
  const healthy =
    state.running &&
    (sinceSuccess !== undefined
      ? sinceSuccess < STALE_AFTER_MS
      : sinceStart !== undefined && sinceStart < STARTUP_GRACE_MS);

  return {
    running: state.running,
    healthy,
    last_success_at: iso(state.lastSuccessAt),
    last_slot: iso(state.lastSlot),
    last_created: state.lastCreated ?? null,
    last_error: state.lastError ?? null,
    last_error_at: iso(state.lastErrorAt),
    next_tick_at: iso(state.nextTickAt),
  };
}

/**
 * Remove all legacy BullMQ repeatable jobs. The API calls this once at boot to
 * clear the old schedules; also available via DELETE /api/admin/queue/repeatables.
 */
export async function removeAllRepeatableJobs(): Promise<void> {
  const repeatables = await scrapeQueue.getRepeatableJobs();
  for (const job of repeatables) {
    await scrapeQueue.removeRepeatableByKey(job.key);
    console.log('scheduler_repeatable_removed', { key: job.key });
  }
}
