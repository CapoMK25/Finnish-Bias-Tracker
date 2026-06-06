<script lang="ts">
  import { page } from '$app/state';
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

  <div class="mt-8">
    <a
      href="/"
      class="inline-block rounded-sm border border-slate-300 bg-white px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50"
      >
      ← Back to all articles
    </a>
  </div>
</div>