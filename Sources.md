# Finnish Media Sources

> Complete list of sources tracked, with their classifications and reasoning. Every classification is contestable — open an issue to challenge any of them.

**Version**: 0.1 (Draft)
**Last updated**: 2026-05-24

## Classification approach

Each source has:
- **Bias score**: -3 to +3 (see [methodology.md](methodology.md))
- **Type**: party_organ | mainstream | tabloid | business | public | alternative
- **Ownership**: who funds it
- **RSS/feed availability**: how we ingest
- **Notes**: editorial history, particular tendencies

## Sources to aggregate

### Left (-3 to -2)

| Source | Score | Type | Ownership | RSS | Notes |
|--------|-------|------|-----------|-----|-------|
| Kansan Uutiset (ku.fi) | -2 | party_organ | Yrjö Sirola Foundation, trade unions | Yes | Explicit Left Alliance organ since 2000 |
| Demokraatti (demokraatti.fi) | -2 | party_organ | SDP-affiliated | Yes | SDP party organ |
| Long Play (longplay.fi) | -2 | mainstream | Independent journalist coop | Limited | Investigative, social-democratic editorial line |
| Voima (voima.fi) | -3 | alternative | Independent | Limited | Anti-capitalist, far-left framing |

### Center-Left (-1)

| Source | Score | Type | Ownership | RSS | Notes |
|--------|-------|------|-----------|-----|-------|
| Yle (yle.fi) | -1 | public | State (Finnish government) | Yes | Public broadcaster. Perceived as left-leaning by 40% of Finns per EVA 2025. Officially neutral. |
| Helsingin Sanomat (hs.fi) | -1 | mainstream | Sanoma Group | Yes (partial) | "Newspaper of record". Lean Left per MBFC. Liberal-progressive editorial line. |
| Suomen Kuvalehti (suomenkuvalehti.fi) | -1 | mainstream | Otavamedia | Yes | Center-left analytical broadsheet |
| Image (image.fi) | -1 | mainstream | A-lehdet | Yes | Culture magazine, urban liberal sensibility |

### Center (0)

| Source | Score | Type | Ownership | RSS | Notes |
|--------|-------|------|-----------|-----|-------|
| STT (stt.fi) | 0 | wire | Cooperative (multiple media owners) | Yes | Wire service, baseline for neutrality |
| MTV Uutiset (mtvuutiset.fi) | 0 | mainstream | MTV Oy (Bonnier) | Yes | Commercial broadcaster, broadly center |
| Suomenmaa (suomenmaa.fi) | 0 | party_organ | Keskusta-affiliated | Yes | Keskusta party organ, but Keskusta is genuinely centrist |
| Kauppalehti (kauppalehti.fi) | 0 | business | Alma Media | Yes | Business journalism, center-right on economics but factual |

### Center-Right (+1)

| Source | Score | Type | Ownership | RSS | Notes |
|--------|-------|------|-----------|-----|-------|
| Iltalehti (iltalehti.fi) | +1 | tabloid | Alma Media | Yes | Tabloid, slight populist lean, broad coverage |
| Ilta-Sanomat (is.fi) | +1 | tabloid | Sanoma Group | Yes | Tabloid, slightly more centrist than IL |
| Talouselämä (talouselama.fi) | +1 | business | Alma Talent | Yes | Business journalism, market-liberal |
| Verkkouutiset (verkkouutiset.fi) | +1 | party_organ | Kokoomus-affiliated | Yes | Kokoomus party organ |

### Right (+2)

| Source | Score | Type | Ownership | RSS | Notes |
|--------|-------|------|-----------|-----|-------|
| Suomen Uutiset (suomenuutiset.fi) | +2 | party_organ | Perussuomalaiset-affiliated | Yes | Finns Party (PS) party organ |

### Swedish-language (special category, scored separately)

| Source | Score | Type | Ownership | RSS | Notes |
|--------|-------|------|-----------|-----|-------|
| Hufvudstadsbladet (hbl.fi) | -1 | mainstream | KSF Media | Yes | Center-liberal, often RKP-aligned |
| Svenska Yle (svenska.yle.fi) | -1 | public | State | Yes | Swedish-language Yle |

## Flagged sources (NOT aggregated)

These sources are excluded from aggregation due to documented patterns of disinformation, conspiracy content, or content that fails basic factual standards. They are listed here for transparency.

| Source | Reason |
|--------|--------|
| MV-lehti | Long history of disinformation, conspiracy content, white nationalism |
| Magneettimedia | Antisemitic content, conspiracy theories |
| Oikea Media | Frequent conspiracy content and unverified claims |

**Inclusion criteria for flagging**:
1. Documented pattern (3+ instances) of demonstrably false claims, OR
2. Editorial endorsement of conspiracy theories, OR
3. Sanctions/rulings by Julkisen sanan neuvosto (JSN) for repeated violations

Flagging is reversible. If a flagged source's editorial standards change verifiably, the flag can be removed via methodology update.

## Sources under consideration

| Source | Status | Note |
|--------|--------|------|
| Uusi Suomi (uusisuomi.fi) | Considering | Mixed content (editorial + blog platform) |
| Maaseudun Tulevaisuus | Considering | Agricultural/rural, often center-right |
| Aamulehti | Considering | Tampere regional, broadly center |
| Turun Sanomat | Considering | Turku regional, broadly center |
| Kaleva | Considering | Oulu regional, broadly center |

## Notes on classifications

- **Party-organ classification is factual** (the outlet is legally/financially affiliated with a party). The bias score reflects the typical editorial output, not just the affiliation.
- **Bias scores are starting points** — they will be refined based on rolling article-level analysis.
- **Source diversity matters** — a left-leaning outlet that quotes diverse sources scores differently from one that doesn't.

## How to challenge a classification

Open a GitHub Issue with:
1. The source name and current classification
2. Your proposed reclassification
3. Evidence (specific articles, ownership facts, editorial statements)

Issues tagged `source-review`. All changes are public and discussed.
