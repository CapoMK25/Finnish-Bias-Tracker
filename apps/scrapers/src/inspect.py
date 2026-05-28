"""Inspect command for browsing scored articles in the terminal.

Usage:
    python -m src.inspect                       # 10 most recent across all sources
    python -m src.inspect --limit 25            # 25 most recent
    python -m src.inspect --source yle          # Yle only
    python -m src.inspect --source yle --limit 5
    python -m src.inspect --full                # Include full rationale + examples
    python -m src.inspect --bias -2,2           # Only articles scored -2 or 2

Used during methodology calibration to audit how the scorer is performing.
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime
from typing import Any

from src.db.articles_repo import get_recent_scored_articles
from src.db.connection import close_pool


# ANSI color codes for terminal output. Disable via NO_COLOR=1 env var.
class Color:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN = "\033[36m"


def bias_color(score: int) -> str:
    """Color-code bias scores by direction and magnitude."""
    if score <= -2:
        return Color.RED
    if score == -1:
        return Color.YELLOW
    if score == 0:
        return Color.GREEN
    if score == 1:
        return Color.CYAN
    return Color.MAGENTA  # +2 or +3


def confidence_color(conf: float) -> str:
    """Color-code confidence: red below 0.4, yellow 0.4-0.6, green 0.6+."""
    if conf < 0.4:
        return Color.RED
    if conf < 0.6:
        return Color.YELLOW
    return Color.GREEN


def format_datetime(dt: datetime | None) -> str:
    """Compact datetime format. Returns 'unknown' if None."""
    if dt is None:
        return "unknown"
    return dt.strftime("%Y-%m-%d %H:%M")


def format_article(article: dict[str, Any], full: bool = False) -> str:
    """Render one article as colored text for terminal display."""
    lines: list[str] = []

    # Header: source + bias score + confidence
    bias = article["bias_score"]
    conf = float(article["confidence"])
    bc = bias_color(bias)
    cc = confidence_color(conf)

    bias_str = f"{bc}{bias:+d}{Color.RESET}" if bias else f"{bc} 0{Color.RESET}"
    header = (
        f"{Color.BOLD}{article['source_slug']:>20}{Color.RESET}  "
        f"bias={bias_str}  "
        f"conf={cc}{conf:.2f}{Color.RESET}  "
        f"topic={Color.CYAN}{article['topic']}{Color.RESET}  "
        f"type={article['article_type']}"
    )
    lines.append(header)

    # Title
    lines.append(f"  {Color.BOLD}{article['title']}{Color.RESET}")

    # URL + timestamps
    lines.append(f"  {Color.DIM}{article['url']}{Color.RESET}")
    pub = format_datetime(article["published_at"])
    scored = format_datetime(article["scored_at"])
    lines.append(
        f"  {Color.DIM}published: {pub}  scored: {scored}  "
        f"body: {article['body_length']} chars  "
        f"model: {article['model']}  prompt: {article['prompt_version']}{Color.RESET}"
    )

    # Summary
    if article.get("summary"):
        lines.append(f"  {Color.DIM}summary:{Color.RESET} {article['summary']}")

    # Full mode: rationale + examples
    if full:
        if article.get("rationale"):
            lines.append("")
            lines.append(f"  {Color.BOLD}Rationale:{Color.RESET}")
            for line in article["rationale"].split("\n"):
                lines.append(f"    {line}")

        examples = article.get("examples", [])
        if examples:
            lines.append("")
            lines.append(f"  {Color.BOLD}Examples:{Color.RESET}")
            for ex in examples:
                lines.append(f"    {Color.DIM}•{Color.RESET} {ex}")

    return "\n".join(lines)


def parse_bias_filter(value: str | None) -> set[int] | None:
    """Parse --bias arg like '-2,2' or '0' into a set of integers."""
    if value is None:
        return None
    try:
        return {int(part.strip()) for part in value.split(",")}
    except ValueError:
        print(f"Invalid --bias value: {value!r}. Expected comma-separated integers.")
        sys.exit(2)


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="inspect",
        description="Browse recently scored articles in the terminal for manual audit.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=10,
        help="Maximum number of articles to display (default: 10)",
    )
    parser.add_argument(
        "--source",
        type=str,
        default=None,
        help="Filter to a single source by slug (e.g., 'yle', 'hs')",
    )
    parser.add_argument(
        "--full",
        action="store_true",
        help="Show full rationale and example quotes (default: summary only)",
    )
    parser.add_argument(
        "--bias",
        type=str,
        default=None,
        metavar="SCORES",
        help="Filter to specific bias scores, e.g. '--bias -2,-1' or '--bias 0'",
    )
    args = parser.parse_args()

    bias_filter = parse_bias_filter(args.bias)

    try:
        articles = get_recent_scored_articles(
            limit=args.limit if not bias_filter else args.limit * 5,
            source_slug=args.source,
        )
    finally:
        # Defer pool close until after potential filtering
        pass

    # Apply bias filter (post-query so we don't complicate the SQL)
    if bias_filter is not None:
        articles = [a for a in articles if a["bias_score"] in bias_filter]
        articles = articles[: args.limit]

    if not articles:
        print(
            f"No articles found{' for source ' + args.source if args.source else ''}"
            f"{' matching bias filter' if bias_filter else ''}."
        )
        close_pool()
        return 0

    print(f"\nShowing {len(articles)} article(s):\n")
    for i, article in enumerate(articles, 1):
        print(f"{Color.DIM}─── #{i} ──────────────────────────────────────────────{Color.RESET}")
        print(format_article(article, full=args.full))
        print()

    close_pool()
    return 0


if __name__ == "__main__":
    sys.exit(main())
