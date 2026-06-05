<!--
  TopicTag
  --------
  Small tag indicating an article's topic classification.

  The topic enum from the scorer:
    economic_policy, immigration, climate, foreign_policy,
    social_policy, health, education, crime, culture, other

  Display labels prettify the underscored names. Falls back to the raw
  string for unknown topics.

  Props:
    topic (string, required): topic code

  Example:
    <TopicTag topic="foreign_policy" />   <!-- renders "Foreign policy" -->
-->

<script lang="ts">
  interface Props {
    topic: string;
  }

  let { topic }: Props = $props();

  const labels: Record<string, string> = {
    economic_policy: 'Economic policy',
    immigration: 'Immigration',
    climate: 'Climate',
    foreign_policy: 'Foreign policy',
    social_policy: 'Social policy',
    health: 'Health',
    education: 'Education',
    crime: 'Crime',
    culture: 'Culture',
    other: 'Other',
  };

  const display = $derived(labels[topic] ?? topic);
</script>

<span
  class="inline-flex items-center rounded-sm border border-slate-200 bg-slate-50 px-1.5 py-0.5 text-[11px] font-medium text-slate-700"
>
  {display}
</span>
