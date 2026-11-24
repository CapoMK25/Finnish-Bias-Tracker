import type { LayoutServerLoad } from './$types';
import { env } from '$lib/server/config'; 


/** @type {import('./$types').LayoutServerLoad} */
export const load: LayoutServerLoad = async ({ fetch }) => {
    
    // Reading the environment variable to determine if the warning banner should be displayed
    const isWarningActive = env.LLM_ALPHA_WARNING;

    return { 
        showBanner: isWarningActive 
    };
}
