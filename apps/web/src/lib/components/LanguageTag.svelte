<!--
  LanguageTag
  -----------
  Small tag indicating article language. Only renders for non-Finnish
  articles (sv, en) since Finnish is the default and adding "FI" to every
  article would be visual noise.

  Props:
    language (string, required): language code, e.g. "fi", "sv"

  Example:
    <LanguageTag language="sv" />
    <LanguageTag language="fi" />  <!-- renders nothing -->
-->

<script lang="ts">
  interface Props {
    language: string;
  }

  let { language }: Props = $props();
</script>

{#if language && language !== 'fi'}
  <span
    class="inline-flex items-center rounded-sm border border-slate-300 bg-slate-50 px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-slate-600"
  >
    {language}
  </span>
{/if}
