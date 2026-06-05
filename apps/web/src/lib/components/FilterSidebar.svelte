<script lang="ts">
  import { updateFilter, clearAllFilters, countActiveFilters } from '$lib/utils/filters';

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

  const activeCount = $derived(countActiveFilters(filters));

  // Group sources by bias bucket for visual organization.
  const sourceGroups = $derived(() => {
    const left = sources.filter((s) => s.bias < 0);
    const center = sources.filter((s) => s.bias === 0);
    const right = sources.filter((s) => s.bias > 0);
    return { left, center, right };
  });

  const TOPICS = [
    'economic_policy',
    'immigration',
    'climate',
    'foreign_policy',
    'social_policy',
    'health',
    'education',
    'crime',
    'culture',
    'other',
  ];

  const TOPIC_LABELS: Record<string, string> = {
    economic_policy: 'Economic policy',
    immigration: 'Immigration',
    climate: 'Climate',
    foreign_policy: 'Foreign policy',
    social_policy: 'Social policy',
    health: 'Health',
    education: 'Education',
    crime: 'Crime',
    culture: 'Culture',
    other: 'Other',
  };

  function toggleSource(slug: string) {
    const next = filters.source.includes(slug)
      ? filters.source.filter((s) => s !== slug)
      : [...filters.source, slug];
    updateFilter('source', next);
  }

  function toggleTopic(topic: string) {
    const next = filters.topic.includes(topic)
      ? filters.topic.filter((t) => t !== topic)
      : [...filters.topic, topic];
    updateFilter('topic', next);
  }

  function updateBiasRange(which: 'min' | 'max', event: Event) {
    const target = event.target as HTMLInputElement;
    const value = target.value;
    updateFilter(which === 'min' ? 'bias_min' : 'bias_max', value);
  }

  function selectLanguage(value: string) {
    updateFilter('language', value);
  }

  function selectRange(value: string) {
    updateFilter('range', value);
  }
</script>

