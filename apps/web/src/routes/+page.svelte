<script lang="ts">
  import type { PageData } from './$types';
  import BiasIndicator from '$lib/components/BiasIndicator.svelte';
  import SourceBadge from '$lib/components/SourceBadge.svelte';
  import LanguageTag from '$lib/components/LanguageTag.svelte';
  import TopicTag from '$lib/components/TopicTag.svelte';
  import EmptyState from '$lib/components/EmptyState.svelte';
  import LoadingState from '$lib/components/LoadingState.svelte';
  import { relativeTime } from '$lib/utils/relativeTime';

  interface Props {
    data: PageData;
  }

  let { data }: Props = $props();

  // Client-side state for "Load more" pagination.
  // articles holds the accumulated list across all loaded pages.
  let articles = $state([...data.articles]);
  let offset = $state(data.articles.length);
  let loading = $state(false);
  let loadMoreError = $state<string | null>(null);
  const total = $derived(data.total);
  const hasMore = $derived(articles.length < total);

  async function loadMore() {
    if (loading || !hasMore) return;

    loading = true;
    loadMoreError = null;

    try {
      const res = await fetch(`/api/articles?limit=${data.pageSize}&offset=${offset}`);
      if (!res.ok) {
        throw new Error(`API returned ${res.status}`);
      }
      const json = await res.json();
      articles = [...articles, ...json.data];
      offset = articles.length;
    } catch (e) {
      console.error('Failed to load more:', e);
      loadMoreError = "Couldn't load more articles. Try again?";
    } finally {
      loading = false;
    }
  }
</script>

<svelte:head>
  <title>Finnish Bias Tracker</title>
  <meta
    name="description"
    content="Mapping political framing across the Finnish press. An open-source bias-detection methodology applied to Finland's major news outlets."
  />
</svelte:head>

<div class="mx-auto max-w-3xl px-6 py-12">
  <header class="mb-10 border-b border-slate-200 pb-6">
    <h1 class="text-3xl font-semibold tracking-tight text-slate-900">
      Finnish Bias Tracker
    </h1>
    <p class="mt-2 text-base text-slate-600">
      Mapping political framing across the Finnish press.
    </p>
  </header>

  <section class="mb-10 text-sm leading-relaxed text-slate-700">
    <p>
      This site applies a documented LLM-based scoring methodology to recent
      articles from Finland's major news outlets, placing each piece on a
      −2 (left) to +2 (right) bias scale. Source colors reflect Finnish
      political tradition: red for the left, blue for the right, green for
      the centre, yellow for Swedish-language outlets, grey for independent
      mainstream press.
    </p>
    <p class="mt-3">
      Every score is recorded with rationale and example phrases from the
      article. The methodology, prompts, and source classifications are all
      public. Scores reflect a consistent application of the methodology —
      they are not absolute truth claims.
    </p>
  </section>

  {#if data.loadError}
    <EmptyState
      title="Couldn't reach the API"
      description="The backend is briefly unreachable. Try refreshing the page in a moment."
    />
  {:else if articles.length === 0}
    <EmptyState
      title="No articles yet"
      description="The scoring pipeline hasn't populated any articles. Check back soon."
    />
  {:else}
    <section aria-label="Recent articles" class="space-y-2">
      {#each articles as article (article.id)}
        <article
          class="flex flex-col gap-2 border border-slate-200 bg-white px-4 py-3 sm:flex-row sm:items-center sm:gap-4"
        >
          <a
            href="/articles/{article.id}"
            class="flex-1 text-sm font-medium text-slate-900 hover:underline"
          >
            {article.title}
          </a>
          <div class="flex flex-wrap items-center gap-2 text-xs text-slate-500">
            <SourceBadge slug={article.source.slug} name={article.source.name} />
            {#if article.score?.topic}
              <TopicTag topic={article.score.topic} />
            {/if}
            {#if article.language === 'sv'}
              <LanguageTag language="sv" />
            {/if}
            <span class="tabular text-slate-500">{relativeTime(article.published_at)}</span>
            {#if article.score}
              <BiasIndicator score={article.score.bias} />
            {/if}
          </div>
        </article>
      {/each}
    </section>

    {#if loading}
      <div class="mt-4">
        <LoadingState rows={3} />
      </div>
    {/if}

    {#if loadMoreError}
      <p class="mt-4 text-center text-sm text-red-700">{loadMoreError}</p>
    {/if}

    {#if hasMore && !loading}
      <div class="mt-8 flex justify-center">
        <button
          type="button"
          onclick={loadMore}
          class="rounded-sm border border-slate-300 bg-white px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50"
        >
          Load more articles
        </button>
      </div>
    {/if}

    {#if !hasMore && articles.length > 0}
      <p class="mt-8 text-center text-xs text-slate-400">
        Showing all {articles.length} articles.
      </p>
    {/if}
  {/if}

  <footer class="mt-16 border-t border-slate-200 pt-6 text-xs text-slate-500">
    <div class="flex flex-wrap gap-x-6 gap-y-2">
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