/**
 * Compact relative-time formatter.
 *
 * Returns strings like "2h ago", "yesterday", "3 days ago" rather than
 * the verbose "2 hours ago" that Intl.RelativeTimeFormat produces by
 * default.
 *
 * For dates older than ~30 days, returns the formatted date instead
 * of a relative string ("12 May 2026"). After a month, "47 days ago"
 * stops being useful, visitors will want to see when something was
 * actually published.
 */

export function relativeTime(input: string | Date | null | undefined): string {
  if (!input) return '';

  const date = typeof input === 'string' ? new Date(input) : input;
  if (Number.isNaN(date.getTime())) return '';

  const now = Date.now();
  const diffMs = now - date.getTime();
  const diffSec = Math.floor(diffMs / 1000);
  const diffMin = Math.floor(diffSec / 60);
  const diffHour = Math.floor(diffMin / 60);
  const diffDay = Math.floor(diffHour / 24);

  if (diffSec < 60) return 'just now';
  if (diffMin < 60) return `${diffMin}m ago`;
  if (diffHour < 24) return `${diffHour}h ago`;
  if (diffDay === 1) return 'yesterday';
  if (diffDay < 30) return `${diffDay} days ago`;

  // Older than 30 days: show the actual date.
  return date.toLocaleDateString('en-GB', {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
  });
}
