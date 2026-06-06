<script lang="ts">
  import type { PageData } from './$types';
  import { goto } from '$app/navigation';
  import SourceCard from '$lib/components/SourceCard.svelte';
  import EmptyState from '$lib/components/EmptyState.svelte';
  import { biasColor } from '$lib/colors';
  import PageMeta from "$lib/components/PageMeta.svelte";

  interface Props {
    data: PageData;
  }

  let { data }: Props = $props();

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

  const RANGE_LABELS: Record<string, string> = {
    '7d': 'Last 7 days',
    '30d': 'Last 30 days',
    '90d': 'Last 90 days',
    all: 'All time',
  };

  // Aggregate per-source averages for the bottom bar chart.
  const sourceAverages = $derived(
    data.sources.map((s: { slug: string; name: string; bias: number }) => {
      const articles = data.perSource[s.slug] ?? [];
      const scored = articles.filter((a: { score: unknown }) => a.score !== null);
      const avg =
        scored.length === 0
          ? null
          : scored.reduce(
              (acc: number, a: { score: { bias: number } | null }) =>
                acc + (a.score?.bias ?? 0),
              0,
            ) / scored.length;
      return {
        slug: s.slug,
        name: s.name,
        sourceBias: s.bias,
        scoredCount: scored.length,
        avg,
      };
    }),
  );

  // For the aggregate chart, only show sources that actually have coverage.
  const aggregateChartData = $derived(
    sourceAverages.filter((s: { avg: number | null }) => s.avg !== null),
  );

  function updateParam(key: string, value: string) {
    const url = new URL(window.location.href);
    url.searchParams.set(key, value);
    goto(url.pathname + url.search, {
      invalidateAll: true,
      replaceState: false,
      keepFocus: true,
      noScroll: true,
    });
  }
</script>

<PageMeta
  title="Source comparison — Finnish Bias Tracker"
  description="Compare how each Finnish news source covers a topic. See bias distribution, article counts, and sample coverage side by side."
  />

<div class="mx-auto max-w-6xl px-6 py-12">
  <header class="mb-10 border-b border-slate-200 pb-6">
    <a
      href="/"
      class="mb-3 inline-block text-sm text-slate-600 hover:text-slate-900 hover:underline"
    >
      ← All articles
    </a>
    <h1 class="text-3xl font-semibold tracking-tight text-slate-900">
      Source comparison
    </h1>
    <p class="mt-2 text-base text-slate-600">
      How each Finnish news source covers a topic.
    </p>
  </header>

  <section class="mb-8 text-sm leading-relaxed text-slate-700">
    <p>
      Pick a topic and a date range. Each source's card shows how many articles
      it published on that topic, what the average bias score was, the
      distribution across the −2 to +2 spectrum, and the three most recent
      articles. The aggregate chart below lets you compare average bias across
      all sources at a glance.
    </p>
  </section>

  <!-- Controls -->
  <section class="mb-8 flex flex-wrap items-end gap-4 border-b border-slate-200 pb-6">
    <label class="flex flex-col gap-1">
      <span class="text-xs font-semibold uppercase tracking-wide text-slate-500">
        Topic
      </span>
      <select
        value={data.selected.topic}
        onchange={(e) => updateParam('topic', (e.target as HTMLSelectElement).value)}
        class="rounded-sm border border-slate-300 bg-white px-3 py-1.5 text-sm font-medium text-slate-900"
      >
        {#each data.topics as topic (topic)}
          <option value={topic}>{TOPIC_LABELS[topic] ?? topic}</option>
        {/each}
      </select>
    </label>

    <label class="flex flex-col gap-1">
      <span class="text-xs font-semibold uppercase tracking-wide text-slate-500">
        Date range
      </span>
      <select
        value={data.selected.range}
        onchange={(e) => updateParam('range', (e.target as HTMLSelectElement).value)}
        class="rounded-sm border border-slate-300 bg-white px-3 py-1.5 text-sm font-medium text-slate-900"
      >
        <option value="7d">Last 7 days</option>
        <option value="30d">Last 30 days</option>
        <option value="90d">Last 90 days</option>
        <option value="all">All time</option>
      </select>
    </label>
  </section>

  {#if data.loadError}
    <EmptyState
      title="Couldn't load comparison data"
      description="The backend is briefly unreachable. Try refreshing in a moment."
    />
  {:else}
    <!-- Source cards grid -->
    <section
      aria-label="Source comparison cards"
      class="mb-12 grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3"
    >
      {#each data.sources as source (source.slug)}
        <SourceCard
          slug={source.slug}
          name={source.name}
          sourceBias={source.bias}
          articles={data.perSource[source.slug] ?? []}
        />
      {/each}
    </section>

    <!-- Aggregate chart: average bias per source -->
    {#if aggregateChartData.length > 0}
      <section
        aria-label="Aggregate bias chart"
        class="border border-slate-200 bg-white p-6"
      >
        <header class="mb-4 border-b border-slate-200 pb-3">
          <h2 class="text-base font-semibold text-slate-900">
            Average bias on {TOPIC_LABELS[data.selected.topic] ?? data.selected.topic},
            by source
          </h2>
          <p class="mt-1 text-xs text-slate-500">
            {RANGE_LABELS[data.selected.range]}. Only sources with scored articles shown.
          </p>
        </header>

        <div class="space-y-2">
          {#each aggregateChartData as s (s.slug)}
            {@const color = biasColor(Math.round(s.avg!))}
            {@const offsetPct = ((s.avg! + 2) / 4) * 100}
            <div class="flex items-center gap-3">
              <span class="w-40 shrink-0 text-xs text-slate-700 truncate">
                {s.name}
              </span>
              <div class="relative h-6 flex-1 border border-slate-200 bg-slate-50">
                <!-- Center line for bias = 0 -->
                <div
                  class="absolute inset-y-0 w-px bg-slate-400"
                  style="left: 50%"
                ></div>
                <!-- Bar from center to the average -->
                {#if s.avg! >= 0}
                  <div
                    class="absolute inset-y-0 border border-[var(--bar-border)] bg-[var(--bar-bg)]"
                    style="left: 50%; width: {offsetPct - 50}%; --bar-bg: {color.bg}; --bar-border: {color.border};"
                  ></div>
                {:else}
                  <div
                    class="absolute inset-y-0 border border-[var(--bar-border)] bg-[var(--bar-bg)]"
                    style="left: {offsetPct}%; width: {50 - offsetPct}%; --bar-bg: {color.bg}; --bar-border: {color.border};"
                  ></div>
                {/if}
              </div>
              <span class="w-12 shrink-0 text-right text-xs tabular text-slate-700">
                {s.avg! > 0 ? '+' : ''}{s.avg!.toFixed(2)}
              </span>
              <span class="w-12 shrink-0 text-right text-[11px] tabular text-slate-400">
                n={s.scoredCount}
              </span>
            </div>
          {/each}
        </div>

        <footer class="mt-4 flex justify-between text-[10px] tabular text-slate-400">
          <span>−2</span>
          <span>0</span>
          <span>+2</span>
        </footer>
      </section>
    {/if}
  {/if}

  <footer class="mt-16 border-t border-slate-200 pt-6 text-xs text-slate-500">
    <div class="flex flex-wrap gap-x-6 gap-y-2">
      <a href="/" class="hover:underline">All articles</a>
      <a href="/methodology" class="hover:underline">Methodology</a>
      
      <a
        href="https://github.com/CapoMK25/Finnish-Bias-Tracker"
        target="_blank"
        rel="noopener noreferrer"
        class="hover:underline"
      >
        Source code
      </a>
    </div>
  </footer>
</div>