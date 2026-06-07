<!--
  Custom error page for SvelteKit's error system.
  Shown for any throw error(...) from a +page.server.ts or +server.ts.

  404s get specific copy. Everything else gets generic 'something went
  wrong' with a Try again button.
-->

<script lang="ts">
  import { page } from '$app/state';

  function tryAgain() {
    location.reload();
  }
</script>

<svelte:head>
  <title>{page.status} — Finnish Bias Tracker</title>
</svelte:head>

<div class="mx-auto max-w-2xl px-6 py-24 text-center">
  <p class="text-sm font-semibold uppercase tracking-wide text-slate-500">
    Error {page.status}
  </p>

  <h1 class="mt-3 text-2xl font-semibold text-slate-900">
    {#if page.status === 404}
      Article not found
    {:else}
      Something went wrong
    {/if}
  </h1>

  <p class="mt-3 text-sm text-slate-600">
    {#if page.status === 404}
      The article you're looking for doesn't exist, or its link has changed.
    {:else}
      {page.error?.message ?? 'An unexpected error occurred.'}
    {/if}
  </p>

  <div class="mt-8 flex flex-wrap items-center justify-center gap-3">
    
     <a href="/"
      class="inline-block rounded-sm border border-slate-300 bg-white px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50"
    >
      ← Back to all articles
    </a>

    {#if page.status !== 404}
      <button
        type="button"
        onclick={tryAgain}
        class="inline-block rounded-sm border border-slate-300 bg-white px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50"
      >
        Try again
      </button>
    {/if}
  </div>
</div>