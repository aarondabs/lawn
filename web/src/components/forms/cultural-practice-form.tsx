"use client";

import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { useRouter } from "next/navigation";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Form, FormControl, FormField, FormItem, FormLabel, FormMessage } from "@/components/ui/form";
import { addCulturalPractice, updateCulturalPractice } from "@/app/actions/cultural-practice";
import { toLocalDatetimeInputValue } from "@/lib/datetime";
import { showGuardrailFindings } from "@/lib/guardrails";
import { MOW_ORIENTATIONS, MOW_ORIENTATION_LABELS, readMowDetails } from "@/lib/enums";
import type { CulturalPractice, Equipment } from "@/lib/api";

const PRACTICE_TYPES = ["mow", "aerate", "dethatch", "overseed", "scalp", "leveling", "edge", "other"] as const;
const NO_EQUIPMENT_VALUE = "__none__";
const MOW_DETAIL_KEYS = ["cut_height_inches", "mow_orientation", "mow_orientation_other"];
// Mirrors MAX_CUT_HEIGHT_INCHES in api/src/lawn_api/schemas/cultural_practice.py.
const MAX_CUT_HEIGHT = 8;

const schema = z.object({
  performed_at: z.string().min(1),
  practice_type: z.enum(PRACTICE_TYPES),
  equipment_id: z.string().optional(),
  notes: z.string().optional(),
  cut_height_inches: z
    .string()
    .optional()
    .refine((v) => {
      if (!v?.trim()) return true;
      const n = Number(v);
      return n > 0 && n <= MAX_CUT_HEIGHT && Number.isInteger(n * 4);
    }, `Enter a quarter-inch height up to ${MAX_CUT_HEIGHT}"`),
  mow_orientation: z.enum(MOW_ORIENTATIONS).optional(),
  mow_orientation_other: z.string().optional(),
});

type FormValues = z.infer<typeof schema>;

/**
 * Merge the structured mow fields into the details blob, preserving any keys
 * other practice types may have put there. Switching a practice away from
 * `mow` clears the mow keys rather than leaving them orphaned.
 */
function buildDetails(
  values: FormValues,
  existing: Record<string, unknown> | null | undefined,
): Record<string, unknown> | null {
  const details: Record<string, unknown> = { ...(existing ?? {}) };
  for (const key of MOW_DETAIL_KEYS) delete details[key];

  if (values.practice_type === "mow") {
    const height = values.cut_height_inches?.trim();
    if (height) details.cut_height_inches = Number(height);
    if (values.mow_orientation) details.mow_orientation = values.mow_orientation;
    const other = values.mow_orientation_other?.trim();
    if (values.mow_orientation === "other" && other) details.mow_orientation_other = other;
  }

  return Object.keys(details).length > 0 ? details : null;
}

type Props = {
  practice?: CulturalPractice;
  equipment: Equipment[];
  initialPracticeType?: (typeof PRACTICE_TYPES)[number];
  /** Last-used mow height, falling back to lawn_profile.target_mow_height_inches. */
  defaultCutHeight?: number;
  onSuccess?: () => void;
};

