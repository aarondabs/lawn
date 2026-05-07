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
import { addEquipment, updateEquipment } from "@/app/actions/equipment";
import type { Equipment } from "@/lib/api";

const EQUIPMENT_TYPES = ["sprayer", "spreader", "aerator", "dethatcher", "mower", "edger", "other"] as const;

const schema = z.object({
  type: z.enum(EQUIPMENT_TYPES),
  make: z.string().min(1),
  model: z.string().min(1),
  last_calibration_date: z.string().optional(),
  notes: z.string().optional(),
});

type FormValues = z.infer<typeof schema>;

type Props = {
  equipment?: Equipment;
  onSuccess?: () => void;
};

export function EquipmentForm({ equipment, onSuccess }: Props) {
  const router = useRouter();

  const form = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: {
      type: (equipment?.type as typeof EQUIPMENT_TYPES[number]) ?? "sprayer",
      make: equipment?.make ?? "",
      model: equipment?.model ?? "",
      last_calibration_date: equipment?.last_calibration_date ?? "",
      notes: equipment?.notes ?? "",
    },
  });

  async function onSubmit(values: FormValues) {
    const payload = {
      type: values.type,
      make: values.make,
      model: values.model,
      calibration: equipment?.calibration ?? null,
      last_calibration_date: values.last_calibration_date || null,
      notes: values.notes || null,
    };

    const result = equipment
      ? await updateEquipment(equipment.id, payload)
      : await addEquipment(payload);

    if (!result.ok) {
      toast.error(result.error);
      return;
    }

    toast.success(equipment ? "Equipment updated." : "Equipment added.");
    onSuccess?.();
    if (!equipment) {
      router.push("/equipment");
    } else {
      router.refresh();
    }
  }

  return (
    <Form {...form}>
      <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
        <div className="grid gap-4 sm:grid-cols-2">
          <FormField control={form.control} name="type" render={({ field }) => (
            <FormItem>
              <FormLabel>Type</FormLabel>
              <Select onValueChange={field.onChange} defaultValue={field.value}>
                <FormControl><SelectTrigger><SelectValue /></SelectTrigger></FormControl>
                <SelectContent>
                  {EQUIPMENT_TYPES.map((t) => <SelectItem key={t} value={t}>{t}</SelectItem>)}
                </SelectContent>
              </Select>
              <FormMessage />
            </FormItem>
          )} />
          <FormField control={form.control} name="make" render={({ field }) => (
            <FormItem>
              <FormLabel>Make</FormLabel>
              <FormControl><Input {...field} /></FormControl>
              <FormMessage />
            </FormItem>
          )} />
          <FormField control={form.control} name="model" render={({ field }) => (
            <FormItem>
              <FormLabel>Model</FormLabel>
              <FormControl><Input {...field} /></FormControl>
              <FormMessage />
            </FormItem>
          )} />
          <FormField control={form.control} name="last_calibration_date" render={({ field }) => (
            <FormItem>
              <FormLabel>Last calibration date</FormLabel>
              <FormControl><Input type="date" {...field} /></FormControl>
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
          {form.formState.isSubmitting ? "Saving…" : equipment ? "Save changes" : "Add equipment"}
        </Button>
      </form>
    </Form>
  );
}
