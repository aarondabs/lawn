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
import { addIrrigationZone, updateIrrigationZone } from "@/app/actions/irrigation-zone";
import type { IrrigationZone } from "@/lib/api";

const HEAD_TYPES = ["rotor", "spray", "mp_rotator", "drip", "hybrid"] as const;
const SUN_EXPOSURES = ["full_sun", "partial_sun", "partial_shade", "full_shade"] as const;
const SLOPES = ["flat", "mild", "moderate", "steep"] as const;
const SOIL_TYPES = ["sand", "sandy_loam", "loam", "silty_loam", "silty_clay_loam", "clay_loam", "clay"] as const;
const ZONE_CATEGORIES = ["turf", "trees_shrubs", "ornamental", "inactive"] as const;

const schema = z.object({
  zone_number: z.coerce.number().int().positive(),
  name: z.string().min(1),
  rachio_zone_id: z.string().optional(),
  zone_category: z.enum(ZONE_CATEGORIES),
  sqft: z.coerce.number().int().positive().optional(),
  head_type: z.enum(HEAD_TYPES),
  nozzle_gpm: z.coerce.number().positive().optional(),
  precipitation_rate_in_per_hr: z.coerce.number().positive().optional(),
  sun_exposure: z.enum(SUN_EXPOSURES),
  slope: z.enum(SLOPES),
  soil_type_override: z.enum(SOIL_TYPES).optional(),
  notes: z.string().optional(),
});

type FormValues = z.infer<typeof schema>;

type Props = {
  zone?: IrrigationZone;
  onSuccess?: () => void;
};

