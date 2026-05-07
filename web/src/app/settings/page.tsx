import type { Metadata } from "next";
import { ApiError, getLawnProfile } from "@/lib/api";
import { LawnProfileForm } from "@/components/forms/lawn-profile-form";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

export const metadata: Metadata = { title: "Settings" };

export default async function SettingsPage() {
  let profile = null;
  let loadError: string | null = null;

  try {
    profile = await getLawnProfile();
  } catch (error) {
    if (error instanceof ApiError && error.status === 404) {
      // No profile yet is expected on a fresh install.
    } else if (error instanceof ApiError) {
      loadError = `Unable to load the current lawn profile (${error.status}). Check API connectivity and try again.`;
    } else {
      loadError = "Unable to load the current lawn profile right now. Check API connectivity and try again.";
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">Settings</h1>
        <p className="text-sm text-muted-foreground">Lawn profile &amp; preferences</p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Lawn profile</CardTitle>
          <CardDescription>
            {loadError
              ? "The existing profile could not be loaded."
              : profile
                ? "Update your lawn details."
                : "Set up your lawn profile to get started."}
          </CardDescription>
        </CardHeader>
        <CardContent>
          {loadError ? (
            <div className="rounded-lg border border-destructive/20 bg-destructive/5 p-4 text-sm text-destructive">
              {loadError}
            </div>
          ) : (
            <LawnProfileForm defaultValues={profile ?? undefined} />
          )}
        </CardContent>
      </Card>
    </div>
  );
}
