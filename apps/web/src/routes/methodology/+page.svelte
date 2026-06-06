<script lang="ts">
  import type { PageData } from './$types';
  import SourceBadge from '$lib/components/SourceBadge.svelte';
  import BiasIndicator from '$lib/components/BiasIndicator.svelte';
  import LanguageTag from '$lib/components/LanguageTag.svelte';

  interface Props {
    data: PageData;
  }

  let { data }: Props = $props();

  // The current LLM prompt. When bias_scoring.py changes, update both files.
  const CURRENT_PROMPT_VERSION = 'v1.2';
  const CURRENT_PROMPT_SYSTEM = `You are an analytical reviewer assessing political bias in Finnish news articles. Your job is to identify *how* an article is framed, not to judge whether its claims are true.

You will be given a Finnish (or Swedish-language Finnish) news article. You will return structured JSON evaluating its political bias on a -3 (far left) to +3 (far right) scale, with 0 being center/neutral.

CRITICAL PRINCIPLES:
1. Score the article, not the source. A right-leaning outlet can publish a neutral article. A left-leaning outlet can publish a right-leaning piece. Judge the text in front of you.
2. Provide concrete evidence. Every score must be backed by specific examples from the article — loaded words, framing choices, source selection, omissions.
3. Be calibrated. Most news articles are mildly biased or neutral (-1 to +1). Reserve -3 and +3 for explicitly partisan or party-organ content.
4. Distinguish opinion from news. Opinion pieces will naturally be more biased; that's expected. Note article_type accordingly.
5. Confidence should reflect ambiguity. If the article is short, technical, or genuinely balanced, confidence should be lower.

BIAS INDICATORS:

Left-leaning signals:
- Emphasis on inequality, workers' rights, public services, climate action
- Sources skew toward unions, NGOs, academics, progressive politicians
- Framing of economic policy emphasizes redistribution, social protection
- Critical framing of business interests, austerity, immigration enforcement

Right-leaning signals:
- Emphasis on individual responsibility, market efficiency, traditional values, sovereignty
- Sources skew toward business leaders, conservative politicians, security officials
- Framing of economic policy emphasizes growth, deregulation, fiscal discipline
- Critical framing of welfare programs, immigration, EU integration, climate regulation

Neutral/center indicators:
- Multiple perspectives represented with similar weight
- Descriptive rather than evaluative language
- Sourcing across the political spectrum
- Wire-style "who/what/when/where" reporting`;
</script>

<svelte:head>
  <title>Methodology — Finnish Bias Tracker</title>
  <meta
    name="description"
    content="How the Finnish Bias Tracker scores political bias in Finnish news articles. Full methodology, prompt evolution, source inventory, and known limitations."
  />
</svelte:head>

