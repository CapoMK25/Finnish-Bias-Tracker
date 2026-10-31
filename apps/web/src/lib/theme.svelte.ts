/**
 * Theme state: 'light', 'dark', or 'system' (follow the OS setting).
 *
 * The inline script in app.html applies the saved theme before first paint so
 * the page never flashes the wrong colors. This store takes over once the app
 * has hydrated: call `theme.init()` once from the root layout's onMount.
 *
 * Keep STORAGE_KEY and THEME_COLORS in sync with the inline script in app.html.
 */

export type ThemeMode = 'light' | 'dark' | 'system';

const STORAGE_KEY = 'fbt-theme';
const THEME_COLORS = { light: '#fafaf8', dark: '#0b1220' } as const; // browser UI color on mobile
const ORDER: ThemeMode[] = ['system', 'light', 'dark'];

function readStoredMode(): ThemeMode {
  try {
    const value = localStorage.getItem(STORAGE_KEY);
    if (value === 'light' || value === 'dark') return value;
  } catch {
    // storage blocked (private mode, strict settings)
  }
  return 'system';
}

class ThemeState {
  /** The user's choice. */
  mode = $state<ThemeMode>('system');
  /** What the OS currently prefers. */
  systemDark = $state(false);
  /** False on the server and until init() has run; lets the UI avoid a hydration mismatch. */
  ready = $state(false);

  /** What is actually shown. */
  resolved = $derived<'light' | 'dark'>(
    this.mode === 'system' ? (this.systemDark ? 'dark' : 'light') : this.mode,
  );

  #started = false;

  /** Browser only. Safe to call more than once. */
  init(): void {
    if (this.#started || typeof window === 'undefined') return;
    this.#started = true;

    const query = window.matchMedia('(prefers-color-scheme: dark)');
    this.mode = readStoredMode();
    this.systemDark = query.matches;

    // The OS switches between light and dark (sunset, schedule)
    query.addEventListener('change', (event) => {
      this.systemDark = event.matches;
      this.#apply();
    });

    // Another tab changed the theme: follow it
    window.addEventListener('storage', (event) => {
      if (event.key !== STORAGE_KEY) return;
      this.mode = readStoredMode();
      this.#apply();
    });

    this.#apply();
    this.ready = true;
  }

  set(mode: ThemeMode): void {
    this.mode = mode;
    try {
      if (mode === 'system') localStorage.removeItem(STORAGE_KEY);
      else localStorage.setItem(STORAGE_KEY, mode);
    } catch {
      // not persisted, but the choice still applies
    }
    this.#apply();
  }

  /** system -> light -> dark -> system */
  cycle(): void {
    this.set(ORDER[(ORDER.indexOf(this.mode) + 1) % ORDER.length]);
  }

  #apply(): void {
    if (typeof document === 'undefined') return;
    const dark = this.resolved === 'dark';
    const root = document.documentElement;
    root.classList.toggle('dark', dark);
    root.style.colorScheme = dark ? 'dark' : 'light';
    document
      .querySelector('meta[name="theme-color"]')
      ?.setAttribute('content', THEME_COLORS[this.resolved]);
  }
}

// Shared instance. It is only ever changed in the browser (init and the event
// handlers are no-ops on the server), so sharing it between server requests is safe.
export const theme = new ThemeState();
