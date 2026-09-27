"use client";

import { createBrowserClient } from "@supabase/ssr";

/**
 * Browser-side Supabase client (uses the anon key, safe to expose).
 * Use this in Client Components ("use client").
 */
export function createClient() {
  return createBrowserClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!
  );
}
