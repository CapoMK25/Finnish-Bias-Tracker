<script lang="ts">
  import { theme, type ThemeMode } from '$lib/theme.svelte';

  const NAMES: Record<ThemeMode, string> = {
    system: 'match system',
    light: 'light',
    dark: 'dark'
  };

  // Until the store is ready (server render and first client render) show a
  // neutral button, so the HTML the server sent and the first client render agree.
  const label = $derived(
    theme.ready ? `Theme: ${NAMES[theme.mode]}. Click to change.` : 'Change theme'
  );
</script>

<button
  type="button"
  onclick={() => theme.cycle()}
  aria-label={label}
  title={label}
  class="inline-flex h-10 w-10 items-center justify-center rounded-sm border border-slate-300 bg-white text-slate-600 hover:bg-slate-100 hover:text-slate-900 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-slate-500"
>
  {#if !theme.ready}
    <span class="h-5 w-5" aria-hidden="true"></span>
  {:else if theme.mode === 'light'}
    <!-- sun -->
    <svg viewBox="0 0 24 24" class="h-5 w-5" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true">
      <circle cx="12" cy="12" r="4" />
      <path d="M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2M4.93 19.07l1.41-1.41M17.66 6.34l1.41-1.41" />
    </svg>
  {:else if theme.mode === 'dark'}
    <!-- moon -->
    <svg viewBox="0 0 24 24" class="h-5 w-5" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
      <path d="M21 12.79A9 9 0 1 1 11.21 3a7 7 0 0 0 9.79 9.79z" />
    </svg>
  {:else}
    <!-- monitor (match system) -->
    <svg viewBox="0 0 24 24" class="h-5 w-5" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
      <rect x="3" y="4" width="18" height="12" rx="2" />
      <path d="M8 20h8M12 16v4" />
    </svg>
  {/if}
</button>
