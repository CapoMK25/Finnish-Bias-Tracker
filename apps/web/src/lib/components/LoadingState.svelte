<!--
  LoadingState
  ------------
  Generic loading skeleton. Renders animated grey blocks that approximate
  the layout being loaded. Avoids spinners (spinners feel like "the app is
  thinking"; skeletons feel like "the content is coming").

  Props:
    rows (number, default 5): number of skeleton rows to show

  Example:
    <LoadingState rows={3} />
-->

<script lang="ts">
  interface Props {
    rows?: number;
  }

  let { rows = 5 }: Props = $props();
</script>

<div class="space-y-3">
  {#each Array(rows) as _, i (i)}
    <div class="flex items-center gap-3 border border-slate-200 bg-white px-4 py-3">
      <div class="h-4 flex-1 animate-pulse rounded-sm bg-slate-200"></div>
      <div class="h-4 w-16 animate-pulse rounded-sm bg-slate-200"></div>
      <div class="h-4 w-10 animate-pulse rounded-sm bg-slate-200"></div>
    </div>
  {/each}
</div>
