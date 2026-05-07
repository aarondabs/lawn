import type { Metadata } from "next";
import Link from "next/link";
import { ArrowLeft } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { SoilTestForm } from "@/components/forms/soil-test-form";

export const metadata: Metadata = { title: "New Soil Test" };

export default function NewSoilTestPage() {
  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <Button asChild variant="ghost" size="sm">
          <Link href="/soil-tests"><ArrowLeft className="mr-1 h-4 w-4" />Soil Tests</Link>
        </Button>
      </div>
      <div>
        <h1 className="text-2xl font-semibold">Add soil test</h1>
      </div>
      <Card className="max-w-2xl">
        <CardHeader><CardTitle className="text-base">Test results</CardTitle></CardHeader>
        <CardContent>
          <SoilTestForm />
        </CardContent>
      </Card>
    </div>
  );
}
