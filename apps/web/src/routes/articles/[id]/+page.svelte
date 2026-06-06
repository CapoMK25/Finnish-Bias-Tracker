<script lang="ts">
  import type { PageData } from './$types';
  import BiasIndicator from '$lib/components/BiasIndicator.svelte';
  import SourceBadge from '$lib/components/SourceBadge.svelte';
  import LanguageTag from '$lib/components/LanguageTag.svelte';
  import TopicTag from '$lib/components/TopicTag.svelte';
  import { relativeTime } from '$lib/utils/relativeTime';
  import PageMeta from "$lib/components/PageMeta.svelte";

  interface Props {
    data: PageData;
  }

  let { data }: Props = $props();

  const article = $derived(data.article);
  const latestScore = $derived(article.scores?.[0] ?? null);
  const earlierScores = $derived(article.scores?.slice(1) ?? []);

  const articleTypeLabel: Record<string, string> = {
    news: 'News',
    opinion: 'Opinion',
    analysis: 'Analysis',
    blog: 'Blog',
  };

  function formatDate(iso: string | null): string {
    if (!iso) return '';
    return new Date(iso).toLocaleDateString('en-GB', {
      day: 'numeric',
      month: 'long',
      year: 'numeric',
    });
  }
</script>

<PageMeta
  title="{article.title} — Finnish Bias Tracker"
  description={latestScore?.summary || article.title}
/>

<div class="mx-auto max-w-3xl px-6 py-8">
  <nav class="mb-6">
    <a
      href="/"
      class="text-sm text-slate-600 hover:text-slate-900 hover:underline"
    >
      ← All articles
    </a>
  </nav>

  <!-- Top section: title and metadata -->
  <header class="mb-8 border-b border-slate-200 pb-6">
    <h1 class="text-2xl font-semibold leading-tight tracking-tight text-slate-900 sm:text-3xl">
      {article.title}
    </h1>

    <div class="mt-4 flex flex-wrap items-center gap-2 text-xs text-slate-500">
      <SourceBadge slug={article.source.slug} name={article.source.name} />
      {#if article.published_at}
        <span class="tabular text-slate-500">
          {formatDate(article.published_at)} ({relativeTime(article.published_at)})
        </span>
      {/if}
      <LanguageTag language={article.language} />
      {#if article.article_type && article.article_type !== 'news'}
        <span
          class="inline-flex items-center rounded-sm border border-slate-300 bg-slate-50 px-1.5 py-0.5 text-[11px] font-medium text-slate-700"
        >
          {articleTypeLabel[article.article_type] ?? article.article_type}
        </span>
      {/if}
    </div>

    <div class="mt-4">
      <a
        href={article.url}
        target="_blank"
        rel="noopener noreferrer"
        class="text-sm text-slate-700 underline hover:text-slate-900"
      >
        Read original at {article.source.name} ↗
      </a>
    </div>
  </header>

  <!-- Middle section: score breakdown -->
  {#if latestScore}
    <section
      aria-label="Bias score breakdown"
      class="mb-10 border border-slate-200 bg-white p-6"
    >
      <header class="mb-4 flex items-baseline justify-between border-b border-slate-200 pb-3">
        <h2 class="text-base font-semibold text-slate-900">Bias score</h2>
        <span class="text-xs text-slate-500">
          Scored under prompt {latestScore.prompt_version}
        </span>
      </header>

      <dl class="grid grid-cols-1 gap-4 sm:grid-cols-3">
        <div>
          <dt class="text-xs uppercase tracking-wide text-slate-500">Bias</dt>
          <dd class="mt-1 flex items-center gap-2">
            <BiasIndicator score={latestScore.bias} showLabel />
          </dd>
        </div>
        <div>
          <dt class="text-xs uppercase tracking-wide text-slate-500">Confidence</dt>
          <dd class="mt-1 text-sm tabular text-slate-900">
            {Math.round(latestScore.confidence * 100)}%
          </dd>
        </div>
        <div>
          <dt class="text-xs uppercase tracking-wide text-slate-500">Topic</dt>
          <dd class="mt-1 text-sm">
            <TopicTag topic={latestScore.topic} />
          </dd>
        </div>
      </dl>

      {#if latestScore.summary}
        <div class="mt-6">
          <dt class="text-xs uppercase tracking-wide text-slate-500">Summary</dt>
          <dd class="mt-1 text-sm leading-relaxed text-slate-700">
            {latestScore.summary}
          </dd>
        </div>
      {/if}

      <details class="mt-6 border-t border-slate-200 pt-4" open>
        <summary class="cursor-pointer text-sm font-medium text-slate-900 hover:underline">
          Why this score?
        </summary>

        <div class="mt-4 text-sm leading-relaxed text-slate-700">
          {#if latestScore.rationale}
            <p class="mb-4">{latestScore.rationale}</p>
          {/if}

          {#if latestScore.examples && latestScore.examples.length > 0}
            <p class="mb-2 text-xs uppercase tracking-wide text-slate-500">
              Examples from the article
            </p>
            <ul class="list-inside list-disc space-y-1">
              {#each latestScore.examples as example, i (i)}
                <li class="text-slate-700">{example}</li>
              {/each}
            </ul>
          {/if}
        </div>
      </details>

      <footer class="mt-6 border-t border-slate-200 pt-3 text-xs text-slate-500">
        <span>Model: <code class="text-slate-700">{latestScore.model}</code></span>
        <span class="mx-2">·</span>
        <span>Provider: {latestScore.provider}</span>
        <span class="mx-2">·</span>
        <span>Scored {relativeTime(latestScore.scored_at)}</span>
      </footer>
    </section>

    <!-- Score history (if 2+ scores) -->
    {#if earlierScores.length > 0}
      <details class="mb-10 border border-slate-200 bg-slate-50 p-4">
        <summary class="cursor-pointer text-sm font-medium text-slate-700 hover:underline">
          Score history ({earlierScores.length} earlier {earlierScores.length === 1 ? 'version' : 'versions'})
        </summary>

        <div class="mt-4 space-y-4">
          {#each earlierScores as score, i (i)}
            <article class="border-l-2 border-slate-300 bg-white p-3 text-xs">
              <header class="mb-2 flex flex-wrap items-center gap-2">
                <BiasIndicator score={score.bias} />
                <span class="font-medium text-slate-700">Prompt {score.prompt_version}</span>
                <span class="text-slate-400">·</span>
                <span class="text-slate-500">{Math.round(score.confidence * 100)}% confidence</span>
                <span class="text-slate-400">·</span>
                <span class="text-slate-500">{relativeTime(score.scored_at)}</span>
              </header>
              {#if score.rationale}
                <p class="leading-relaxed text-slate-600">{score.rationale}</p>
              {/if}
            </article>
          {/each}
        </div>
      </details>
    {/if}
  {:else}
    <!-- Article exists but has no scores -->
    <section class="mb-10 border border-slate-200 bg-slate-50 p-6 text-sm text-slate-600">
      This article hasn't been scored yet. The article body is below; the
      scoring pipeline may pick it up on a future pass.
    </section>
  {/if}

  <!-- Bottom section: article body in serif -->
  <article class="prose prose-slate max-w-none">
    <div class="font-serif text-base leading-relaxed text-slate-900 whitespace-pre-wrap">
      {article.body}
    </div>
  </article>

  <footer class="mt-12 border-t border-slate-200 pt-6 text-xs text-slate-500">
    <a
      href={article.url}
      target="_blank"
      rel="noopener noreferrer"
      class="hover:underline"
    >
      Read original at {article.source.name} ↗
    </a>
  </footer>
</div>