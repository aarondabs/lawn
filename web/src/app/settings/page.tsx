import type { Metadata } from "next";
import { Download } from "lucide-react";

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

      <Card>
        <CardHeader>
          <CardTitle>Data export</CardTitle>
          <CardDescription>
            Download your records as CSV. Flat, one row per line item, with derived fields (amount
            used, nitrogen, applications remaining) so each file stands alone in a spreadsheet.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid gap-2 sm:grid-cols-2">
            {[
              { label: "Treatments", href: "/api/export/treatments" },
              { label: "Cultural practices", href: "/api/export/cultural-practices" },
              { label: "Irrigation events", href: "/api/export/irrigation-events" },
              { label: "Products & inventory", href: "/api/export/products" },
              { label: "Soil tests", href: "/api/export/soil-tests" },
              { label: "Weather (daily)", href: "/api/export/weather-daily" },
            ].map((item) => (
              <a
                key={item.href}
                href={item.href}
                download
                className="flex items-center justify-between rounded-md border px-3 py-2 text-sm transition-colors hover:bg-muted/50"
              >
                <span>{item.label}</span>
                <Download className="h-4 w-4 text-muted-foreground" />
              </a>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
