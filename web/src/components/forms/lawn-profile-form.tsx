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
import { saveLawnProfile } from "@/app/actions/lawn-profile";
import type { LawnProfile } from "@/lib/api";

const SOIL_TYPES = ["sand", "sandy_loam", "loam", "silty_loam", "silty_clay_loam", "clay_loam", "clay"] as const;
const WATER_SOURCES = ["city", "well", "mixed"] as const;

const schema = z.object({
  total_sqft: z.coerce.number().int().positive(),
  grass_type: z.string().min(1),
  establishment_date: z.string().optional(),
  target_mow_height_inches: z.coerce.number().positive(),
  latitude: z.coerce.number(),
  longitude: z.coerce.number(),
  usda_zone: z.string().min(1),
  climate_notes: z.string().optional(),
  soil_type: z.enum(SOIL_TYPES),
  water_source: z.enum(WATER_SOURCES),
});

type FormValues = z.infer<typeof schema>;

type Props = {
  defaultValues?: Partial<LawnProfile>;
};

export function LawnProfileForm({ defaultValues }: Props) {
  const router = useRouter();

  const form = useForm<FormValues>({
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    resolver: zodResolver(schema) as any,
    defaultValues: {
      total_sqft: defaultValues?.total_sqft ?? undefined,
      grass_type: defaultValues?.grass_type ?? "TTTF",
      establishment_date: defaultValues?.establishment_date ?? "",
      target_mow_height_inches: defaultValues?.target_mow_height_inches ?? undefined,
      latitude: defaultValues?.latitude ?? 39.0473,
      longitude: defaultValues?.longitude ?? -95.6752,
      usda_zone: defaultValues?.usda_zone ?? "6a",
      climate_notes: defaultValues?.climate_notes ?? "",
      soil_type: (defaultValues?.soil_type as typeof SOIL_TYPES[number]) ?? "loam",
      water_source: (defaultValues?.water_source as typeof WATER_SOURCES[number]) ?? "city",
    },
  });

  async function onSubmit(values: FormValues) {
    const result = await saveLawnProfile({
      total_sqft: values.total_sqft,
      grass_type: values.grass_type,
      establishment_date: values.establishment_date || null,
      target_mow_height_inches: values.target_mow_height_inches,
      latitude: values.latitude,
      longitude: values.longitude,
      usda_zone: values.usda_zone,
      climate_notes: values.climate_notes || null,
      soil_type: values.soil_type,
      water_source: values.water_source,
    });

    if (!result.ok) {
      toast.error(result.error);
      return;
    }

    toast.success("Lawn profile saved.");
    router.refresh();
  }

  return (
    <Form {...form}>
      <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
        <div className="grid gap-4 sm:grid-cols-2">
          <FormField
            control={form.control}
            name="total_sqft"
            render={({ field }) => (
              <FormItem>
                <FormLabel>Total sq ft</FormLabel>
                <FormControl><Input type="number" {...field} /></FormControl>
                <FormMessage />
              </FormItem>
            )}
          />
          <FormField
            control={form.control}
            name="grass_type"
            render={({ field }) => (
              <FormItem>
                <FormLabel>Grass type</FormLabel>
                <FormControl><Input {...field} /></FormControl>
                <FormMessage />
              </FormItem>
            )}
          />
          <FormField
            control={form.control}
            name="target_mow_height_inches"
            render={({ field }) => (
              <FormItem>
                <FormLabel>Target mow height (in)</FormLabel>
                <FormControl><Input type="number" step="0.5" {...field} /></FormControl>
                <FormMessage />
              </FormItem>
            )}
          />
          <FormField
            control={form.control}
            name="establishment_date"
            render={({ field }) => (
              <FormItem>
                <FormLabel>Establishment date</FormLabel>
                <FormControl><Input type="date" {...field} /></FormControl>
                <FormMessage />
              </FormItem>
            )}
          />
          <FormField
            control={form.control}
            name="latitude"
            render={({ field }) => (
              <FormItem>
                <FormLabel>Latitude</FormLabel>
                <FormControl><Input type="number" step="any" {...field} /></FormControl>
                <FormMessage />
              </FormItem>
            )}
          />
          <FormField
            control={form.control}
            name="longitude"
            render={({ field }) => (
              <FormItem>
                <FormLabel>Longitude</FormLabel>
                <FormControl><Input type="number" step="any" {...field} /></FormControl>
                <FormMessage />
              </FormItem>
            )}
          />
          <FormField
            control={form.control}
            name="usda_zone"
            render={({ field }) => (
              <FormItem>
                <FormLabel>USDA zone</FormLabel>
                <FormControl><Input {...field} /></FormControl>
                <FormMessage />
              </FormItem>
            )}
          />
          <FormField
            control={form.control}
            name="soil_type"
            render={({ field }) => (
              <FormItem>
                <FormLabel>Soil type</FormLabel>
                <Select onValueChange={field.onChange} defaultValue={field.value}>
                  <FormControl><SelectTrigger><SelectValue /></SelectTrigger></FormControl>
                  <SelectContent>
                    {SOIL_TYPES.map((t) => (
                      <SelectItem key={t} value={t}>{t.replace(/_/g, " ")}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                <FormMessage />
              </FormItem>
            )}
          />
          <FormField
            control={form.control}
            name="water_source"
            render={({ field }) => (
              <FormItem>
                <FormLabel>Water source</FormLabel>
                <Select onValueChange={field.onChange} defaultValue={field.value}>
                  <FormControl><SelectTrigger><SelectValue /></SelectTrigger></FormControl>
                  <SelectContent>
                    {WATER_SOURCES.map((s) => (
                      <SelectItem key={s} value={s}>{s}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                <FormMessage />
              </FormItem>
            )}
          />
        </div>
        <FormField
          control={form.control}
          name="climate_notes"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Climate notes</FormLabel>
              <FormControl><Textarea rows={3} {...field} /></FormControl>
              <FormMessage />
            </FormItem>
          )}
        />
        <Button type="submit" disabled={form.formState.isSubmitting}>
          {form.formState.isSubmitting ? "Saving…" : "Save profile"}
        </Button>
      </form>
    </Form>
  );
}
