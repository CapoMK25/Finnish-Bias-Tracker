"""Dry run: what would the scope filter drop from the articles already stored?

Read-only: it only SELECTs. Use it to check that the filter is conservative
(only clearly out-of-scope pieces are dropped) and to see which URL sections
each outlet uses, so the section lists in src/relevance.py can be tuned.

Usage, from apps/scrapers with the venv active:
    python -m scripts.preview_scope_filter               # newest 5000 articles
    python -m scripts.preview_scope_filter --limit 20000 --show 15

The body is not loaded, so foreign-section pieces that mention Finland only in
their lead are judged on the title alone: the preview is slightly harsher than
the real filter.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from urllib.parse import urlparse

import psycopg

from src.config import settings
from src.relevance import check_scope


def section_of(url: str) -> str:
    parts = [p for p in urlparse(url or "").path.split("/") if p]
    return parts[0].lower() if parts else "(none)"


def analyze(rows: list[tuple[str, str, str]], show: int = 8) -> str:
    """rows: (source_slug, url, title). Returns a printable report."""
    totals: Counter[str] = Counter()
    dropped: Counter[str] = Counter()
    sections: dict[str, Counter[str]] = defaultdict(Counter)
    reasons: Counter[str] = Counter()
    samples: dict[str, list[tuple[str, str]]] = defaultdict(list)

    for slug, url, title in rows:
        decision = check_scope(title=title or "", url=url or "", source=slug)
        totals[slug] += 1
        sections[slug][section_of(url)] += 1
        if not decision.in_scope:
            dropped[slug] += 1
            reasons[decision.reason.split(":")[0]] += 1
            if len(samples[slug]) < show:
                samples[slug].append((decision.reason, title or ""))

    out: list[str] = []
    n, d = sum(totals.values()), sum(dropped.values())
    out.append(f"{n} articles checked, {d} would be dropped ({(100 * d / n) if n else 0:.0f}%)\n")

    out.append("== per outlet: dropped / total ==")
    for slug, total in sorted(totals.items(), key=lambda kv: -kv[1]):
        share = 100 * dropped[slug] / total
        out.append(f"  {slug:<22}{dropped[slug]:>5} / {total:<5} ({share:.0f}%)")

    out.append("\n== why (rule family) ==")
    for reason, count in reasons.most_common():
        out.append(f"  {reason:<28}{count:>5}")

    out.append("\n== URL sections per outlet (use this to tune the section lists) ==")
    for slug in sorted(totals):
        top = ", ".join(f"{sec} {cnt}" for sec, cnt in sections[slug].most_common(12))
        out.append(f"  {slug}: {top}")

    out.append(f"\n== what would be dropped: first {show} per outlet (CHECK THESE) ==")
    for slug in sorted(samples):
        out.append(f"  [{slug}]")
        for reason, title in samples[slug]:
            out.append(f"    {reason:<34} {title[:90]}")
    return "\n".join(out)


def main() -> None:
    parser = argparse.ArgumentParser(description="Dry-run the scope filter on stored articles.")
    parser.add_argument("--limit", type=int, default=5000, help="newest N articles (default 5000)")
    parser.add_argument("--show", type=int, default=8, help="dropped examples per outlet")
    args = parser.parse_args()

    query = """
        SELECT s.slug, a.url, a.title
        FROM articles a JOIN sources s ON s.id = a.source_id
        ORDER BY a.scraped_at DESC
        LIMIT %s
    """
    with psycopg.connect(settings.database_url) as conn, conn.cursor() as cur:
        cur.execute(query, (args.limit,))
        rows = [(r[0], r[1], r[2]) for r in cur.fetchall()]
    print(analyze(rows, show=args.show))


if __name__ == "__main__":
    main()
