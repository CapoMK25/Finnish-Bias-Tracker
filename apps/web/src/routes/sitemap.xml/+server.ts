import type { RequestHandler } from './$types';
import { env } from '$env/dynamic/private';
import { PUBLIC_SITE_URL } from '$env/static/public';

/**
 * Sitemap generator. Dynamic so it stays in sync with the article inventory.
 *
 * Lists all static pages plus every article URL fetched from /api/articles.
 * The `lastmod` per article reflects when the article was scraped, giving
 * crawlers a reasonable freshness signal.
 *
 * Cached for one hour. The article inventory changes faster than that in
 * principle, but new articles getting indexed an hour late is acceptable.
 */
export const GET: RequestHandler = async ({ fetch }) => {
  const apiUrl = env.API_URL ?? 'http://localhost:3000';
  const siteUrl = PUBLIC_SITE_URL || 'http://localhost:5173';

  // Fetch all article IDs. 1000 is well above current article count;
  // when we cross 1000, this needs to paginate (loop until total reached).
  const res = await fetch(`${apiUrl}/api/articles?limit=1000`);

  let articles: Array<{ id: string; scraped_at?: string; published_at?: string | null }> = [];
  if (res.ok) {
    const json = await res.json();
    articles = json.data;
  }

  const now = new Date().toISOString().split('T')[0];

  const staticUrls = [
    { loc: `${siteUrl}/`, lastmod: now, changefreq: 'hourly', priority: '1.0' },
    { loc: `${siteUrl}/compare`, lastmod: now, changefreq: 'daily', priority: '0.8' },
    { loc: `${siteUrl}/methodology`, lastmod: now, changefreq: 'monthly', priority: '0.7' },
  ];

  const articleUrls = articles.map((a) => ({
    loc: `${siteUrl}/articles/${a.id}`,
    lastmod: (a.published_at ?? a.scraped_at ?? new Date().toISOString()).split('T')[0],
    changefreq: 'monthly',
    priority: '0.6',
  }));

  const urls = [...staticUrls, ...articleUrls];

  const xml = `<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
${urls
  .map(
    (u) => `  <url>
    <loc>${u.loc}</loc>
    <lastmod>${u.lastmod}</lastmod>
    <changefreq>${u.changefreq}</changefreq>
    <priority>${u.priority}</priority>
  </url>`,
  )
  .join('\n')}
</urlset>`;

  return new Response(xml, {
    headers: {
      'Content-Type': 'application/xml',
      'Cache-Control': 'public, max-age=3600',
    },
  });
};