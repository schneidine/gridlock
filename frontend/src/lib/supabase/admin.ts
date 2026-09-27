import { createClient } from "@supabase/supabase-js";

/**
 * Service-role Supabase client for server-only writes that bypass RLS (e.g.
 * the AI insight cache). Never import this from a Client Component -- the
 * service-role key must not reach the browser.
 */
export function createAdminClient() {
  return createClient(process.env.NEXT_PUBLIC_SUPABASE_URL!, process.env.SUPABASE_SERVICE_ROLE_KEY!, {
    auth: { persistSession: false },
  });
}
