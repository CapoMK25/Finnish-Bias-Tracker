# Calibration observations from an #18 source rollout

After adding party-organ scrapers, I audited 2 articles per source (10 total).

## Headline findings

**Scorer correctly identifies framing direction.** Suomen Uutiset (+2 source)
scored +1 on both articles, including one with explicit immigration framing.
KU (-2 source) scored -1 on an article featuring a Left Alliance MP's
criticism of the government. The scorer is detecting political framing — not
blind to it.

**Scorer is one step too conservative for party-organ content.** Articles
that read as ±2 in framing consistently score ±1. The rationales correctly
identify the partisan framing (e.g., noting "tekosyyltä" rhetoric in the
SU Espoo article, or the loaded book title in the KU article), but the
final score lands at ±1 instead of ±2.

## Hypothesis for v1.1 prompt

The current prompt likely reserves ±2 for thresholds that even explicit
party-organ content rarely crosses. Need to recalibrate the ±2 / ±3
boundaries downward.

Suggested prompt addition for v1.1:

  PARTY-AFFILIATED FRAMING: When an article from a party-affiliated outlet
  uses framing that clearly serves that party's editorial direction
  (loaded language, selection of sources, implied conclusions, omission
  of opposing views), score it ±2, not ±1. Reserve ±3 for explicit
  propaganda where the framing dominates the article completely.

## Specific examples for calibration test cases

- Suomen Uutiset "Espoon koulujen väkivaltaluvut räjähtäneet": should be +2
  (immigration framing, "panttaavat" language, implied cover-up)
- KU "Nyt yhteisöveroalesta vaietaan": should be -2 (party MP byline,
  loaded book reference, "Hallitus on ollut kummallisen vähäsanainen"
  framing)

## What works correctly

- Direction detection: 100% correct on partisan articles (4/4)
- Confidence calibration: still appropriately variable (0.5 on the book
  review, 0.7 on policy pieces)
- Topic classification: continues to be reliable
- Neutral articles correctly score 0 (foreign affairs wire coverage,
  apolitical content)