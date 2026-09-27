"use server";

// TEMP: mock company sign-in for the dashboard, bypassing real auth for the
// duration of the project. Stores the chosen org in a plain cookie instead
// of a Supabase session.

import { cookies } from "next/headers";
import { redirect } from "next/navigation";

export async function mockSignIn(formData: FormData) {
  const orgId = formData.get("org_id");
  if (typeof orgId === "string" && orgId) {
    const cookieStore = await cookies();
    cookieStore.set("gridlock_org", orgId, { path: "/", maxAge: 60 * 60 * 24 * 30 });
  }
  redirect("/dashboard");
}

export async function mockSignOut() {
  const cookieStore = await cookies();
  cookieStore.delete("gridlock_org");
  redirect("/login");
}
