<!--
  /design-system
  --------------
  Internal route showing all design system components rendered with
  sample data. Used during development to verify visual consistency.

  Not linked from the public navigation. Accessible directly via URL.
-->

<script lang="ts">
  import BiasIndicator from '$lib/components/BiasIndicator.svelte';
  import SourceBadge from '$lib/components/SourceBadge.svelte';
  import LanguageTag from '$lib/components/LanguageTag.svelte';
  import EmptyState from '$lib/components/EmptyState.svelte';
  import LoadingState from '$lib/components/LoadingState.svelte';

  const sources = [
    { slug: 'kansan-uutiset', name: 'Kansan Uutiset', bias: -2 },
    { slug: 'demokraatti', name: 'Demokraatti', bias: -2 },
    { slug: 'yle', name: 'Yle Uutiset', bias: -1 },
    { slug: 'helsingin-sanomat', name: 'Helsingin Sanomat', bias: -1 },
    { slug: 'svenska-yle', name: 'Svenska Yle', bias: -1 },
    { slug: 'hufvudstadsbladet', name: 'Hufvudstadsbladet', bias: -1 },
    { slug: 'suomenmaa', name: 'Suomenmaa', bias: 0 },
    { slug: 'iltalehti', name: 'Iltalehti', bias: 1 },
    { slug: 'ilta-sanomat', name: 'Ilta-Sanomat', bias: 1 },
    { slug: 'verkkouutiset', name: 'Verkkouutiset', bias: 1 },
    { slug: 'suomen-uutiset', name: 'Suomen Uutiset', bias: 2 },
  ];
</script>

<svelte:head>
  <title>Design system — Finnish Bias Tracker</title>
</svelte:head>

<main class="mx-auto max-w-4xl px-6 py-12">
  <header class="mb-12 border-b border-slate-200 pb-6">
    <h1 class="text-2xl font-semibold">Design system</h1>
    <p class="mt-2 text-sm text-slate-600">
      Reference page for shared components. See
      <code class="rounded-sm bg-slate-100 px-1 py-0.5 text-xs">apps/web/src/lib/design-system.md</code>
      for the full design rationale.
    </p>
  </header>

  <section class="mb-12">
    <h2 class="mb-4 text-lg font-semibold">BiasIndicator</h2>
    <p class="mb-4 text-sm text-slate-600">
      Pill showing position on the −3 to +3 bias scale. Independent of which
      source produced the article — the bias score is a property of the article.
    </p>
    <div class="flex flex-wrap items-center gap-2">
      <BiasIndicator score={-3} />
      <BiasIndicator score={-2} />
      <BiasIndicator score={-1} />
      <BiasIndicator score={0} />
      <BiasIndicator score={1} />
      <BiasIndicator score={2} />
      <BiasIndicator score={3} />
    </div>
    <div class="mt-4 flex flex-wrap items-center gap-2">
      <BiasIndicator score={-2} showLabel />
      <BiasIndicator score={0} showLabel />
      <BiasIndicator score={2} showLabel />
    </div>
  </section>

  <section class="mb-12">
    <h2 class="mb-4 text-lg font-semibold">SourceBadge</h2>
    <p class="mb-4 text-sm text-slate-600">
      Source name with party-identity color tint. See
      <code class="rounded-sm bg-slate-100 px-1 py-0.5 text-xs">design-system.md</code>
      for the reasoning behind party-identity (not bias-spectrum) coloring.
    </p>
    <div class="flex flex-wrap items-center gap-2">
      {#each sources as source (source.slug)}
        <SourceBadge slug={source.slug} name={source.name} />
      {/each}
    </div>
    <p class="mt-4 mb-2 text-sm text-slate-600">As link:</p>
    <SourceBadge slug="yle" name="Yle Uutiset" href="/sources/yle" />
  </section>

  <section class="mb-12">
    <h2 class="mb-4 text-lg font-semibold">LanguageTag</h2>
    <p class="mb-4 text-sm text-slate-600">
      Small tag for non-Finnish articles. Renders nothing for
      <code class="rounded-sm bg-slate-100 px-1 py-0.5 text-xs">language="fi"</code>
      since Finnish is the default.
    </p>
    <div class="flex flex-wrap items-center gap-2">
      <LanguageTag language="sv" />
      <LanguageTag language="en" />
      <span class="text-xs text-slate-400">
        (Finnish renders nothing — invisible to keep visual density low)
      </span>
    </div>
  </section>

  <section class="mb-12">
    <h2 class="mb-4 text-lg font-semibold">Sources × bias in context</h2>
    <p class="mb-4 text-sm text-slate-600">
      The two color systems are designed to disagree when reality disagrees.
      A Kansan Uutiset article that happens to score +1 displays as left-red
      (source identity) next to a right-blue pill (this article's actual lean).
      That tension is meaningful.
    </p>
    <div class="space-y-2">
      {#each sources as source (source.slug)}
        <div class="flex items-center gap-3 border border-slate-200 bg-white px-4 py-3">
          <span class="flex-1 text-sm">Sample article headline placeholder</span>
          <SourceBadge slug={source.slug} name={source.name} />
          <BiasIndicator score={source.bias} />
        </div>
      {/each}
    </div>
  </section>

  <section class="mb-12">
    <h2 class="mb-4 text-lg font-semibold">EmptyState</h2>
    <EmptyState
      title="No articles match these filters"
      description="Try removing the bias range filter or expanding the date range."
    />
  </section>

  <section class="mb-12">
    <h2 class="mb-4 text-lg font-semibold">LoadingState</h2>
    <LoadingState rows={3} />
  </section>
</main>
