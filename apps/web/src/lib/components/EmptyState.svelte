<!--
  EmptyState
  ----------
  Generic "no results" placeholder. Used across the article list, source
  comparison page, and anywhere else a query can return zero results.

  Props:
    title (string, required): primary message
    description (string, optional): secondary message explaining how to fix it

  Example:
    <EmptyState
      title="No articles match these filters"
      description="Try removing the bias range filter or expanding the date range."
    />
-->

<script lang="ts">
  interface Props {
    title: string;
    description?: string;
  }

  let { title, description }: Props = $props();
</script>

<div class="border border-slate-200 bg-white px-6 py-12 text-center">
  <p class="text-base font-medium text-slate-900">{title}</p>
  {#if description}
    <p class="mt-2 text-sm text-slate-500">{description}</p>
  {/if}
</div>