<aside class="text-sm">
  <header class="mb-4 flex items-baseline justify-between">
    <h2 class="text-base font-semibold text-slate-900">
      Filters
      {#if activeCount > 0}
        <span class="ml-1 text-sm font-normal text-slate-500">({activeCount} active)</span>
      {/if}
    </h2>
    {#if activeCount > 0}
      <button
        type="button"
        onclick={clearAllFilters}
        class="text-xs text-slate-600 underline hover:text-slate-900"
      >
        Clear all
      </button>
    {/if}
  </header>

  <!-- Source filter -->
  <section class="mb-6">
    <h3 class="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">Source</h3>

    {#if sourceGroups().left.length > 0}
      <p class="mb-1 text-[11px] font-medium uppercase tracking-wide text-slate-400">Left</p>
      <div class="mb-2 space-y-1">
        {#each sourceGroups().left as source (source.slug)}
          <label class="flex items-center gap-2 cursor-pointer">
            <input
              type="checkbox"
              checked={filters.source.includes(source.slug)}
              onchange={() => toggleSource(source.slug)}
              class="h-3.5 w-3.5 rounded-sm border-slate-300"
            />
            <span class="text-slate-700">{source.name}</span>
          </label>
        {/each}
      </div>
    {/if}

    {#if sourceGroups().center.length > 0}
      <p class="mb-1 text-[11px] font-medium uppercase tracking-wide text-slate-400">Center</p>
      <div class="mb-2 space-y-1">
        {#each sourceGroups().center as source (source.slug)}
          <label class="flex items-center gap-2 cursor-pointer">
            <input
              type="checkbox"
              checked={filters.source.includes(source.slug)}
              onchange={() => toggleSource(source.slug)}
              class="h-3.5 w-3.5 rounded-sm border-slate-300"
            />
            <span class="text-slate-700">{source.name}</span>
          </label>
        {/each}
      </div>
    {/if}

    {#if sourceGroups().right.length > 0}
      <p class="mb-1 text-[11px] font-medium uppercase tracking-wide text-slate-400">Right</p>
      <div class="space-y-1">
        {#each sourceGroups().right as source (source.slug)}
          <label class="flex items-center gap-2 cursor-pointer">
            <input
              type="checkbox"
              checked={filters.source.includes(source.slug)}
              onchange={() => toggleSource(source.slug)}
              class="h-3.5 w-3.5 rounded-sm border-slate-300"
            />
            <span class="text-slate-700">{source.name}</span>
          </label>
        {/each}
      </div>
    {/if}
  </section>

  <!-- Bias range -->
  <section class="mb-6">
    <h3 class="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">Bias range</h3>
    <div class="flex items-center gap-2">
      <label class="flex flex-col gap-1">
        <span class="text-[11px] text-slate-500">Min</span>
        <input
          type="number"
          min="-3"
          max="3"
          step="1"
          value={filters.biasMin ?? ''}
          oninput={(e) => updateBiasRange('min', e)}
          placeholder="−3"
          class="w-16 rounded-sm border border-slate-300 px-2 py-1 text-sm tabular"
        />
      </label>
      <span class="text-slate-400">to</span>
      <label class="flex flex-col gap-1">
        <span class="text-[11px] text-slate-500">Max</span>
        <input
          type="number"
          min="-3"
          max="3"
          step="1"
          value={filters.biasMax ?? ''}
          oninput={(e) => updateBiasRange('max', e)}
          placeholder="+3"
          class="w-16 rounded-sm border border-slate-300 px-2 py-1 text-sm tabular"
        />
      </label>
    </div>
  </section>

  <!-- Topic -->
  <section class="mb-6">
    <h3 class="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">Topic</h3>
    <div class="space-y-1">
      {#each TOPICS as topic (topic)}
        <label class="flex items-center gap-2 cursor-pointer">
          <input
            type="checkbox"
            checked={filters.topic.includes(topic)}
            onchange={() => toggleTopic(topic)}
            class="h-3.5 w-3.5 rounded-sm border-slate-300"
          />
          <span class="text-slate-700">{TOPIC_LABELS[topic]}</span>
        </label>
      {/each}
    </div>
  </section>

  <!-- Language -->
  <section class="mb-6">
    <h3 class="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">Language</h3>
    <div class="space-y-1">
      <label class="flex items-center gap-2 cursor-pointer">
        <input
          type="radio"
          name="language"
          value=""
          checked={filters.language === ''}
          onchange={() => selectLanguage('')}
          class="h-3.5 w-3.5 border-slate-300"
        />
        <span class="text-slate-700">All</span>
      </label>
      <label class="flex items-center gap-2 cursor-pointer">
        <input
          type="radio"
          name="language"
          value="fi"
          checked={filters.language === 'fi'}
          onchange={() => selectLanguage('fi')}
          class="h-3.5 w-3.5 border-slate-300"
        />
        <span class="text-slate-700">Finnish only</span>
      </label>
      <label class="flex items-center gap-2 cursor-pointer">
        <input
          type="radio"
          name="language"
          value="sv"
          checked={filters.language === 'sv'}
          onchange={() => selectLanguage('sv')}
          class="h-3.5 w-3.5 border-slate-300"
        />
        <span class="text-slate-700">Swedish only</span>
      </label>
    </div>
  </section>

  <!-- Date range -->
  <section class="mb-6">
    <h3 class="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">Date range</h3>
    <div class="space-y-1">
      <label class="flex items-center gap-2 cursor-pointer">
        <input
          type="radio"
          name="range"
          value=""
          checked={filters.range === ''}
          onchange={() => selectRange('')}
          class="h-3.5 w-3.5 border-slate-300"
        />
        <span class="text-slate-700">All time</span>
      </label>
      <label class="flex items-center gap-2 cursor-pointer">
        <input
          type="radio"
          name="range"
          value="7d"
          checked={filters.range === '7d'}
          onchange={() => selectRange('7d')}
          class="h-3.5 w-3.5 border-slate-300"
        />
        <span class="text-slate-700">Last 7 days</span>
      </label>
      <label class="flex items-center gap-2 cursor-pointer">
        <input
          type="radio"
          name="range"
          value="30d"
          checked={filters.range === '30d'}
          onchange={() => selectRange('30d')}
          class="h-3.5 w-3.5 border-slate-300"
        />
        <span class="text-slate-700">Last 30 days</span>
      </label>
    </div>
  </section>
</aside>