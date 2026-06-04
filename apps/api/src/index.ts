import 'dotenv/config';
import { Hono } from 'hono';
import { serve } from '@hono/node-server';
import { cors } from 'hono/cors';
import { logger } from 'hono/logger';
import { prettyJSON } from 'hono/pretty-json';

import { storiesRouter } from './routes/stories.js';
import { sourcesRouter } from './routes/sources.js';
import { articlesRouter } from './routes/articles.js';

import { config } from 'dotenv';
import { resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

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
    origin: ['http://localhost:5173', 'http://localhost:4173'],
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

// Routes
app.route('/api/stories', storiesRouter);
app.route('/api/sources', sourcesRouter);
app.route('/api/articles', articlesRouter);
// 404 handler
app.notFound((c) => c.json({ error: 'Not found' }, 404));

// Error handler
app.onError((err, c) => {
  console.error('Unhandled error:', err);
  return c.json({ error: 'Internal server error' }, 500);
});

const port = Number(process.env.API_PORT) || 3000;
const host = process.env.API_HOST || '0.0.0.0';

console.log(`🚀 Finnish Bias Tracker API starting on http://${host}:${port}`);

serve({
  fetch: app.fetch,
  port,
  hostname: host,
});

export type AppType = typeof app;
