/// <reference types="node" />
import { defineConfig } from 'drizzle-kit';
import { config } from 'dotenv';
import path from 'path';

// drizzle-kit runs this file via its own transpiler. Use traditional path
// (no node: protocol) and __dirname-less resolution to stay compatible.
// .env lives at the repo root, two levels up from apps/api/.
config({ path: path.resolve(process.cwd(), '../../.env') });

export default defineConfig({
  schema: './src/db/schema.ts',
  out: './src/db/migrations',
  dialect: 'postgresql',
  dbCredentials: {
    url: process.env.DATABASE_URL!,
  },
  verbose: true,
  strict: true,
});