export function CulturalPracticeForm({
  practice,
  equipment,
  initialPracticeType,
  defaultCutHeight,
  onSuccess,
}: Props) {
  const router = useRouter();
  const existingMow = readMowDetails(practice?.details);

  const form = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: {
      performed_at: practice
        ? toLocalDatetimeInputValue(practice.performed_at)
        : toLocalDatetimeInputValue(new Date()),
      practice_type: (practice?.practice_type as typeof PRACTICE_TYPES[number]) ?? initialPracticeType ?? "mow",
      equipment_id: practice?.equipment_id ?? "",
      notes: practice?.notes ?? "",
      // Height is prefilled but never locked -- Aaron varies it seasonally.
      cut_height_inches:
        existingMow.cut_height_inches?.toString() ?? (practice ? "" : defaultCutHeight?.toString() ?? ""),
      mow_orientation: existingMow.mow_orientation,
      mow_orientation_other: existingMow.mow_orientation_other ?? "",
    },
  });

  const practiceType = form.watch("practice_type");
  const isMow = practiceType === "mow";
  const orientation = form.watch("mow_orientation");

  async function onSubmit(values: FormValues) {
    const payload = {
      performed_at: new Date(values.performed_at).toISOString(),
      practice_type: values.practice_type,
      details: buildDetails(values, practice?.details),
      equipment_id: values.equipment_id || null,
      notes: values.notes || null,
    };

    const result = practice
      ? await updateCulturalPractice(practice.id, payload)
      : await addCulturalPractice(payload);

    if (!result.ok) {
      toast.error(result.error);
      return;
    }

    toast.success(practice ? "Practice updated." : "Practice logged.");
    // Overseeding inside a pre-emergent's blocking window warns here.
    showGuardrailFindings(result.data?.guardrail_findings);
    onSuccess?.();
    if (!practice) {
      router.push("/cultural");
    } else {
      router.refresh();
    }
  }

  const selectedEquipment = equipment.find((e) => e.id === form.watch("equipment_id"));

  return (
    <Form {...form}>
      <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
        <div className="grid gap-4 sm:grid-cols-2">
          <FormField control={form.control} name="performed_at" render={({ field }) => (
            <FormItem>
              <FormLabel>Date &amp; time</FormLabel>
              <FormControl><Input type="datetime-local" {...field} /></FormControl>
              <FormMessage />
            </FormItem>
          )} />
          <FormField control={form.control} name="practice_type" render={({ field }) => (
            <FormItem>
              <FormLabel>Practice type</FormLabel>
              <Select onValueChange={field.onChange} defaultValue={field.value}>
                <FormControl><SelectTrigger><SelectValue /></SelectTrigger></FormControl>
                <SelectContent>
                  {PRACTICE_TYPES.map((t) => <SelectItem key={t} value={t}>{t}</SelectItem>)}
                </SelectContent>
              </Select>
              <FormMessage />
            </FormItem>
          )} />
          <FormField control={form.control} name="equipment_id" render={({ field }) => (
            <FormItem>
              <FormLabel>Equipment</FormLabel>
              <Select
                value={field.value || NO_EQUIPMENT_VALUE}
                onValueChange={(value) => field.onChange(value === NO_EQUIPMENT_VALUE ? "" : value)}
              >
                <FormControl>
                  <SelectTrigger className="w-full">
                    <SelectValue placeholder="None">
                      {selectedEquipment ? `${selectedEquipment.make} ${selectedEquipment.model}` : "None"}
                    </SelectValue>
                  </SelectTrigger>
                </FormControl>
                <SelectContent className="min-w-[var(--radix-select-trigger-width)]">
                  <SelectItem value={NO_EQUIPMENT_VALUE}>None</SelectItem>
                  {equipment.map((e) => (
                    <SelectItem key={e.id} value={e.id} className="max-w-[32rem] truncate">
                      {e.make} {e.model}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <FormMessage />
            </FormItem>
          )} />
        </div>

        {isMow && (
          <div className="grid gap-4 sm:grid-cols-2">
            <FormField control={form.control} name="cut_height_inches" render={({ field }) => (
              <FormItem>
                <FormLabel>Cut height (in)</FormLabel>
                <FormControl>
                  <Input type="number" inputMode="decimal" step="0.25" min="0.25" max={MAX_CUT_HEIGHT} {...field} />
                </FormControl>
                <FormMessage />
              </FormItem>
            )} />
            <FormField control={form.control} name="mow_orientation" render={({ field }) => (
              <FormItem>
                <FormLabel>Mow direction</FormLabel>
                <Select value={field.value ?? ""} onValueChange={field.onChange}>
                  <FormControl>
                    <SelectTrigger className="w-full">
                      <SelectValue placeholder="Select direction">
                        {field.value ? MOW_ORIENTATION_LABELS[field.value] : "Select direction"}
                      </SelectValue>
                    </SelectTrigger>
                  </FormControl>
                  <SelectContent className="min-w-[var(--radix-select-trigger-width)]">
                    {MOW_ORIENTATIONS.map((o) => (
                      <SelectItem key={o} value={o}>{MOW_ORIENTATION_LABELS[o]}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                <FormMessage />
              </FormItem>
            )} />
            {orientation === "other" && (
              <FormField control={form.control} name="mow_orientation_other" render={({ field }) => (
                <FormItem className="sm:col-span-2">
                  <FormLabel>Describe the direction</FormLabel>
                  <FormControl><Input placeholder="e.g. contour around the pond" {...field} /></FormControl>
                  <FormMessage />
                </FormItem>
              )} />
            )}
          </div>
        )}

        <FormField control={form.control} name="notes" render={({ field }) => (
          <FormItem>
            <FormLabel>Notes</FormLabel>
            <FormControl><Textarea rows={2} {...field} /></FormControl>
            <FormMessage />
          </FormItem>
        )} />
        <Button type="submit" disabled={form.formState.isSubmitting}>
          {form.formState.isSubmitting ? "Saving…" : practice ? "Save changes" : "Log practice"}
        </Button>
      </form>
    </Form>
  );
}
