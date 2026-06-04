<!--
  SourceBadge
  -----------
  Source name with party-identity color tint.

  See design-system.md for the full reasoning behind party-identity
  coloring (Finnish convention: blue = right, red = left, green = centre,
  yellow = Swedish-speaking, grey = independent).

  Props:
    slug (string, required): source slug, e.g. "suomen-uutiset"
    name (string, required): display name
    href (string, optional): if provided, badge becomes a link to source profile

  Example:
    <SourceBadge slug="kansan-uutiset" name="Kansan Uutiset" />
    <SourceBadge slug="yle" name="Yle Uutiset" href="/sources/yle" />
-->

<script lang="ts">
  import { sourceColor } from '$lib/colors';

  interface Props {
    slug: string;
    name: string;
    href?: string;
  }

  let { slug, name, href }: Props = $props();

  const color = $derived(sourceColor(slug));
</script>

{#if href}
  <a
    {href}
    class="inline-flex items-center rounded-sm border px-2 py-0.5 text-xs font-medium hover:underline"
    style="background-color: {color.bg}; color: {color.fg}; border-color: {color.border};"
  >
    {name}
  </a>
{:else}
  <span
    class="inline-flex items-center rounded-sm border px-2 py-0.5 text-xs font-medium"
    style="background-color: {color.bg}; color: {color.fg}; border-color: {color.border};"
  >
    {name}
  </span>
{/if}
