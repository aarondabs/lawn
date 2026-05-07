import type { Metadata } from "next";
import Link from "next/link";
import { ArrowLeft } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { IrrigationZoneForm } from "@/components/forms/irrigation-zone-form";

export const metadata: Metadata = { title: "New Zone" };

export default function NewZonePage() {
  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <Button asChild variant="ghost" size="sm">
          <Link href="/zones"><ArrowLeft className="mr-1 h-4 w-4" />Zones</Link>
        </Button>
      </div>
      <div>
        <h1 className="text-2xl font-semibold">New irrigation zone</h1>
      </div>
      <Card className="max-w-2xl">
        <CardHeader><CardTitle className="text-base">Zone details</CardTitle></CardHeader>
        <CardContent>
          <IrrigationZoneForm />
        </CardContent>
      </Card>
    </div>
  );
}
