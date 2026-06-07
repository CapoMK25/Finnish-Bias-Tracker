<!--
  LoadingState
  ------------
  Animated skeleton rows matching the article-list layout. Used during
  client-side fetches (e.g., 'Load more' on the landing page).

  The skeleton structure mirrors a real article row: title block on the
  left, metadata badges on the right. Heights and spacing approximate
  the loaded content, so the swap from skeleton to real content doesn't
  cause layout shift.

  Props:
    rows (number, default 5): number of skeleton rows to show
-->

<script lang="ts">
  interface Props {
    rows?: number;
  }

  let { rows = 5 }: Props = $props();
</script>

<div class="space-y-2" aria-busy="true" aria-live="polite">
  {#each Array(rows) as _, i (i)}
    <div class="flex flex-col gap-2 border border-slate-200 bg-white px-4 py-3 sm:flex-row sm:items-center sm:gap-4">
      <!-- Title placeholder (flex-1 to take remaining space) -->
      <div class="h-4 flex-1 animate-pulse rounded-sm bg-slate-200"></div>

      <!-- Metadata badges placeholders -->
      <div class="flex flex-wrap items-center gap-2">
        <div class="h-5 w-24 animate-pulse rounded-sm bg-slate-200"></div>
        <div class="h-5 w-16 animate-pulse rounded-sm bg-slate-200"></div>
        <div class="h-5 w-14 animate-pulse rounded-sm bg-slate-200"></div>
        <div class="h-5 w-10 animate-pulse rounded-sm bg-slate-200"></div>
      </div>
    </div>
  {/each}
</div>