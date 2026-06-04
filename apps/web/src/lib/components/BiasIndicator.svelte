<!--
  BiasIndicator
  -------------
  Colored pill showing a bias score on the -3 to +3 scale.

  Props:
    score (number, required): -3 to +3
    showLabel (boolean, default false): when true, renders the textual
      label ("mild left") next to the number

  Example:
    <BiasIndicator score={-2} />
    <BiasIndicator score={1} showLabel />
-->

<script lang="ts">
  import { biasColor } from '$lib/colors';

  interface Props {
    score: number;
    showLabel?: boolean;
  }

  let { score, showLabel = false }: Props = $props();

  const color = $derived(biasColor(score));
  const formatted = $derived(score > 0 ? `+${score}` : `${score}`);
</script>

<span
  class="inline-flex items-center gap-1.5 rounded-sm border px-1.5 py-0.5 text-xs font-semibold tabular"
  style="background-color: {color.bg}; color: {color.fg}; border-color: {color.border};"
  title="Bias score: {formatted} ({color.label})"
>
  <span>{formatted}</span>
  {#if showLabel}
    <span class="font-normal">{color.label}</span>
  {/if}
</span>
