"use client";

import { useSyncExternalStore } from "react";
import { DEFAULT_THEME, THEME_STORAGE_KEY, type Theme } from "./theme-init";

// The theme lives on <html data-theme>, set before first paint by the inline
// script in app/layout.tsx and persisted to localStorage by setTheme().

export function storedTheme(): Theme {
  try {
    const t = localStorage.getItem(THEME_STORAGE_KEY);
    if (t === "light" || t === "dark") return t;
  } catch {}
  return DEFAULT_THEME;
}

export function setTheme(theme: Theme) {
  document.documentElement.setAttribute("data-theme", theme);
  try {
    localStorage.setItem(THEME_STORAGE_KEY, theme);
  } catch {}
}

function subscribe(onChange: () => void) {
  const observer = new MutationObserver(onChange);
  observer.observe(document.documentElement, { attributes: true, attributeFilter: ["data-theme"] });
  return () => observer.disconnect();
}

function currentTheme(): Theme {
  return document.documentElement.getAttribute("data-theme") === "light" ? "light" : "dark";
}

/** The active theme, re-rendering whenever the toggle changes it. */
export function useTheme(): Theme {
  return useSyncExternalStore(subscribe, currentTheme, () => DEFAULT_THEME);
}

/** A semantic color (tier, priority) used as text: full strength on dark, darkened on light. */
export function inkColor(color: string) {
  return `color-mix(in srgb, ${color} var(--ink-strength), black)`;
}
