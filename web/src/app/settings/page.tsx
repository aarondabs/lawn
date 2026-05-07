import type { Metadata } from "next";
import { getLawnProfile } from "@/lib/api";
import { LawnProfileForm } from "@/components/forms/lawn-profile-form";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

export const metadata: Metadata = { title: "Settings" };

export default async function SettingsPage() {
  let profile = null;
  try {
    profile = await getLawnProfile();
  } catch {
    // 404 = no profile yet, that's fine
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
            {profile ? "Update your lawn details." : "Set up your lawn profile to get started."}
          </CardDescription>
        </CardHeader>
        <CardContent>
          <LawnProfileForm defaultValues={profile ?? undefined} />
        </CardContent>
      </Card>
    </div>
  );
}
