# Methodology

> This document explains how bias is determined in the Finnish Media Bias Tracker. It is intentionally public and will evolve based on feedback and audit findings. Every change is tracked in git history.

**Version**: 0.1 (Draft)
**Last updated**: 2026-05-24

## Core principles

1. **Transparency over authority** — we publish our reasoning, not just our conclusions.
2. **Two-tier bias** — sources have structural bias (ownership, party); articles have analytical bias (per-piece scoring).
3. **Confidence intervals matter** — every score has uncertainty; we don't hide it.
4. **Auditability** — every LLM score is stored with its rationale and can be inspected.
5. **No anonymous editorial control** — methodology changes are public and discussed in issues.

## Bias scale

A 7-point integer scale from -3 to +3:

| Score | Label | Description |
|-------|-------|-------------|
| -3 | Far Left | Explicit far-left framing, often party-organ |
| -2 | Left | Consistent left framing on most issues |
| -1 | Center-Left | Mild leftward lean in story selection or language |
| 0 | Center | No discernible lean, or balanced coverage |
| +1 | Center-Right | Mild rightward lean in story selection or language |
| +2 | Right | Consistent right framing on most issues |
| +3 | Far Right | Explicit far-right framing, often party-organ |

A separate **flagged** category exists for sources excluded from aggregation due to repeated disinformation. These are documented but not scored.

## Source-level bias (hard labels)

Source-level bias combines three factual signals:

1. **Ownership** — who funds and controls the outlet
2. **Party affiliation** — is it explicitly a party organ?
3. **Editorial history** — documented editorial stances over time

These are recorded in `docs/sources.md` with reasoning and citations.

**Hard labels do not change frequently.** They reflect structural facts, not individual article content.

## Article-level bias (soft labels)

Each article is scored independently using the following pipeline:

### Inputs
- Full article text (extracted via `trafilatura`)
- Source name and source-level bias
- Publication date
- Topic classification

### LLM scoring rubric

The LLM (Claude Haiku 4.5 for scale) is prompted to evaluate:

1. **Loaded language**: Are emotionally charged or politically coded words used? Provide examples.
2. **Source diversity**: Are sources within the article ideologically diverse, or one-sided?
3. **Framing choices**: Whose perspective is centered? Who is portrayed as the protagonist/antagonist?
4. **Story selection signals**: Is this story typically prioritized by one side?
5. **Omitted context**: Are relevant facts that would complicate the narrative left out?

### Output structure

Each scored article produces:

```json
{
  "bias_score": -1,
  "confidence": 0.78,
  "rationale": "Article frames austerity measures as 'necessary discipline' twice, sources are primarily government officials with no opposition perspective included.",
  "examples": [
    "use of 'tarpeellinen kuri' (necessary discipline) in headline",
    "no quotes from opposition parties despite story being about contested policy"
  ],
  "topic": "economic_policy",
  "summary": "Government defends new spending cuts amid criticism."
}
```

### Double-scoring

For higher-stakes articles (high-traffic, politically charged topics), we run the scoring **twice with different prompts** and use the average. Disagreements above a threshold trigger human review.

### Human review queue

Every Nth article (sampling rate TBD) is flagged for human review. Discrepancies between human and LLM scoring inform prompt iteration.

## Story clustering

Articles covering the same event are clustered using semantic embeddings:

1. Each article is embedded using Voyage AI's `voyage-3` model (multilingual, strong on Finnish).
2. Embeddings are clustered using HDBSCAN within rolling 48-hour windows.
3. Clusters with fewer than 3 articles are not displayed (insufficient signal).

## Blindspot detection

For each cluster, we compute:

- **Coverage distribution**: percentage of articles by bias bucket (left / center / right)
- **Entropy**: Shannon entropy of the distribution (higher = more balanced)
- **Blindspot label**:
  - `left_blindspot`: <10% of coverage is from left sources
  - `right_blindspot`: <10% of coverage is from right sources
  - `balanced`: roughly equal coverage across buckets

## Topic-aware scoring

Bias is topic-dependent. The same source might be:
- Center on EU/foreign policy
- Right-leaning on immigration
- Left-leaning on environmental policy

We track this by computing **rolling bias averages per (source, topic)** pair. The displayed source-level bias is the weighted average across all topics, but per-topic bias is available in source profiles.

## Limitations (acknowledged)

- **LLM scoring is imperfect.** It will make mistakes. We mitigate via double-scoring, human review, and transparent rationale.
- **Bias detection in Finnish is harder than English** due to less training data. Calibration may differ from English-language tools.
- **Centrist consensus is itself a perspective.** Calling something "center" doesn't mean it's neutral truth — it means it aligns with the median of Finnish political discourse.
- **We are not unbiased.** No methodology can be. We are *consistent and documented*, which is the next best thing.

## Methodology change log

| Version | Date | Change |
|---------|------|--------|
| 0.1 | 2026-05-24 | Initial draft |

## Open questions

These are unresolved and welcome input:

1. **How to handle paywalled articles?** Currently planned: store headlines and metadata only, no full-text analysis.
2. **Should opinion pieces be scored separately from news articles?** Currently: yes, with a clear `article_type` field.
3. **How to handle wire copy (STT) republished by partisan outlets?** Currently: score the publication context, not the wire copy itself.
4. **Should we track headline-vs-body bias separately?** (Tabloids often have inflammatory headlines and tame bodies.)

Discussion in [GitHub Issues](../../issues) tagged `methodology`.
