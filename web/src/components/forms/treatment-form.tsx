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
import { addTreatment, updateTreatment } from "@/app/actions/treatment";
import type { Treatment, Product, Equipment } from "@/lib/api";

const UNITS = ["lb", "oz", "fl_oz", "gal"] as const;
const APPLICATORS = ["self", "spouse", "lawn_service", "other"] as const;

const schema = z.object({
  applied_at: z.string().min(1),
  product_id: z.string().uuid("Select a product"),
  rate_applied: z.coerce.number().positive(),
  rate_unit: z.enum(UNITS),
  area_treated_sqft: z.coerce.number().int().positive(),
  equipment_id: z.string().optional(),
  applicator: z.enum(APPLICATORS),
  weather_temp_f: z.coerce.number().optional(),
  weather_wind_mph: z.coerce.number().nonnegative().optional(),
  weather_conditions: z.string().optional(),
  target: z.string().optional(),
  notes: z.string().optional(),
});

type FormValues = z.infer<typeof schema>;

function toLocalDatetimeString(iso: string) {
  return iso.slice(0, 16);
}

type Props = {
  treatment?: Treatment;
  products: Product[];
  equipment: Equipment[];
  defaultSqft?: number;
  onSuccess?: () => void;
};

export function TreatmentForm({ treatment, products, equipment, defaultSqft, onSuccess }: Props) {
  const router = useRouter();

  const form = useForm<FormValues>({
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    resolver: zodResolver(schema) as any,
    defaultValues: {
      applied_at: treatment
        ? toLocalDatetimeString(treatment.applied_at)
        : toLocalDatetimeString(new Date().toISOString()),
      product_id: treatment?.product_id ?? "",
      rate_applied: treatment?.rate_applied ?? undefined,
      rate_unit: (treatment?.rate_unit as typeof UNITS[number]) ?? "lb",
      area_treated_sqft: treatment?.area_treated_sqft ?? defaultSqft ?? undefined,
      equipment_id: treatment?.equipment_id ?? "",
      applicator: (treatment?.applicator as typeof APPLICATORS[number]) ?? "self",
      weather_temp_f: treatment?.weather_temp_f ?? undefined,
      weather_wind_mph: treatment?.weather_wind_mph ?? undefined,
      weather_conditions: treatment?.weather_conditions ?? "",
      target: treatment?.target ?? "",
      notes: treatment?.notes ?? "",
    },
  });

  async function onSubmit(values: FormValues) {
    const payload = {
      applied_at: new Date(values.applied_at).toISOString(),
      product_id: values.product_id,
      rate_applied: values.rate_applied,
      rate_unit: values.rate_unit,
      area_treated_sqft: values.area_treated_sqft,
      equipment_id: values.equipment_id || null,
      applicator: values.applicator,
      weather_temp_f: values.weather_temp_f ?? null,
      weather_wind_mph: values.weather_wind_mph ?? null,
      weather_conditions: values.weather_conditions || null,
      target: values.target || null,
      notes: values.notes || null,
    };

    const result = treatment
      ? await updateTreatment(treatment.id, payload)
      : await addTreatment(payload);

    if (!result.ok) {
      toast.error(result.error);
      return;
    }

    toast.success(treatment ? "Treatment updated." : "Treatment logged.");
    onSuccess?.();
    if (!treatment) {
      router.push("/treatments");
    } else {
      router.refresh();
    }
  }

  return (
    <Form {...form}>
      <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
        <div className="grid gap-4 sm:grid-cols-2">
          <FormField control={form.control} name="applied_at" render={({ field }) => (
            <FormItem>
              <FormLabel>Applied at</FormLabel>
              <FormControl><Input type="datetime-local" {...field} /></FormControl>
              <FormMessage />
            </FormItem>
          )} />
          <FormField control={form.control} name="product_id" render={({ field }) => (
            <FormItem>
              <FormLabel>Product</FormLabel>
              <Select onValueChange={field.onChange} defaultValue={field.value}>
                <FormControl><SelectTrigger><SelectValue placeholder="Select product" /></SelectTrigger></FormControl>
                <SelectContent>
                  {products.map((p) => (
                    <SelectItem key={p.id} value={p.id}>{p.name}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <FormMessage />
            </FormItem>
          )} />
          <div className="flex gap-2">
            <FormField control={form.control} name="rate_applied" render={({ field }) => (
              <FormItem className="flex-1">
                <FormLabel>Rate applied</FormLabel>
                <FormControl><Input type="number" step="0.01" {...field} /></FormControl>
                <FormMessage />
              </FormItem>
            )} />
            <FormField control={form.control} name="rate_unit" render={({ field }) => (
              <FormItem className="w-24">
                <FormLabel>Unit</FormLabel>
                <Select onValueChange={field.onChange} defaultValue={field.value}>
                  <FormControl><SelectTrigger><SelectValue /></SelectTrigger></FormControl>
                  <SelectContent>
                    {UNITS.map((u) => <SelectItem key={u} value={u}>{u}</SelectItem>)}
                  </SelectContent>
                </Select>
                <FormMessage />
              </FormItem>
            )} />
          </div>
          <FormField control={form.control} name="area_treated_sqft" render={({ field }) => (
            <FormItem>
              <FormLabel>Area treated (sq ft)</FormLabel>
              <FormControl><Input type="number" {...field} /></FormControl>
              <FormMessage />
            </FormItem>
          )} />
          <FormField control={form.control} name="equipment_id" render={({ field }) => (
            <FormItem>
              <FormLabel>Equipment</FormLabel>
              <Select onValueChange={field.onChange} defaultValue={field.value}>
                <FormControl><SelectTrigger><SelectValue placeholder="None" /></SelectTrigger></FormControl>
                <SelectContent>
                  {equipment.map((e) => (
                    <SelectItem key={e.id} value={e.id}>{e.make} {e.model}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <FormMessage />
            </FormItem>
          )} />
          <FormField control={form.control} name="applicator" render={({ field }) => (
            <FormItem>
              <FormLabel>Applicator</FormLabel>
              <Select onValueChange={field.onChange} defaultValue={field.value}>
                <FormControl><SelectTrigger><SelectValue /></SelectTrigger></FormControl>
                <SelectContent>
                  {APPLICATORS.map((a) => <SelectItem key={a} value={a}>{a}</SelectItem>)}
                </SelectContent>
              </Select>
              <FormMessage />
            </FormItem>
          )} />
          <FormField control={form.control} name="target" render={({ field }) => (
            <FormItem>
              <FormLabel>Target (what for?)</FormLabel>
              <FormControl><Input placeholder="e.g. broadleaf weeds" {...field} /></FormControl>
              <FormMessage />
            </FormItem>
          )} />
          <FormField control={form.control} name="weather_temp_f" render={({ field }) => (
            <FormItem>
              <FormLabel>Temp (°F)</FormLabel>
              <FormControl><Input type="number" placeholder="optional" {...field} /></FormControl>
              <FormMessage />
            </FormItem>
          )} />
          <FormField control={form.control} name="weather_wind_mph" render={({ field }) => (
            <FormItem>
              <FormLabel>Wind (mph)</FormLabel>
              <FormControl><Input type="number" placeholder="optional" {...field} /></FormControl>
              <FormMessage />
            </FormItem>
          )} />
          <FormField control={form.control} name="weather_conditions" render={({ field }) => (
            <FormItem>
              <FormLabel>Weather conditions</FormLabel>
              <FormControl><Input placeholder="optional" {...field} /></FormControl>
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
          {form.formState.isSubmitting ? "Saving…" : treatment ? "Save changes" : "Log treatment"}
        </Button>
      </form>
    </Form>
  );
}