export function IrrigationZoneForm({ zone, onSuccess }: Props) {
  const router = useRouter();

  const form = useForm<FormValues>({
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    resolver: zodResolver(schema) as any,
    defaultValues: {
      zone_number: zone?.zone_number ?? undefined,
      name: zone?.name ?? "",
      rachio_zone_id: zone?.rachio_zone_id ?? "",
      zone_category: zone?.zone_category ?? "turf",
      sqft: zone?.sqft ?? undefined,
      head_type: (zone?.head_type as typeof HEAD_TYPES[number]) ?? "rotor",
      nozzle_gpm: zone?.nozzle_gpm ?? undefined,
      precipitation_rate_in_per_hr: zone?.precipitation_rate_in_per_hr ?? undefined,
      sun_exposure: (zone?.sun_exposure as typeof SUN_EXPOSURES[number]) ?? "full_sun",
      slope: (zone?.slope as typeof SLOPES[number]) ?? "flat",
      soil_type_override: (zone?.soil_type_override as typeof SOIL_TYPES[number]) ?? undefined,
      notes: zone?.notes ?? "",
    },
  });

  async function onSubmit(values: FormValues) {
    const payload = {
      zone_number: values.zone_number,
      name: values.name,
      rachio_zone_id: values.rachio_zone_id || null,
      zone_category: values.zone_category,
      sqft: values.sqft ?? null,
      head_type: values.head_type,
      nozzle_gpm: values.nozzle_gpm ?? null,
      precipitation_rate_in_per_hr: values.precipitation_rate_in_per_hr ?? null,
      sun_exposure: values.sun_exposure,
      slope: values.slope,
      soil_type_override: values.soil_type_override ?? null,
      notes: values.notes || null,
    };

    const result = zone
      ? await updateIrrigationZone(zone.id, payload)
      : await addIrrigationZone(payload);

    if (!result.ok) {
      toast.error(result.error);
      return;
    }

    toast.success(zone ? "Zone updated." : "Zone created.");
    onSuccess?.();
    if (!zone) {
      router.push("/zones");
    } else {
      router.refresh();
    }
  }

  return (
    <Form {...form}>
      <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
        <div className="grid gap-4 sm:grid-cols-2">
          <FormField control={form.control} name="zone_number" render={({ field }) => (
            <FormItem>
              <FormLabel>Zone number</FormLabel>
              <FormControl><Input type="number" {...field} /></FormControl>
              <FormMessage />
            </FormItem>
          )} />
          <FormField control={form.control} name="name" render={({ field }) => (
            <FormItem>
              <FormLabel>Name</FormLabel>
              <FormControl><Input {...field} /></FormControl>
              <FormMessage />
            </FormItem>
          )} />
          <FormField control={form.control} name="zone_category" render={({ field }) => (
            <FormItem>
              <FormLabel>Zone category</FormLabel>
              <Select onValueChange={field.onChange} defaultValue={field.value}>
                <FormControl><SelectTrigger><SelectValue /></SelectTrigger></FormControl>
                <SelectContent>
                  {ZONE_CATEGORIES.map((c) => <SelectItem key={c} value={c}>{c.replace(/_/g, " ")}</SelectItem>)}
                </SelectContent>
              </Select>
              <FormMessage />
            </FormItem>
          )} />
          <FormField control={form.control} name="head_type" render={({ field }) => (
            <FormItem>
              <FormLabel>Head type</FormLabel>
              <Select onValueChange={field.onChange} defaultValue={field.value}>
                <FormControl><SelectTrigger><SelectValue /></SelectTrigger></FormControl>
                <SelectContent>
                  {HEAD_TYPES.map((t) => <SelectItem key={t} value={t}>{t.replace(/_/g, " ")}</SelectItem>)}
                </SelectContent>
              </Select>
              <FormMessage />
            </FormItem>
          )} />
          <FormField control={form.control} name="sun_exposure" render={({ field }) => (
            <FormItem>
              <FormLabel>Sun exposure</FormLabel>
              <Select onValueChange={field.onChange} defaultValue={field.value}>
                <FormControl><SelectTrigger><SelectValue /></SelectTrigger></FormControl>
                <SelectContent>
                  {SUN_EXPOSURES.map((s) => <SelectItem key={s} value={s}>{s.replace(/_/g, " ")}</SelectItem>)}
                </SelectContent>
              </Select>
              <FormMessage />
            </FormItem>
          )} />
          <FormField control={form.control} name="slope" render={({ field }) => (
            <FormItem>
              <FormLabel>Slope</FormLabel>
              <Select onValueChange={field.onChange} defaultValue={field.value}>
                <FormControl><SelectTrigger><SelectValue /></SelectTrigger></FormControl>
                <SelectContent>
                  {SLOPES.map((s) => <SelectItem key={s} value={s}>{s}</SelectItem>)}
                </SelectContent>
              </Select>
              <FormMessage />
            </FormItem>
          )} />
          <FormField control={form.control} name="sqft" render={({ field }) => (
            <FormItem>
              <FormLabel>Area (sq ft)</FormLabel>
              <FormControl><Input type="number" placeholder="optional" {...field} /></FormControl>
              <FormMessage />
            </FormItem>
          )} />
          <FormField control={form.control} name="nozzle_gpm" render={({ field }) => (
            <FormItem>
              <FormLabel>Nozzle GPM</FormLabel>
              <FormControl><Input type="number" step="0.01" placeholder="optional" {...field} /></FormControl>
              <FormMessage />
            </FormItem>
          )} />
          <FormField control={form.control} name="precipitation_rate_in_per_hr" render={({ field }) => (
            <FormItem>
              <FormLabel>Precip rate (in/hr)</FormLabel>
              <FormControl><Input type="number" step="0.01" placeholder="optional" {...field} /></FormControl>
              <FormMessage />
            </FormItem>
          )} />
          <FormField control={form.control} name="rachio_zone_id" render={({ field }) => (
            <FormItem>
              <FormLabel>Rachio zone ID</FormLabel>
              <FormControl><Input placeholder="optional" {...field} /></FormControl>
              <FormMessage />
            </FormItem>
          )} />
          <FormField control={form.control} name="soil_type_override" render={({ field }) => (
            <FormItem>
              <FormLabel>Soil type override</FormLabel>
              <Select onValueChange={field.onChange} defaultValue={field.value}>
                <FormControl><SelectTrigger><SelectValue placeholder="Use lawn default" /></SelectTrigger></FormControl>
                <SelectContent>
                  {SOIL_TYPES.map((t) => <SelectItem key={t} value={t}>{t.replace(/_/g, " ")}</SelectItem>)}
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
          {form.formState.isSubmitting ? "Saving…" : zone ? "Save changes" : "Create zone"}
        </Button>
      </form>
    </Form>
  );
}
