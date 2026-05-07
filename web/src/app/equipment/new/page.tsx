import type { Metadata } from "next";
import Link from "next/link";
import { ArrowLeft } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { EquipmentForm } from "@/components/forms/equipment-form";

export const metadata: Metadata = { title: "New Equipment" };

export default function NewEquipmentPage() {
  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <Button asChild variant="ghost" size="sm">
          <Link href="/equipment"><ArrowLeft className="mr-1 h-4 w-4" />Equipment</Link>
        </Button>
      </div>
      <div>
        <h1 className="text-2xl font-semibold">Add equipment</h1>
      </div>
      <Card className="max-w-2xl">
        <CardHeader><CardTitle className="text-base">Equipment details</CardTitle></CardHeader>
        <CardContent>
          <EquipmentForm />
        </CardContent>
      </Card>
    </div>
  );
}
