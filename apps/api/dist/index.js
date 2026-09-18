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
import { registerRepeatableJobs } from './queue/scheduler.js';
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
app.use('*', cors({
    origin: ['http://localhost:5173', 'http://localhost:4173'],
    credentials: true,
}));
// Health check
app.get('/health', (c) => c.json({
    status: 'ok',
    version: '0.1.0',
    timestamp: new Date().toISOString(),
}));
// Shutdown handlers
process.on('SIGINT', async () => {
    console.log('Shutting down...');
    await closeQueue();
    process.exit(0);
});
process.on('SIGTERM', async () => {
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
// Schedule repeatable scrape jobs once the API is up.
registerRepeatableJobs().catch((err) => {
    console.error('Failed to register repeatable jobs:', err);
});
serve({
    fetch: app.fetch,
    port,
    hostname: host,
});
