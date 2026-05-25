import { config } from 'dotenv';
import { resolve, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
// src → api → apps → repo root
const projectRoot = resolve(__dirname, '../../..');

config({ path: resolve(projectRoot, '.env') });

export const env = {
  DATABASE_URL: process.env.DATABASE_URL ?? '',
  REDIS_URL: process.env.REDIS_URL ?? 'redis://localhost:6379',
  API_PORT: Number(process.env.API_PORT) || 3000,
  API_HOST: process.env.API_HOST || '0.0.0.0',
  ANTHROPIC_API_KEY: process.env.ANTHROPIC_API_KEY ?? '',
  NODE_ENV: process.env.NODE_ENV || 'development',
};

if (!env.DATABASE_URL) {
  throw new Error('DATABASE_URL is not set. Check your .env file at the project root.');
}
