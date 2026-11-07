import { db, schema } from './client.js';

const sources = [
  // Left (-2)
  { slug: 'kansan-uutiset', name: 'Kansan Uutiset', url: 'https://www.ku.fi', rssUrl: 'https://www.ku.fi/feed', biasScore: -2, sourceType: 'party_organ', ownership: 'Yrjö Sirola Foundation, trade unions', language: 'fi' },
  { slug: 'demokraatti', name: 'Demokraatti', url: 'https://demokraatti.fi', rssUrl: 'https://demokraatti.fi/feed/', biasScore: -2, sourceType: 'party_organ', ownership: 'SDP-affiliated', language: 'fi' },

  // Center-Left (-1)
  { slug: 'yle', name: 'Yle Uutiset', url: 'https://yle.fi', rssUrl: 'https://feeds.yle.fi/uutiset/v1/majorHeadlines/YLE_UUTISET.rss', biasScore: -1, sourceType: 'public', ownership: 'State (Finnish government)', language: 'fi' },
  { slug: 'helsingin-sanomat', name: 'Helsingin Sanomat', url: 'https://www.hs.fi', rssUrl: 'https://www.hs.fi/rss/tuoreimmat.xml', biasScore: -1, sourceType: 'mainstream', ownership: 'Sanoma Group', language: 'fi' },

  // Center (0)
  { slug: 'suomenmaa', name: 'Suomenmaa', url: 'https://www.suomenmaa.fi', rssUrl: 'https://www.suomenmaa.fi/feed/', biasScore: 0, sourceType: 'party_organ', ownership: 'Keskusta-affiliated', language: 'fi' },

  // Center-Right (+1)
  { slug: 'iltalehti', name: 'Iltalehti', url: 'https://www.iltalehti.fi', rssUrl: 'https://www.iltalehti.fi/rss/uutiset.xml', biasScore: 1, sourceType: 'tabloid', ownership: 'Alma Media', language: 'fi' },
  { slug: 'ilta-sanomat', name: 'Ilta-Sanomat', url: 'https://www.is.fi', rssUrl: 'https://www.is.fi/rss/tuoreimmat.xml', biasScore: 1, sourceType: 'tabloid', ownership: 'Sanoma Group', language: 'fi' },
  { slug: 'verkkouutiset', name: 'Verkkouutiset', url: 'https://www.verkkouutiset.fi', rssUrl: 'https://www.verkkouutiset.fi/feed/', biasScore: 1, sourceType: 'party_organ', ownership: 'Kokoomus-affiliated', language: 'fi' },

  // Right (+2)
  { slug: 'suomen-uutiset', name: 'Suomen Uutiset', url: 'https://www.suomenuutiset.fi', rssUrl: 'https://www.suomenuutiset.fi/feed/', biasScore: 2, sourceType: 'party_organ', ownership: 'Perussuomalaiset-affiliated', language: 'fi' },

  // Swedish-language
  { slug: 'hufvudstadsbladet', name: 'Hufvudstadsbladet', url: 'https://www.hbl.fi', rssUrl: 'https://www.hbl.fi/feed/', biasScore: -1, sourceType: 'mainstream', ownership: 'KSF Media', language: 'sv' },
  { slug: 'svenska-yle', name: 'Svenska Yle', url: 'https://svenska.yle.fi', rssUrl: 'https://svenska.yle.fi/rss/senaste-nytt', biasScore: -1, sourceType: 'public', ownership: 'State', language: 'sv' },
];

async function jobbyjob() {
  console.log(`Seeding ${sources.length} sources...`);

  for (const source of sources) {
    try {
      await db
        .insert(schema.sources)
        .values(source)
        .onConflictDoNothing({ target: schema.sources.slug });
      console.log(`  ✓ ${source.slug}`);
    } catch (err) {
      console.error(`  ✗ ${source.slug}:`, err);
    }
  }

  console.log('Seeding complete!');
  process.exit(0);
}

jobbyjob().catch((err) => {
  console.error('Seed failed:', err);
  process.exit(1);
});