<div class="mx-auto max-w-3xl px-6 py-12">
  <nav class="mb-6">
    <a href="/" class="text-sm text-slate-600 hover:text-slate-900 hover:underline">
      ← All articles
    </a>
  </nav>

  <header class="mb-10 border-b border-slate-200 pb-6">
    <h1 class="text-3xl font-semibold tracking-tight text-slate-900">
      Methodology
    </h1>
    <p class="mt-2 text-base text-slate-600">
      How the Finnish Bias Tracker scores political bias.
    </p>
  </header>

  <!-- Table of contents -->
  <nav aria-label="Table of contents" class="mb-12 border border-slate-200 bg-slate-50 p-4 text-sm">
    <p class="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">
      On this page
    </p>
    <ol class="list-inside list-decimal space-y-1 text-slate-700">
      <li><a href="#what-this-does" class="hover:underline">What this project does</a></li>
      <li><a href="#bias-scale" class="hover:underline">The bias scale</a></li>
      <li><a href="#what-gets-scored" class="hover:underline">What gets scored</a></li>
      <li><a href="#calibration-history" class="hover:underline">Calibration history</a></li>
      <li><a href="#limitations" class="hover:underline">Known limitations</a></li>
      <li><a href="#source-inventory" class="hover:underline">Source inventory</a></li>
      <li><a href="#open-methodology" class="hover:underline">Open methodology</a></li>
    </ol>
  </nav>

  <!-- 1. What this project does -->
  <section id="what-this-does" class="mb-12 scroll-mt-6">
    <h2 class="mb-4 text-xl font-semibold text-slate-900">
      1. What this project does
    </h2>
    <div class="space-y-4 font-serif text-base leading-relaxed text-slate-800">
      <p>
        The Finnish Bias Tracker aggregates recent articles from Finland's
        major news outlets and applies a documented bias-scoring methodology
        to each one. Sources span the political spectrum and both national
        languages: from Vasemmistoliitto-affiliated Kansan Uutiset on the
        left to Perussuomalaiset-affiliated Suomen Uutiset on the right,
        from the public broadcaster Yle to Swedish-language Hufvudstadsbladet
        and Svenska Yle.
      </p>
      <p>
        The goal is not to declare which articles are <em>true</em>, but
        to make the framing visible. Two outlets covering the same event
        can describe it in ways that emphasize different facts, choose
        different sources, and use different language. By placing each
        article on a -2 to +2 bias scale alongside the LLM's rationale,
        the project lets readers see those framing differences directly.
        The scoring methodology, prompts, source classifications, and
        scoring history are all public — anyone can audit them.
      </p>
    </div>
  </section>

  <!-- 2. The bias scale -->
  <section id="bias-scale" class="mb-12 scroll-mt-6">
    <h2 class="mb-4 text-xl font-semibold text-slate-900">
      2. The bias scale
    </h2>
    <p class="mb-4 font-serif text-base leading-relaxed text-slate-800">
      Every scored article receives an integer bias value from −2 to +2.
      In Finnish political convention, negative values represent the left
      and positive values the right — the opposite of US conventions where
      red is the right and blue is the left.
    </p>

    <div class="overflow-x-auto">
      <table class="w-full border-collapse border border-slate-200 text-sm">
        <thead>
          <tr class="bg-slate-50 text-left">
            <th class="border border-slate-200 px-3 py-2 font-semibold text-slate-700">
              Score
            </th>
            <th class="border border-slate-200 px-3 py-2 font-semibold text-slate-700">
              Indicator
            </th>
            <th class="border border-slate-200 px-3 py-2 font-semibold text-slate-700">
              Description
            </th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <td class="border border-slate-200 px-3 py-2 tabular">−2</td>
            <td class="border border-slate-200 px-3 py-2">
              <BiasIndicator score={-2} />
            </td>
            <td class="border border-slate-200 px-3 py-2 text-slate-700">
              Clear partisan framing, often party-organ content. Loaded
              language consistent with a particular left-wing political
              position.
            </td>
          </tr>
          <tr>
            <td class="border border-slate-200 px-3 py-2 tabular">−1</td>
            <td class="border border-slate-200 px-3 py-2">
              <BiasIndicator score={-1} />
            </td>
            <td class="border border-slate-200 px-3 py-2 text-slate-700">
              Mild left lean detectable in framing, source selection, or
              vocabulary choices. The article still reads as journalism,
              not advocacy.
            </td>
          </tr>
          <tr>
            <td class="border border-slate-200 px-3 py-2 tabular">0</td>
            <td class="border border-slate-200 px-3 py-2">
              <BiasIndicator score={0} />
            </td>
            <td class="border border-slate-200 px-3 py-2 text-slate-700">
              Neutral, balanced, or wire-style reporting. Multiple
              perspectives represented; descriptive rather than evaluative
              language.
            </td>
          </tr>
          <tr>
            <td class="border border-slate-200 px-3 py-2 tabular">+1</td>
            <td class="border border-slate-200 px-3 py-2">
              <BiasIndicator score={1} />
            </td>
            <td class="border border-slate-200 px-3 py-2 text-slate-700">
              Mild right lean detectable in framing, source selection, or
              vocabulary choices. The article still reads as journalism,
              not advocacy.
            </td>
          </tr>
          <tr>
            <td class="border border-slate-200 px-3 py-2 tabular">+2</td>
            <td class="border border-slate-200 px-3 py-2">
              <BiasIndicator score={2} />
            </td>
            <td class="border border-slate-200 px-3 py-2 text-slate-700">
              Clear partisan framing, often party-organ content. Loaded
              language consistent with a particular right-wing political
              position.
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <p class="mt-4 font-serif text-sm leading-relaxed text-slate-600">
      The underlying database schema allows scores from −3 to +3, but in
      practice the current scoring methodology (v1.2) clamps to ±2.
      Reserve ±3 for editorial cases the model rates as explicit
      propaganda — extremely rare in the current dataset.
    </p>
  </section>

  <!-- 3. What gets scored -->
  <section id="what-gets-scored" class="mb-12 scroll-mt-6">
    <h2 class="mb-4 text-xl font-semibold text-slate-900">
      3. What gets scored
    </h2>
    <div class="space-y-4 font-serif text-base leading-relaxed text-slate-800">
      <p>
        Every article passes through the same scoring pipeline. After
        scraping, the article's title, body, source, and publication
        date are sent to an LLM (currently Gemini 2.5 Flash-Lite) with
        a versioned prompt. The model returns structured JSON
        containing the bias score, a confidence value, the detected
        topic, a one-sentence neutral summary, and a list of specific
        phrases from the article that drove the score.
      </p>
      <p>
        Each scoring result is stored alongside the article with the
        prompt version that produced it. When the prompt is revised,
        the article can be rescored under the new version without
        losing the historical scoring data. Every article's detail
        page shows the full scoring rationale and any version history.
      </p>
      <p>
        The current prompt ({CURRENT_PROMPT_VERSION}) is below. It is
        intentionally English-language even though the articles are
        in Finnish or Swedish — modern LLMs apply the same scoring
        principles across languages, and the prompt is more readable
        for the methodology audit if it's in English.
      </p>
    </div>

    <details class="mt-6 border border-slate-200 bg-slate-50">
      <summary class="cursor-pointer px-4 py-3 text-sm font-medium text-slate-900 hover:bg-slate-100">
        View the {CURRENT_PROMPT_VERSION} prompt
      </summary>
      <div class="border-t border-slate-200 bg-white p-4">
        <pre class="whitespace-pre-wrap break-words font-mono text-xs leading-relaxed text-slate-700">{CURRENT_PROMPT_SYSTEM}</pre>
      </div>
    </details>
  </section>

  <!-- 4. Calibration history -->
  <section id="calibration-history" class="mb-12 scroll-mt-6">
    <h2 class="mb-4 text-xl font-semibold text-slate-900">
      4. Calibration history
    </h2>
    <div class="space-y-4 font-serif text-base leading-relaxed text-slate-800">
      <p>
        Three prompt versions have been used so far. Each revision
        was driven by observed scoring failures on real articles, not
        by abstract reasoning about what bias detection should look
        like.
      </p>
    </div>

    <div class="mt-4 space-y-4">
      <article class="border-l-2 border-slate-300 bg-white p-4">
        <header class="mb-2 flex items-baseline justify-between">
          <h3 class="text-base font-semibold text-slate-900">v1.0 — initial</h3>
          <span class="text-xs text-slate-500">May 2026</span>
        </header>
        <p class="text-sm leading-relaxed text-slate-700">
          First-pass prompt. Returned bias on a −3 to +3 scale,
          confidence, topic, and a free-text rationale. Calibration
          audit found the model consistently scored mainstream
          articles as 0 (correct) but also scored party-organ
          articles as 0 or ±1 — under-detecting strong partisan
          framing. Examples were unstructured prose, hard to audit.
        </p>
      </article>

      <article class="border-l-2 border-slate-300 bg-white p-4">
        <header class="mb-2 flex items-baseline justify-between">
          <h3 class="text-base font-semibold text-slate-900">v1.1 — examples as array</h3>
          <span class="text-xs text-slate-500">May 2026</span>
        </header>
        <p class="text-sm leading-relaxed text-slate-700">
          Restructured the prompt to require an array of specific
          phrases from the article rather than freeform examples.
          Forced the model to ground its score in concrete textual
          evidence. Bias detection on partisan sources improved
          marginally, but the model still avoided the ±2 endpoints
          even for clear party-organ content.
        </p>
      </article>

      <article class="border-l-2 border-slate-300 bg-white p-4">
        <header class="mb-2 flex items-baseline justify-between">
          <h3 class="text-base font-semibold text-slate-900">v1.2 — current</h3>
          <span class="text-xs text-slate-500">June 2026</span>
        </header>
        <p class="text-sm leading-relaxed text-slate-700">
          Added explicit calibration instruction: "Reserve ±3 for
          explicitly partisan or party-organ content." Recalibrated
          the indicators for left-leaning and right-leaning signals
          to be more specific. After v1.2, party-organ sources
          (Kansan Uutiset, Suomen Uutiset) reliably score ±2 on
          opinion-heavy articles, and mainstream sources score in
          the −1 to +1 range as expected.
        </p>
      </article>
    </div>
  </section>

  <!-- 5. Known limitations -->
  <section id="limitations" class="mb-12 scroll-mt-6">
    <h2 class="mb-4 text-xl font-semibold text-slate-900">
      5. Known limitations
    </h2>
    <div class="space-y-4 font-serif text-base leading-relaxed text-slate-800">
      <p>
        This project is pre-alpha. The methodology has known weaknesses
        worth being explicit about.
      </p>
      <ul class="ml-6 list-disc space-y-3">
        <li>
          <strong>Single-LLM scoring.</strong> Each article is scored by
          one model under one prompt. There is no inter-annotator
          agreement check — no second model or human rater whose
          scores would be compared with the primary scorer. Established
          bias-detection methodologies (AllSides, Ad Fontes Media) use
          panels of raters with different ideological orientations to
          mitigate single-source bias. This project does not.
        </li>
        <li>
          <strong>English-language prompt scoring non-English content.</strong>
          The prompt is in English; the articles are in Finnish or
          Swedish. Modern LLMs handle this competently for major
          European languages, but the model's understanding of
          subtle Finnish political vocabulary, party-specific
          rhetoric, or culturally specific framing is necessarily
          less refined than a native speaker's would be.
        </li>
        <li>
          <strong>Small sample sizes during early operation.</strong>
          The project began continuous scraping in mid-2026. Some
          source-topic combinations may have only a handful of
          scored articles. Average bias scores from small samples
          are noisy; the comparison page shows article counts
          (<code>n=N</code>) alongside averages so readers can
          weigh confidence appropriately.
        </li>
        <li>
          <strong>Gemini quota-gated free-tier operation.</strong>
          The project runs on the free tier of Google's Gemini API,
          which has a 1,500 daily request limit. This caps how many
          articles can be scored per day and means the scoring
          pipeline occasionally pauses when quota is exhausted.
          The constraint may relax in future if a paid tier is enabled.
        </li>
        <li>
          <strong>Paywall extraction is partial.</strong> Some
          sources (notably Hufvudstadsbladet) paywall most of their
          content. The scraper extracts whatever is publicly visible
          — typically the teaser and first paragraph. Bias scoring
          on partial articles is less reliable than on full text,
          and confidence values tend to be lower for these.
        </li>
        <li>
          <strong>No real-time updates.</strong> The scraping pipeline
          runs on a schedule, not continuously. Articles can take up
          to several hours between publication and appearing in the
          index. The relative-time labels reflect when the article
          was originally published, not when the bias tracker
          ingested it.
        </li>
        <li>
          <strong>Source-level labels are editorial judgments.</strong>
          The base bias of each source (Kansan Uutiset = −2, Yle = −1,
          and so on) is a hand-applied classification based on
          ownership, party affiliation, and editorial history. These
          are defensible classifications, but they are not
          uncontested. The source comparison page lets readers
          compare actual scored articles against these baseline
          classifications.
        </li>
      </ul>
    </div>
  </section>

  <!-- 6. Source inventory -->
  <section id="source-inventory" class="mb-12 scroll-mt-6">
    <h2 class="mb-4 text-xl font-semibold text-slate-900">
      6. Source inventory
    </h2>
    <p class="mb-4 font-serif text-base leading-relaxed text-slate-800">
      Every source currently in the bias tracker, sorted by
      source-level bias from left to right. Source-level bias is the
      editorial classification used as a baseline; individual articles
      can and often do score differently.
    </p>

    {#if data.loadError}
      <p class="border border-slate-200 bg-slate-50 p-4 text-sm text-slate-500 italic">
        The source list could not be loaded. The API may be temporarily
        unreachable.
      </p>
    {:else}
      <div class="overflow-x-auto">
        <table class="w-full border-collapse border border-slate-200 text-sm">
          <thead>
            <tr class="bg-slate-50 text-left">
              <th class="border border-slate-200 px-3 py-2 font-semibold text-slate-700">
                Source
              </th>
              <th class="border border-slate-200 px-3 py-2 font-semibold text-slate-700">
                Bias
              </th>
              <th class="border border-slate-200 px-3 py-2 font-semibold text-slate-700">
                Language
              </th>
              <th class="border border-slate-200 px-3 py-2 font-semibold text-slate-700">
                Articles indexed
              </th>
            </tr>
          </thead>
          <tbody>
            {#each data.sources as source (source.slug)}
              <tr>
                <td class="border border-slate-200 px-3 py-2">
                  <SourceBadge slug={source.slug} name={source.name} />
                </td>
                <td class="border border-slate-200 px-3 py-2">
                  <BiasIndicator score={source.bias} />
                </td>
                <td class="border border-slate-200 px-3 py-2">
                  <LanguageTag language={source.language} />
                </td>
                <td class="border border-slate-200 px-3 py-2 tabular text-slate-700">
                  {source.article_count}
                </td>
              </tr>
            {/each}
          </tbody>
        </table>
      </div>
    {/if}
  </section>

  <!-- 7. Open methodology -->
  <section id="open-methodology" class="mb-12 scroll-mt-6">
    <h2 class="mb-4 text-xl font-semibold text-slate-900">
      7. Open methodology
    </h2>
    <div class="space-y-4 font-serif text-base leading-relaxed text-slate-800">
      <p>
        Every prompt version, every scoring decision, and every
        source classification is public. The full source code is
        on GitHub and the project is licensed under AGPL-3.0 —
        derivative work must remain open-source. The license choice
        is intentional: a bias-detection methodology that hides
        its workings is not a methodology, it is an oracle.
      </p>
      <p>
        Methodology improvements, prompt refinements, and source
        classification updates are welcome as GitHub issues or pull
        requests. The project specifically welcomes contributions
        from people with backgrounds in Finnish media studies,
        political science, or computational linguistics.
      </p>
      <div class="flex flex-wrap gap-4">
        
        <a
          href="https://github.com/CapoMK25/Finnish-Bias-Tracker"
          target="_blank"
          rel="noopener noreferrer"
          class="rounded-sm border border-slate-300 bg-white px-4 py-2 text-sm font-medium text-slate-900 hover:bg-slate-50"
        >
          GitHub repository →
        </a>
        <a
          href="https://www.gnu.org/licenses/agpl-3.0.html"
          target="_blank"
          rel="noopener noreferrer"
          class="rounded-sm border border-slate-300 bg-white px-4 py-2 text-sm font-medium text-slate-900 hover:bg-slate-50"
        >
          AGPL-3.0 license →
        </a>
      </div>
    </div>
  </section>

  <footer class="mt-16 border-t border-slate-200 pt-6 text-xs text-slate-500">
    <div class="flex flex-wrap gap-x-6 gap-y-2">
      <a href="/" class="hover:underline">All articles</a>
      <a href="/compare" class="hover:underline">Compare sources</a>
      
      <a
        href="https://github.com/CapoMK25/Finnish-Bias-Tracker"
        target="_blank"
        rel="noopener noreferrer"
        class="hover:underline"
      >
        Source code
      </a>
    </div>
  </footer>
</div>