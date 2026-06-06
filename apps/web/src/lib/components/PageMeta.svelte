<script lang="ts">
  import { page } from '$app/state';
  import { PUBLIC_SITE_URL } from '$env/static/public';

  interface Props {
    title: string;
    description: string;
    canonical?: string;
    /** Override OG image; defaults to the global one */
    image?: string;
  }

  let { title, description, canonical, image }: Props = $props();

  // Compute the canonical URL.
  // If caller didn't pass one explicitly, use the current path without query params.
  const siteUrl = PUBLIC_SITE_URL || 'http://localhost:5173';
  const computedCanonical = $derived(
    canonical ? `${siteUrl}${canonical}` : `${siteUrl}${page.url.pathname}`
  );

  // Default OG image is the global one. Per-page images would be passed in.
  const ogImageUrl = $derived(image ?? `${siteUrl}/og-image.png`);

  // Twitter requires absolute URLs; reuse the same.
  const twitterImageUrl = $derived(ogImageUrl);
</script>

<svelte:head>
  <title>{title}</title>
  <meta name="description" content={description} />

  <!-- Canonical URL -->
  <link rel="canonical" href={computedCanonical} />

  <!-- OpenGraph -->
  <meta property="og:type" content="website" />
  <meta property="og:title" content={title} />
  <meta property="og:description" content={description} />
  <meta property="og:url" content={computedCanonical} />
  <meta property="og:image" content={ogImageUrl} />
  <meta property="og:image:width" content="1200" />
  <meta property="og:image:height" content="630" />
  <meta property="og:site_name" content="Finnish Bias Tracker" />
  <meta property="og:locale" content="en_US" />

  <!-- Twitter Card -->
  <meta name="twitter:card" content="summary_large_image" />
  <meta name="twitter:title" content={title} />
  <meta name="twitter:description" content={description} />
  <meta name="twitter:image" content={twitterImageUrl} />
</svelte:head>