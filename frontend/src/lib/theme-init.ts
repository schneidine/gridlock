// Shared by the server layout (inline script) and the client toggle (lib/theme.ts).
// Kept out of the "use client" module so the layout gets plain strings.
export type Theme = "dark" | "light";

export const THEME_STORAGE_KEY = "theme";
export const DEFAULT_THEME: Theme = "dark";

// Runs in <head> before the page paints, so a saved light theme never flashes dark.
export const THEME_INIT_SCRIPT = `(function(){try{var t=localStorage.getItem("${THEME_STORAGE_KEY}");if(t==="light"||t==="dark")document.documentElement.setAttribute("data-theme",t)}catch(e){}})()`;
