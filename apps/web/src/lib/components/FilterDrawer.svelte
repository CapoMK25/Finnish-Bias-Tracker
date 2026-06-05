<script lang="ts">
  import FilterSidebar from './FilterSidebar.svelte';
  import { countActiveFilters } from '$lib/utils/filters';

  interface Source {
    slug: string;
    name: string;
    bias: number;
    language: string;
  }

  interface Props {
    sources: Source[];
    filters: {
      source: string[];
      biasMin: string | null;
      biasMax: string | null;
      topic: string[];
      language: string;
      range: string;
    };
  }

  let { sources, filters }: Props = $props();

  let isOpen = $state(false);
  const activeCount = $derived(countActiveFilters(filters));

  function open() {
    isOpen = true;
    // Prevent body scroll behind the drawer
    document.body.style.overflow = 'hidden';
  }

  function close() {
    isOpen = false;
    document.body.style.overflow = '';
  }

  // Close drawer on escape key
  function onKeydown(e: KeyboardEvent) {
    if (e.key === 'Escape' && isOpen) {
      close();
    }
  }
</script>

<svelte:window onkeydown={onKeydown} />

<!-- Mobile: button to open drawer -->
<button
  type="button"
  onclick={open}
  class="md:hidden flex w-full items-center justify-between border border-slate-300 bg-white px-4 py-2 text-sm font-medium text-slate-700 mb-4 rounded-sm"
>
  <span>
    Filters
    {#if activeCount > 0}
      <span class="ml-1 text-slate-500">({activeCount} active)</span>
    {/if}
  </span>
  <span class="text-slate-400" aria-hidden="true">▾</span>
</button>

<!-- Drawer overlay and panel -->
{#if isOpen}
  <div
    class="md:hidden fixed inset-0 z-50 bg-black/40"
    onclick={close}
    onkeydown={(e) => e.key === 'Enter' && close()}
    role="button"
    tabindex="-1"
    aria-label="Close filter drawer"
  ></div>

  <div
    class="md:hidden fixed inset-y-0 right-0 z-50 w-80 max-w-[85vw] overflow-y-auto bg-white p-6 shadow-xl"
    role="dialog"
    aria-label="Filters"
  >
    <header class="mb-4 flex items-center justify-between border-b border-slate-200 pb-3">
      <h2 class="text-base font-semibold text-slate-900">Filters</h2>
      <button
        type="button"
        onclick={close}
        class="text-sm text-slate-500 hover:text-slate-900"
        aria-label="Close filters"
      >
        Close
      </button>
    </header>
    <FilterSidebar {sources} {filters} />
  </div>
{/if}

<!-- Desktop: always-visible sidebar -->
<div class="hidden md:block">
  <FilterSidebar {sources} {filters} />
</div>