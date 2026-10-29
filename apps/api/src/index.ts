import 'dotenv/config';
import { Hono } from 'hono';
import { serve } from '@hono/node-server';
import { cors } from 'hono/cors';
import { logger } from 'hono/logger';
import { prettyJSON } from 'hono/pretty-json';

import { storiesRouter } from './routes/stories.js';
import { sourcesRouter } from './routes/sources.js';
import { articlesRouter } from './routes/articles.js';
import { adminRoutes } from './routes/admin.js';
import { clustersRouter } from './routes/clusters.js';

import { config } from 'dotenv';
import { resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import {
  removeAllRepeatableJobs,
  startHourlyScheduler,
  stopHourlyScheduler,
} from './queue/scheduler.js';
import { closeQueue } from './queue/scrape-queue.js';

// Resolve project root regardless of directory from which the server is started
const __filename = fileURLToPath(import.meta.url);
const __dirname = resolve(__filename, '..');
const projectRoot = resolve(__dirname, '../../..'); // src → api → apps → root
config({ path: resolve(projectRoot, '.env') });

const app = new Hono();

// Middleware
app.use('*', logger());
app.use('*', prettyJSON());
app.use(
  '*',
  cors({
    // Added your live production domain to the origin array to permit secure cross-origin API calls
    origin: [
      'http://localhost:5173', 
      'http://localhost:4173', 
      'https://finnishbiastracker.cloud-ip.cc'
    ],
    credentials: true,
  })
);

// Health check
app.get('/health', (c) =>
  c.json({
    status: 'ok',
    version: '0.1.0',
    timestamp: new Date().toISOString(),
  })
);

// Shutdown handlers
process.on('SIGINT', async () => {
  console.log('Shutting down...');
  stopHourlyScheduler();
  await closeQueue();
  process.exit(0);
});

process.on('SIGTERM', async () => {
  stopHourlyScheduler();
  await closeQueue();
  process.exit(0);
});

// Routes
app.route('/api/stories', storiesRouter);
app.route('/api/sources', sourcesRouter);
app.route('/api/articles', articlesRouter);
app.route('/api/admin', adminRoutes);
app.route('/api/clusters', clustersRouter);

// 404 handler
app.notFound((c) => c.json({ error: 'Not found' }, 404));

// Error handler
app.onError((err, c) => {
  console.error('Unhandled error:', err);
  return c.json({ error: 'Internal server error' }, 500);
});

const port = Number(process.env.API_PORT) || 3000;
const host = process.env.API_HOST || '0.0.0.0';

// Start the backend here
console.log(`Finnish Bias Tracker Backend API starting on http://${host}:${port}`);

// Enqueue the scrape jobs every hour, starting with the current hour right now
// (a no-op if they are already queued). This replaces the old BullMQ repeatable
// jobs, which only fired once per API restart: see queue/scheduler.ts.
startHourlyScheduler();

// Remove the legacy repeatable schedules left in Redis by the old scheduler.
removeAllRepeatableJobs().catch((err) => {
  console.error('Failed to clear legacy repeatable jobs:', err);
});

serve({
  fetch: app.fetch,
  port,
  hostname: host,
});

export type AppType = typeof app;
