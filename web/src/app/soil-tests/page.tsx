import type { Metadata } from "next";
import Link from "next/link";
import { Plus, TestTube } from "lucide-react";

import { listSoilTests } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from "@/components/ui/table";

export const metadata: Metadata = { title: "Soil Tests" };

export default async function SoilTestsPage() {
  const tests = await listSoilTests().catch(() => []);
  const sorted = [...tests].sort((a, b) => b.sample_date.localeCompare(a.sample_date));

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold">Soil Tests</h1>
          <p className="text-sm text-muted-foreground">{sorted.length} test{sorted.length !== 1 ? "s" : ""}</p>
        </div>
        <Button asChild size="sm">
          <Link href="/soil-tests/new"><Plus className="mr-1 h-4 w-4" />Add</Link>
        </Button>
      </div>

      <div className="hidden rounded-md border md:block">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Date</TableHead>
              <TableHead>Lab</TableHead>
              <TableHead className="text-right">pH</TableHead>
              <TableHead className="text-right">OM%</TableHead>
              <TableHead className="text-right">P (ppm)</TableHead>
              <TableHead className="text-right">K (ppm)</TableHead>
              <TableHead />
            </TableRow>
          </TableHeader>
          <TableBody>
            {sorted.length === 0 && (
              <TableRow>
                <TableCell colSpan={7} className="text-center text-muted-foreground">No soil tests yet.</TableCell>
              </TableRow>
            )}
            {sorted.map((t) => (
              <TableRow key={t.id}>
                <TableCell>{t.sample_date}</TableCell>
                <TableCell>{t.lab_name}</TableCell>
                <TableCell className="text-right">{t.ph ?? "–"}</TableCell>
                <TableCell className="text-right">{t.organic_matter_pct ?? "–"}</TableCell>
                <TableCell className="text-right">{t.phosphorus_ppm ?? "–"}</TableCell>
                <TableCell className="text-right">{t.potassium_ppm ?? "–"}</TableCell>
                <TableCell>
                  <Button asChild variant="ghost" size="sm">
                    <Link href={`/soil-tests/${t.id}`}>View</Link>
                  </Button>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>

      <div className="space-y-3 md:hidden">
        {sorted.length === 0 && (
          <p className="text-center text-sm text-muted-foreground">No soil tests yet.</p>
        )}
        {sorted.map((t) => (
          <Link key={t.id} href={`/soil-tests/${t.id}`}>
            <Card className="transition-colors hover:bg-muted/50">
              <CardContent className="flex items-center gap-3 py-3">
                <TestTube className="h-5 w-5 shrink-0 text-amber-600" />
                <div className="min-w-0 flex-1">
                  <p className="truncate font-medium">{t.lab_name}</p>
                  <p className="text-xs text-muted-foreground">
                    {t.sample_date}
                    {t.ph != null && ` · pH ${t.ph}`}
                    {t.organic_matter_pct != null && ` · OM ${t.organic_matter_pct}%`}
                  </p>
                </div>
              </CardContent>
            </Card>
          </Link>
        ))}
      </div>
    </div>
  );
}
