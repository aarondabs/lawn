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
import {
  CALIBRATED_RATE_UNITS,
  rateUnitLabel,
  readSprayerCalibration,
} from "@/lib/enums";
import type { Equipment } from "@/lib/api";

const EQUIPMENT_TYPES = ["sprayer", "spreader", "aerator", "dethatcher", "mower", "edger", "other"] as const;

const schema = z.object({
  type: z.enum(EQUIPMENT_TYPES),
  make: z.string().min(1),
  model: z.string().min(1),
  last_calibration_date: z.string().optional(),
  notes: z.string().optional(),
  // Sprayer-only. Stored in the calibration JSONB, not as columns.
  application_rate: z.string().optional(),
  application_rate_unit: z.enum(CALIBRATED_RATE_UNITS).optional(),
  nozzle_count: z.string().optional(),
  pressure_psi: z.string().optional(),
});

type FormValues = z.infer<typeof schema>;

const CALIBRATION_KEYS = ["application_rate", "application_rate_unit", "nozzle_count", "pressure_psi"];

/**
 * Fold the sprayer fields into the calibration blob, preserving any other keys
 * already there. Switching a machine away from `sprayer` clears them, so a
 * stale rate cannot go on prefilling tank fills.
 */
function buildCalibration(
  values: FormValues,
  existing: Record<string, unknown> | null | undefined,
): Record<string, unknown> | null {
  const calibration: Record<string, unknown> = { ...(existing ?? {}) };
  for (const key of CALIBRATION_KEYS) delete calibration[key];

  if (values.type === "sprayer") {
    const rate = values.application_rate?.trim();
    if (rate) {
      calibration.application_rate = Number(rate);
      calibration.application_rate_unit = values.application_rate_unit ?? "gal_per_1000";
    }
    const nozzles = values.nozzle_count?.trim();
    if (nozzles) calibration.nozzle_count = Number(nozzles);
    const psi = values.pressure_psi?.trim();
    if (psi) calibration.pressure_psi = Number(psi);
  }

  return Object.keys(calibration).length > 0 ? calibration : null;
}

type Props = {
  equipment?: Equipment;
  onSuccess?: () => void;
};

export function EquipmentForm({ equipment, onSuccess }: Props) {
  const router = useRouter();

  const existingCalibration = readSprayerCalibration(equipment?.calibration);

  const form = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: {
      type: (equipment?.type as typeof EQUIPMENT_TYPES[number]) ?? "sprayer",
      make: equipment?.make ?? "",
      model: equipment?.model ?? "",
      last_calibration_date: equipment?.last_calibration_date ?? "",
      notes: equipment?.notes ?? "",
      application_rate: existingCalibration.application_rate?.toString() ?? "",
      application_rate_unit: existingCalibration.application_rate_unit ?? "gal_per_1000",
      nozzle_count: existingCalibration.nozzle_count?.toString() ?? "",
      pressure_psi: existingCalibration.pressure_psi?.toString() ?? "",
    },
  });

  const isSprayer = form.watch("type") === "sprayer";

  async function onSubmit(values: FormValues) {
    const payload = {
      type: values.type,
      make: values.make,
      model: values.model,
      calibration: buildCalibration(values, equipment?.calibration),
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
        {isSprayer && (
          <div className="rounded-lg border bg-muted/40 p-4">
            <div className="mb-3">
              <h3 className="font-medium">Calibration</h3>
              <p className="text-xs text-muted-foreground">
                The application rate turns a tank volume into the area it covers, and prefills every
                tank fill on a liquid treatment.
              </p>
            </div>
            <div className="grid gap-4 sm:grid-cols-2">
              <FormField control={form.control} name="application_rate" render={({ field }) => (
                <FormItem>
                  <FormLabel>Application rate</FormLabel>
                  <FormControl>
                    <Input type="number" step="0.01" inputMode="decimal" placeholder="e.g. 1.0" {...field} />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )} />
              <FormField control={form.control} name="application_rate_unit" render={({ field }) => (
                <FormItem>
                  <FormLabel>Rate unit</FormLabel>
                  <Select value={field.value ?? "gal_per_1000"} onValueChange={field.onChange}>
                    <FormControl>
                      <SelectTrigger>
                        <SelectValue>{rateUnitLabel(field.value ?? "gal_per_1000")}</SelectValue>
                      </SelectTrigger>
                    </FormControl>
                    <SelectContent>
                      {CALIBRATED_RATE_UNITS.map((u) => (
                        <SelectItem key={u} value={u}>{rateUnitLabel(u)}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  <FormMessage />
                </FormItem>
              )} />
              <FormField control={form.control} name="nozzle_count" render={({ field }) => (
                <FormItem>
                  <FormLabel>Nozzles</FormLabel>
                  <FormControl><Input type="number" placeholder="optional" {...field} /></FormControl>
                  <FormMessage />
                </FormItem>
              )} />
              <FormField control={form.control} name="pressure_psi" render={({ field }) => (
                <FormItem>
                  <FormLabel>Pressure (psi)</FormLabel>
                  <FormControl><Input type="number" step="0.1" placeholder="optional" {...field} /></FormControl>
                  <FormMessage />
                </FormItem>
              )} />
            </div>
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
          {form.formState.isSubmitting ? "Saving…" : equipment ? "Save changes" : "Add equipment"}
        </Button>
      </form>
    </Form>
  );
}
