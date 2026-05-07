"use client";

import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { useRouter } from "next/navigation";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Form, FormControl, FormField, FormItem, FormLabel, FormMessage } from "@/components/ui/form";
import { addSoilTest, updateSoilTest } from "@/app/actions/soil-test";
import type { SoilTest } from "@/lib/api";

const schema = z.object({
  sample_date: z.string().min(1),
  lab_name: z.string().min(1),
  ph: z.coerce.number().min(0).max(14).optional(),
  organic_matter_pct: z.coerce.number().nonnegative().optional(),
  phosphorus_ppm: z.coerce.number().nonnegative().optional(),
  potassium_ppm: z.coerce.number().nonnegative().optional(),
  calcium_ppm: z.coerce.number().nonnegative().optional(),
  magnesium_ppm: z.coerce.number().nonnegative().optional(),
  sulfur_ppm: z.coerce.number().nonnegative().optional(),
  iron_ppm: z.coerce.number().nonnegative().optional(),
  manganese_ppm: z.coerce.number().nonnegative().optional(),
  zinc_ppm: z.coerce.number().nonnegative().optional(),
  copper_ppm: z.coerce.number().nonnegative().optional(),
  boron_ppm: z.coerce.number().nonnegative().optional(),
  cec: z.coerce.number().nonnegative().optional(),
  lab_recommendations: z.string().optional(),
  notes: z.string().optional(),
});

type FormValues = z.infer<typeof schema>;

type Props = {
  soilTest?: SoilTest;
  onSuccess?: () => void;
};

function numField(val: number | null | undefined) {
  return val != null ? val : undefined;
}

