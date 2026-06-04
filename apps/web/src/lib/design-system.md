# Design system

This document records the visual decisions made for the Finnish Bias Tracker
frontend. Every component in `src/lib/components/` should align with what's
documented here. When implementations need to diverge, this document gets
updated, not the components.

## Philosophy

The visual language is deliberately restrained. The reference points are
content-focused publications and government information sites from roughly
2017 to 2020: solid colors, plain typography, 1px borders, light backgrounds,
no gradients, no glassmorphism, no glow effects. Think Stripe documentation,
Gov.uk, mid-period Medium, FiveThirtyEight before the redesigns.

The reason is functional, not nostalgic. The site shows political content
across the spectrum and asks the reader to think about framing. Visual
sobriety helps the reader take the content seriously. A site that looked
like a 2026 AI demo; animated gradients, glowing accents, rounded-2xl
everything — would undercut the methodology the project is trying to
demonstrate.

## Colors

Two parallel color systems. They serve different purposes and are used in
different components.

### Source color: party identity

Each source is associated with a color reflecting its Finnish political
identity. This is **not** a bias-score gradient — it encodes which Finnish
political tradition the source historically aligns with.

In Finnish political color convention (different from the US-based convention):

- **Blue** = the right (Kokoomus, Perussuomalaiset)
- **Red** = the left (SDP, Vasemmistoliitto)
- **Green** = the Centre (Keskusta) and Greens (Vihreät)
- **Yellow** = the Swedish-speaking minority (SFP/RKP)
- **Grey** = independent / mainstream / no party affiliation

Source-to-color mapping for v1:

| Source              | Color label   | Reasoning                          |
| ------------------- | ------------- | ---------------------------------- |
| Suomen Uutiset      | deep blue     | Perussuomalaiset organ (right +2)  |
| Verkkouutiset       | lighter blue  | Kokoomus organ (right +1)          |
| HBL                 | yellow        | RKP-adjacent Swedish-language      |
| Svenska Yle         | yellow        | Swedish-language public service    |
| Suomenmaa           | green         | Keskusta organ (centre)            |
| Kansan Uutiset      | bright red    | Vasemmistoliitto organ (left -2)   |
| Demokraatti         | softer red    | SDP organ (left -1 to -2)          |
| Yle                 | grey          | Public broadcaster, no party tie   |
| Helsingin Sanomat   | grey          | Independent mainstream             |
| Iltalehti           | grey          | Tabloid, Alma Media                |
| Ilta-Sanomat        | grey          | Tabloid, Sanoma                    |

This is a methodological statement: Finnish politics has its own visual
language. The site refuses to import US-style "red Democrat / blue
Republican" — a non-Finnish reader sees Finnish conventions and learns
them, not the other way around.

Exact hex values in `src/lib/colors.ts`. Pure #ff0000 reads as alarm; #b32d2d reads as
considered editorial choice.

### Bias color: scale position

Independent of source, each article (and the source's overall bias score)
gets a color reflecting position on the -3 to +3 scale. This is what
appears in the `BiasIndicator` pill.

| Score | Color label    | Use                                |
| ----- | -------------- | ---------------------------------- |
| -3    | deep red       | extreme left, party-organ tier     |
| -2    | red            | strong left                        |
| -1    | muted red      | mild left lean                     |
|  0    | warm grey      | neutral / balanced / wire          |
| +1    | muted blue     | mild right lean                    |
| +2    | blue           | strong right                       |
| +3    | deep blue      | extreme right, party-organ tier    |

The two systems are intentionally allowed to disagree on any individual
article. A Kansan Uutiset article that scores +2 displays as: source
badge in left-red (Kansan Uutiset's identity), bias indicator pill in
right-blue (the article's actual lean). That tension is meaningful and
the UI lets it surface.

## Typography

- **Body**: Inter, self-hosted via `@fontsource/inter`. System fallback
  for first paint: `-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto,
  sans-serif`.
- **Numbers**: tabular figures via `font-variant-numeric: tabular-nums`
  on bias scores and counts. Keeps columns aligned.
- **No serif in v1**. Defer to a later issue if methodology page wants
  it.
- **No Google Fonts CDN**. Self-host so page loads don't leak to Google.

## Spacing

Tailwind's default 4px scale. Components use `gap-2` (8px), `gap-4` (16px),
`gap-6` (24px) as the standard rhythm. Avoid arbitrary values like `gap-7`.

## Borders and shadows

- Borders are 1px, `border-slate-200` for cards on white, `border-slate-300`
  for stronger separation.
- No `box-shadow` anywhere in v1. Cards distinguish themselves via
  borders, not elevation.

## Rounding

- Default `rounded-sm` (2px) for most surfaces.
- `rounded` (4px) only for interactive elements (buttons, badges).
- Never `rounded-md` or higher. The 2024-2026 trend of rounded-everything
  is what we're avoiding.

## Dark mode

Not supported in v1. Decision deferred to a later issue. The reason is
scope (every color decided twice) and the 2017-2020 aesthetic baseline
defaults to light mode anyway.

## Component inventory

All shared components live under `src/lib/components/`. See the components
folder for the actual implementations; this is the list:

- `BiasIndicator.svelte` — colored pill showing a bias score (-3 to +3)
- `SourceBadge.svelte` — source name with party-identity color tint
- `LanguageTag.svelte` — small "SV" tag for Swedish-language articles
- `EmptyState.svelte` — generic "no results" placeholder
- `LoadingState.svelte` — generic loading skeleton

A `/design-system` route renders all five with sample data for visual
review.
