// src/lib/server/config.ts 
import * as path from 'path';
import { config } from 'dotenv';

// Determine the absolute path to the .env file relative to this module
const projectRoot = process.cwd(); 
config({ path: path.join(projectRoot, '.env') });


/** 
 * Centralized object for all environment variables, providing type safety and defaults.
 */
export const env = {
    // Core System Variables
    DATABASE_URL: process.env.DATABASE_URL ?? '', 
    REDIS_URL: process.env.REDIS_URL ?? 'redis://localhost:6379',
    NODE_ENV: process.env.NODE_ENV || 'development',


    // LLM/API Variables (Keep the logic, but remove the console log)
    LLM_PROVIDER: process.env.LLM_PROVIDER, 
    LLM_ALPHA_WARNING: process.env.LLM_ALPHA_WARNING === 'true' ? true : false, 
    MISTRAL_API_KEY: process.env.MISTRAL_API_KEY ?? '',


    // Other variables (add all others here...)
    API_PORT: Number(process.env.API_PORT) || 3000,
};


if (!env.DATABASE_URL) {
throw new Error('FATAL ERROR: DATABASE_URL is not set. Please ensure your .env file is configured.');
}