export function SoilTestForm({ soilTest, onSuccess }: Props) {
  const router = useRouter();

  const form = useForm<FormValues>({
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    resolver: zodResolver(schema) as any,
    defaultValues: {
      sample_date: soilTest?.sample_date ?? "",
      lab_name: soilTest?.lab_name ?? "",
      ph: numField(soilTest?.ph),
      organic_matter_pct: numField(soilTest?.organic_matter_pct),
      phosphorus_ppm: numField(soilTest?.phosphorus_ppm),
      potassium_ppm: numField(soilTest?.potassium_ppm),
      calcium_ppm: numField(soilTest?.calcium_ppm),
      magnesium_ppm: numField(soilTest?.magnesium_ppm),
      sulfur_ppm: numField(soilTest?.sulfur_ppm),
      iron_ppm: numField(soilTest?.iron_ppm),
      manganese_ppm: numField(soilTest?.manganese_ppm),
      zinc_ppm: numField(soilTest?.zinc_ppm),
      copper_ppm: numField(soilTest?.copper_ppm),
      boron_ppm: numField(soilTest?.boron_ppm),
      cec: numField(soilTest?.cec),
      lab_recommendations: soilTest?.lab_recommendations ?? "",
      notes: soilTest?.notes ?? "",
    },
  });

  async function onSubmit(values: FormValues) {
    const payload = {
      sample_date: values.sample_date,
      lab_name: values.lab_name,
      ph: values.ph ?? null,
      organic_matter_pct: values.organic_matter_pct ?? null,
      phosphorus_ppm: values.phosphorus_ppm ?? null,
      potassium_ppm: values.potassium_ppm ?? null,
      calcium_ppm: values.calcium_ppm ?? null,
      magnesium_ppm: values.magnesium_ppm ?? null,
      sulfur_ppm: values.sulfur_ppm ?? null,
      iron_ppm: values.iron_ppm ?? null,
      manganese_ppm: values.manganese_ppm ?? null,
      zinc_ppm: values.zinc_ppm ?? null,
      copper_ppm: values.copper_ppm ?? null,
      boron_ppm: values.boron_ppm ?? null,
      cec: values.cec ?? null,
      base_saturation: soilTest?.base_saturation ?? null,
      lab_recommendations: values.lab_recommendations || null,
      pdf_path: soilTest?.pdf_path ?? null,
      notes: values.notes || null,
    };

    const result = soilTest
      ? await updateSoilTest(soilTest.id, payload)
      : await addSoilTest(payload);

    if (!result.ok) {
      toast.error(result.error);
      return;
    }

    toast.success(soilTest ? "Soil test updated." : "Soil test saved.");
    onSuccess?.();
    if (!soilTest) {
      router.push("/soil-tests");
    } else {
      router.refresh();
    }
  }

  return (
    <Form {...form}>
      <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
        <div className="grid gap-4 sm:grid-cols-2">
          <FormField control={form.control} name="sample_date" render={({ field }) => (
            <FormItem>
              <FormLabel>Sample date</FormLabel>
              <FormControl><Input type="date" {...field} /></FormControl>
              <FormMessage />
            </FormItem>
          )} />
          <FormField control={form.control} name="lab_name" render={({ field }) => (
            <FormItem>
              <FormLabel>Lab name</FormLabel>
              <FormControl><Input {...field} /></FormControl>
              <FormMessage />
            </FormItem>
          )} />
          <FormField control={form.control} name="ph" render={({ field }) => (
            <FormItem>
              <FormLabel>pH</FormLabel>
              <FormControl><Input type="number" step="0.1" placeholder="optional" {...field} /></FormControl>
              <FormMessage />
            </FormItem>
          )} />
          <FormField control={form.control} name="organic_matter_pct" render={({ field }) => (
            <FormItem>
              <FormLabel>Organic matter (%)</FormLabel>
              <FormControl><Input type="number" step="0.1" placeholder="optional" {...field} /></FormControl>
              <FormMessage />
            </FormItem>
          )} />
          <FormField control={form.control} name="phosphorus_ppm" render={({ field }) => (
            <FormItem>
              <FormLabel>Phosphorus (ppm)</FormLabel>
              <FormControl><Input type="number" step="0.1" placeholder="optional" {...field} /></FormControl>
              <FormMessage />
            </FormItem>
          )} />
          <FormField control={form.control} name="potassium_ppm" render={({ field }) => (
            <FormItem>
              <FormLabel>Potassium (ppm)</FormLabel>
              <FormControl><Input type="number" step="0.1" placeholder="optional" {...field} /></FormControl>
              <FormMessage />
            </FormItem>
          )} />
          <FormField control={form.control} name="calcium_ppm" render={({ field }) => (
            <FormItem>
              <FormLabel>Calcium (ppm)</FormLabel>
              <FormControl><Input type="number" step="0.1" placeholder="optional" {...field} /></FormControl>
              <FormMessage />
            </FormItem>
          )} />
          <FormField control={form.control} name="magnesium_ppm" render={({ field }) => (
            <FormItem>
              <FormLabel>Magnesium (ppm)</FormLabel>
              <FormControl><Input type="number" step="0.1" placeholder="optional" {...field} /></FormControl>
              <FormMessage />
            </FormItem>
          )} />
          <FormField control={form.control} name="cec" render={({ field }) => (
            <FormItem>
              <FormLabel>CEC</FormLabel>
              <FormControl><Input type="number" step="0.1" placeholder="optional" {...field} /></FormControl>
              <FormMessage />
            </FormItem>
          )} />
          <FormField control={form.control} name="sulfur_ppm" render={({ field }) => (
            <FormItem>
              <FormLabel>Sulfur (ppm)</FormLabel>
              <FormControl><Input type="number" step="0.1" placeholder="optional" {...field} /></FormControl>
              <FormMessage />
            </FormItem>
          )} />
        </div>
        <details className="text-sm">
          <summary className="cursor-pointer text-muted-foreground">Micronutrients (Fe, Mn, Zn, Cu, B)</summary>
          <div className="mt-3 grid gap-4 sm:grid-cols-3">
            {(["iron_ppm", "manganese_ppm", "zinc_ppm", "copper_ppm", "boron_ppm"] as const).map((key) => (
              <FormField key={key} control={form.control} name={key} render={({ field }) => (
                <FormItem>
                  <FormLabel>{key.replace("_ppm", "").replace("_", " ")} (ppm)</FormLabel>
                  <FormControl><Input type="number" step="0.01" placeholder="optional" {...field} /></FormControl>
                  <FormMessage />
                </FormItem>
              )} />
            ))}
          </div>
        </details>
        <FormField control={form.control} name="lab_recommendations" render={({ field }) => (
          <FormItem>
            <FormLabel>Lab recommendations</FormLabel>
            <FormControl><Textarea rows={3} {...field} /></FormControl>
            <FormMessage />
          </FormItem>
        )} />
        <FormField control={form.control} name="notes" render={({ field }) => (
          <FormItem>
            <FormLabel>Notes</FormLabel>
            <FormControl><Textarea rows={2} {...field} /></FormControl>
            <FormMessage />
          </FormItem>
        )} />
        <Button type="submit" disabled={form.formState.isSubmitting}>
          {form.formState.isSubmitting ? "Saving…" : soilTest ? "Save changes" : "Save soil test"}
        </Button>
      </form>
    </Form>
  );
}
