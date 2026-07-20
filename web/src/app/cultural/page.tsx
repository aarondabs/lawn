import type { Metadata } from "next";
import Link from "next/link";
import { Shovel } from "lucide-react";

import { getLawnProfile, listCulturalPractices, listEquipment } from "@/lib/api";
import { defaultCutHeight, formatMowSummary } from "@/lib/enums";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from "@/components/ui/table";
import { NewCulturalDialog } from "./_components/new-cultural-dialog";

export const metadata: Metadata = { title: "Cultural Practices" };

function formatDate(iso: string) {
  return new Date(iso).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
}

export default async function CulturalPage() {
  const [practices, equipment, profile] = await Promise.all([
    listCulturalPractices().catch(() => []),
    listEquipment().catch(() => []),
    getLawnProfile().catch(() => null),
  ]);
  const cutHeightDefault = defaultCutHeight(practices, profile?.target_mow_height_inches);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold">Cultural Practices</h1>
          <p className="text-sm text-muted-foreground">{practices.length} record{practices.length !== 1 ? "s" : ""}</p>
        </div>
        <NewCulturalDialog equipment={equipment} defaultCutHeight={cutHeightDefault} />
      </div>

      <div className="hidden rounded-md border md:block">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Date</TableHead>
              <TableHead>Practice</TableHead>
              <TableHead>Detail</TableHead>
              <TableHead>Equipment</TableHead>
              <TableHead />
            </TableRow>
          </TableHeader>
          <TableBody>
            {practices.length === 0 && (
              <TableRow>
                <TableCell colSpan={5} className="text-center text-muted-foreground">No practices logged yet.</TableCell>
              </TableRow>
            )}
            {practices.map((p) => (
              <TableRow key={p.id}>
                <TableCell>{formatDate(p.performed_at)}</TableCell>
                <TableCell><Badge variant="secondary">{p.practice_type}</Badge></TableCell>
                <TableCell className="text-sm text-muted-foreground">
                  {formatMowSummary(p.details) ?? "–"}
                </TableCell>
                <TableCell>
                  {p.equipment_id
                    ? (() => {
                        const e = equipment.find((item) => item.id === p.equipment_id);
                        return e ? `${e.make} ${e.model}` : "–";
                      })()
                    : "–"}
                </TableCell>
                <TableCell>
                  <Button asChild variant="ghost" size="sm">
                    <Link href={`/cultural/${p.id}`}>View</Link>
                  </Button>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>

      <div className="space-y-3 md:hidden">
        {practices.length === 0 && (
          <p className="text-center text-sm text-muted-foreground">No practices logged yet.</p>
        )}
        {practices.map((p) => (
          <Link key={p.id} href={`/cultural/${p.id}`}>
            <Card className="transition-colors hover:bg-muted/50">
              <CardContent className="flex items-center gap-3 py-3">
                <Shovel className="h-5 w-5 shrink-0 text-muted-foreground" />
                <div className="min-w-0 flex-1">
                  <p className="truncate font-medium capitalize">{p.practice_type}</p>
                  <p className="truncate text-xs text-muted-foreground">
                    {[formatDate(p.performed_at), formatMowSummary(p.details)].filter(Boolean).join(" · ")}
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
