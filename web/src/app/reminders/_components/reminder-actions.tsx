"use client";

import { useState, useTransition } from "react";
import { useRouter } from "next/navigation";
import { toast } from "sonner";
import { Check, Clock, Trash2 } from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { markReminderComplete, snoozeReminderTo, removeReminder } from "@/app/actions/reminder";
import type { Reminder } from "@/lib/api";

type Props = { reminder: Reminder };

export function ReminderActions({ reminder }: Props) {
  const router = useRouter();
  const [isPending, startTransition] = useTransition();
  const [confirmDelete, setConfirmDelete] = useState(false);

  function handleComplete() {
    startTransition(async () => {
      const result = await markReminderComplete(reminder.id);
      if (!result.ok) {
        toast.error(result.error);
        return;
      }
      toast.success("Reminder completed.");
      router.refresh();
    });
  }

  function handleSnooze(days: number) {
    // Parse the date string as local date to avoid UTC shift
    const [y, m, d] = reminder.due_date.split("-").map(Number);
    const dt = new Date(y, m - 1, d);
    dt.setDate(dt.getDate() + days);
    const newDate = [
      dt.getFullYear(),
      String(dt.getMonth() + 1).padStart(2, "0"),
      String(dt.getDate()).padStart(2, "0"),
    ].join("-");
    startTransition(async () => {
      const result = await snoozeReminderTo(reminder.id, newDate);
      if (!result.ok) {
        toast.error(result.error);
        return;
      }
      toast.success(`Snoozed to ${newDate}.`);
      router.refresh();
    });
  }

  function handleDelete() {
    startTransition(async () => {
      const result = await removeReminder(reminder.id);
      if (!result.ok) {
        toast.error(result.error);
        return;
      }
      toast.success("Reminder deleted.");
      router.refresh();
    });
  }

  if (reminder.completed) {
    const completedLabel = reminder.completed_at
      ? new Date(reminder.completed_at).toLocaleDateString("en-US", { month: "short", day: "numeric" })
      : "";
    return (
      <span className="text-xs text-muted-foreground">
        Done {completedLabel}
      </span>
    );
  }

  return (
    <div className="flex items-center gap-1">
      <Button
        variant="ghost"
        size="sm"
        disabled={isPending}
        onClick={handleComplete}
        title="Mark complete"
      >
        <Check className="h-4 w-4" />
      </Button>

      <DropdownMenu>
        <DropdownMenuTrigger
          render={<Button variant="ghost" size="sm" disabled={isPending} title="Snooze" />}
        >
          <Clock className="h-4 w-4" />
        </DropdownMenuTrigger>
        <DropdownMenuContent align="end">
          <DropdownMenuItem onClick={() => handleSnooze(3)}>Snooze 3 days</DropdownMenuItem>
          <DropdownMenuItem onClick={() => handleSnooze(7)}>Snooze 1 week</DropdownMenuItem>
          <DropdownMenuItem onClick={() => handleSnooze(14)}>Snooze 2 weeks</DropdownMenuItem>
          <DropdownMenuItem onClick={() => handleSnooze(30)}>Snooze 1 month</DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>

      <AlertDialog open={confirmDelete} onOpenChange={setConfirmDelete}>
        <AlertDialogTrigger
          render={
            <Button
              variant="ghost"
              size="sm"
              className="text-destructive hover:text-destructive"
              disabled={isPending}
              title="Delete"
            />
          }
        >
          <Trash2 className="h-4 w-4" />
        </AlertDialogTrigger>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete reminder?</AlertDialogTitle>
            <AlertDialogDescription>
              &ldquo;{reminder.description}&rdquo; will be permanently deleted.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
              onClick={handleDelete}
            >
              Delete
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
