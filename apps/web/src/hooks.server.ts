import { env } from '$lib/server/config'; 

/** @type {import('@sveltejs/kit').Handle} */
export async function handle({ event, resolve }) {
    // Forcing execution of the config to ensure environment variables are loaded
    console.log("=========================================");
    console.log("[SERVER BOOTSTRAP] Environment loaded successfully.");
    console.log(`[SERVER BOOTSTRAP] LLM Warning Status: ${env.LLM_ALPHA_WARNING ? 'ACTIVE (Alpha)' : 'INACTIVE'}`);
    console.log("=========================================");

    return resolve(event);
}
