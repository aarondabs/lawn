import type { Metadata } from "next";
import { Bell } from "lucide-react";

import { listReminders } from "@/lib/api";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { NewReminderDialog } from "./_components/new-reminder-dialog";
import { ReminderActions } from "./_components/reminder-actions";

export const metadata: Metadata = { title: "Reminders" };

const TYPE_COLORS: Record<string, string> = {
  treatment: "bg-emerald-100 text-emerald-800 dark:bg-emerald-900/30 dark:text-emerald-300",
  cultural: "bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-300",
  check: "bg-amber-100 text-amber-800 dark:bg-amber-900/30 dark:text-amber-300",
  other: "bg-zinc-100 text-zinc-700 dark:bg-zinc-800 dark:text-zinc-300",
};

function formatDate(dateStr: string) {
  // Parse as local date to avoid UTC offset shifting the display
  const [y, m, d] = dateStr.split("-").map(Number);
  return new Date(y, m - 1, d).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

function isOverdue(dateStr: string) {
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const [y, m, d] = dateStr.split("-").map(Number);
  return new Date(y, m - 1, d) < today;
}

export default async function RemindersPage() {
  const reminders = await listReminders({ completed: false }).catch(() => []);

  const overdue = reminders.filter((r) => isOverdue(r.due_date));
  const upcoming = reminders.filter((r) => !isOverdue(r.due_date));

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold">Reminders</h1>
          <p className="text-sm text-muted-foreground">
            {reminders.length} pending
            {overdue.length > 0 && (
              <span className="ml-1 text-red-600 dark:text-red-400">
                ({overdue.length} overdue)
              </span>
            )}
          </p>
        </div>
        <NewReminderDialog />
      </div>

      {reminders.length === 0 && (
        <div className="flex flex-col items-center gap-3 rounded-lg border border-dashed py-16 text-center">
          <Bell className="h-10 w-10 text-muted-foreground/40" />
          <p className="text-muted-foreground">No pending reminders.</p>
          <NewReminderDialog />
        </div>
      )}

      {reminders.length > 0 && (
        <>
          {/* Desktop table */}
          <div className="hidden rounded-md border md:block">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Due</TableHead>
                  <TableHead>Type</TableHead>
                  <TableHead>Description</TableHead>
                  <TableHead />
                </TableRow>
              </TableHeader>
              <TableBody>
                {overdue.length > 0 && (
                  <>
                    <TableRow className="bg-red-50/50 dark:bg-red-900/10">
                      <TableCell
                        colSpan={4}
                        className="py-1.5 text-xs font-semibold uppercase tracking-wide text-red-600 dark:text-red-400"
                      >
                        Overdue
                      </TableCell>
                    </TableRow>
                    {overdue.map((r) => (
                      <TableRow key={r.id} className="bg-red-50/30 dark:bg-red-900/5">
                        <TableCell className="font-medium text-red-700 dark:text-red-400">
                          {formatDate(r.due_date)}
                        </TableCell>
                        <TableCell>
                          <span
                            className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${TYPE_COLORS[r.reminder_type] ?? TYPE_COLORS.other}`}
                          >
                            {r.reminder_type}
                          </span>
                        </TableCell>
                        <TableCell>{r.description}</TableCell>
                        <TableCell className="text-right">
                          <ReminderActions reminder={r} />
                        </TableCell>
                      </TableRow>
                    ))}
                  </>
                )}
                {upcoming.length > 0 && (
                  <>
                    {overdue.length > 0 && (
                      <TableRow className="bg-muted/30">
                        <TableCell
                          colSpan={4}
                          className="py-1.5 text-xs font-semibold uppercase tracking-wide text-muted-foreground"
                        >
                          Upcoming
                        </TableCell>
                      </TableRow>
                    )}
                    {upcoming.map((r) => (
                      <TableRow key={r.id}>
                        <TableCell>{formatDate(r.due_date)}</TableCell>
                        <TableCell>
                          <span
                            className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${TYPE_COLORS[r.reminder_type] ?? TYPE_COLORS.other}`}
                          >
                            {r.reminder_type}
                          </span>
                        </TableCell>
                        <TableCell>{r.description}</TableCell>
                        <TableCell className="text-right">
                          <ReminderActions reminder={r} />
                        </TableCell>
                      </TableRow>
                    ))}
                  </>
                )}
              </TableBody>
            </Table>
          </div>

          {/* Mobile card list */}
          <div className="space-y-3 md:hidden">
            {reminders.map((r) => (
              <Card
                key={r.id}
                className={isOverdue(r.due_date) ? "border-red-300 dark:border-red-700" : ""}
              >
                <CardContent className="flex items-center gap-3 py-3">
                  <Bell
                    className={`h-5 w-5 shrink-0 ${
                      isOverdue(r.due_date)
                        ? "text-red-500"
                        : "text-amber-500"
                    }`}
                  />
                  <div className="min-w-0 flex-1">
                    <p className="truncate font-medium">{r.description}</p>
                    <p className="text-xs text-muted-foreground">
                      {isOverdue(r.due_date) ? "Overdue · " : ""}
                      {formatDate(r.due_date)}
                    </p>
                  </div>
                  <Badge
                    variant="outline"
                    className={`shrink-0 text-xs ${TYPE_COLORS[r.reminder_type] ?? TYPE_COLORS.other}`}
                  >
                    {r.reminder_type}
                  </Badge>
                  <ReminderActions reminder={r} />
                </CardContent>
              </Card>
            ))}
          </div>
        </>
      )}
    </div>
  );
}
