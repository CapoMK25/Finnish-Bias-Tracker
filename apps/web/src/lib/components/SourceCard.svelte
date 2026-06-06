<script lang="ts">
  import SourceBadge from './SourceBadge.svelte';
  import BiasIndicator from './BiasIndicator.svelte';
  import { biasColor } from '$lib/colors';

  interface Article {
    id: string;
    title: string;
    score: { bias: number } | null;
  }

  interface Props {
    slug: string;
    name: string;
    sourceBias: number;
    articles: Article[];
  }

  let { slug, name, sourceBias, articles }: Props = $props();

  // Articles with a v1.2 score (i.e., a non-null score). The histogram and
  // average bias both depend on scored articles only — unscored ones
  // contribute to the count but not to the score-based stats.
  const scoredArticles = $derived(articles.filter((a) => a.score !== null));

  const articleCount = $derived(articles.length);
  const scoredCount = $derived(scoredArticles.length);

  // Average bias (rounded to one decimal for display).
  const averageBias = $derived(() => {
    if (scoredCount === 0) return null;
    const sum = scoredArticles.reduce((acc, a) => acc + (a.score?.bias ?? 0), 0);
    return sum / scoredCount;
  });

  // Histogram: count per bias value -2..+2.
  const histogram = $derived(() => {
    const counts = [0, 0, 0, 0, 0]; // -2, -1, 0, +1, +2
    for (const a of scoredArticles) {
      const b = a.score?.bias;
      if (b !== undefined && b !== null && b >= -2 && b <= 2) {
        counts[b + 2]++;
      }
    }
    return counts;
  });

  const maxHistogramCount = $derived(Math.max(1, ...histogram()));

  // Sample article titles to display (first 3 by API order, which is
  // most recent first).
  const sampleArticles = $derived(articles.slice(0, 3));
</script>

<article class="flex h-full flex-col border border-slate-200 bg-white p-4">
  <header class="mb-3 flex items-start justify-between gap-2">
    <SourceBadge {slug} {name} />
    <span
      class="text-[11px] uppercase tracking-wide text-slate-400 tabular"
      title="Source-level bias classification"
    >
      bias {sourceBias > 0 ? `+${sourceBias}` : sourceBias}
    </span>
  </header>

  {#if articleCount === 0}
    <p class="flex-1 text-sm text-slate-500 italic">
      No coverage in this period.
    </p>
  {:else}
    <!-- Article count + average bias -->
    <div class="mb-3 grid grid-cols-2 gap-3 text-sm">
      <div>
        <p class="text-[11px] uppercase tracking-wide text-slate-500">Articles</p>
        <p class="mt-0.5 text-lg font-semibold tabular text-slate-900">
          {articleCount}
        </p>
      </div>
      <div>
        <p class="text-[11px] uppercase tracking-wide text-slate-500">Avg bias</p>
        <p class="mt-0.5 text-lg font-semibold tabular text-slate-900">
          {#if averageBias() !== null}
            {averageBias()! > 0 ? '+' : ''}{averageBias()!.toFixed(1)}
          {:else}
            —
          {/if}
        </p>
      </div>
    </div>

    <!-- Histogram -->
    {#if scoredCount > 0}
      <div class="mb-4">
        <p class="mb-1 text-[11px] uppercase tracking-wide text-slate-500">
          Distribution
        </p>
        <div class="flex h-12 items-end gap-0.5">
          {#each histogram() as count, i (i)}
            {@const bias = i - 2}
            {@const color = biasColor(bias)}
            {@const heightPct = (count / maxHistogramCount) * 100}
            <div
              class="flex-1 min-w-0"
              title="{count} article{count === 1 ? '' : 's'} at bias {bias > 0 ? `+${bias}` : bias}"
            >
              <div
                class="w-full border border-[var(--bar-border)] bg-[var(--bar-bg)]"
                style="height: {Math.max(2, heightPct)}%; min-height: 2px; --bar-bg: {color.bg}; --bar-border: {color.border};"
              ></div>
            </div>
          {/each}
        </div>
        <div class="mt-1 flex justify-between text-[10px] text-slate-400 tabular">
          <span>−2</span>
          <span>−1</span>
          <span>0</span>
          <span>+1</span>
          <span>+2</span>
        </div>
      </div>
    {/if}

    <!-- Sample articles -->
    {#if sampleArticles.length > 0}
      <div class="mt-auto">
        <p class="mb-2 text-[11px] uppercase tracking-wide text-slate-500">
          Recent articles
        </p>
        <ul class="space-y-1.5">
          {#each sampleArticles as article (article.id)}
            <li class="flex items-start gap-2 text-xs">
              {#if article.score}
                <BiasIndicator score={article.score.bias} />
              {/if}
              <a
                href="/articles/{article.id}"
                class="flex-1 leading-snug text-slate-700 hover:underline line-clamp-2"
              >
                {article.title}
              </a>
            </li>
          {/each}
        </ul>
      </div>
    {/if}
  {/if}
</article>