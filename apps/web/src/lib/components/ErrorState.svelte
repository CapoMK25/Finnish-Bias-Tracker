<!--
  ErrorState
  ----------
  Display when something went wrong fetching the data. Visually distinct
  from EmptyState (which is "no results") so users don't conflate the
  two situations.

  Props:
    title (string, required): primary message
    description (string, optional): secondary message
    onRetry (function, optional): if provided, renders a 'Try again' button
      that calls this function. If absent, the component just displays
      the message without a retry affordance.

  Example:
    <ErrorState
      title="Couldn't load articles"
      description="The backend is briefly unreachable."
      onRetry={() => location.reload()}
    />
-->

<script lang="ts">
  interface Props {
    title: string;
    description?: string;
    onRetry?: () => void;
  }

  let { title, description, onRetry }: Props = $props();
</script>

<div class="border border-red-200 bg-red-50 px-6 py-8 text-center">
  <p class="text-base font-medium text-red-900">{title}</p>
  {#if description}
    <p class="mt-2 text-sm text-red-700">{description}</p>
  {/if}
  {#if onRetry}
    <button
      type="button"
      onclick={onRetry}
      class="mt-4 rounded-sm border border-red-300 bg-white px-4 py-2 text-sm font-medium text-red-900 hover:bg-red-50"
    >
      Try again
    </button>
  {/if}
</div>
