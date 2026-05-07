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
import type { CulturalPractice, Equipment } from "@/lib/api";

const PRACTICE_TYPES = ["mow", "aerate", "dethatch", "overseed", "scalp", "leveling", "edge", "other"] as const;
const NO_EQUIPMENT_VALUE = "__none__";

const schema = z.object({
  performed_at: z.string().min(1),
  practice_type: z.enum(PRACTICE_TYPES),
  equipment_id: z.string().optional(),
  notes: z.string().optional(),
});

type FormValues = z.infer<typeof schema>;

type Props = {
  practice?: CulturalPractice;
  equipment: Equipment[];
  initialPracticeType?: (typeof PRACTICE_TYPES)[number];
  onSuccess?: () => void;
};

export function CulturalPracticeForm({ practice, equipment, initialPracticeType, onSuccess }: Props) {
  const router = useRouter();

  const form = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: {
      performed_at: practice
        ? toLocalDatetimeInputValue(practice.performed_at)
        : toLocalDatetimeInputValue(new Date()),
      practice_type: (practice?.practice_type as typeof PRACTICE_TYPES[number]) ?? initialPracticeType ?? "mow",
      equipment_id: practice?.equipment_id ?? "",
      notes: practice?.notes ?? "",
    },
  });

  async function onSubmit(values: FormValues) {
    const payload = {
      performed_at: new Date(values.performed_at).toISOString(),
      practice_type: values.practice_type,
      details: practice?.details ?? null,
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
