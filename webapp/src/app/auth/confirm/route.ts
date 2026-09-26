import { createClient } from "@/lib/supabase/server";
import { redirect } from "next/navigation";
import { type EmailOtpType } from "@supabase/supabase-js";
import { type NextRequest } from "next/server";

// Handles the magic-link redirect from Supabase Auth: exchanges the token
// hash in the URL for a session, then sends the user back to the app.
export async function GET(request: NextRequest) {
  const { searchParams } = new URL(request.url);
  const token_hash = searchParams.get("token_hash");
  const type = searchParams.get("type") as EmailOtpType | null;
  const next = searchParams.get("next") ?? "/";

  if (token_hash && type) {
    const supabase = await createClient();
    const { error } = await supabase.auth.verifyOtp({ type, token_hash });
    if (!error) {
      redirect(next);
    }
  }

  redirect("/login?error=invalid-link");
}
