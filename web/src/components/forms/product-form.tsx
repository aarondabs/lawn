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
import { addProduct, updateProduct } from "@/app/actions/product";
import { RATE_UNITS, rateUnitLabel } from "@/lib/enums";
import type { Product } from "@/lib/api";

const PRODUCT_TYPES = [
  "fertilizer_synthetic",
  "fertilizer_organic",
  "herbicide_pre",
  "herbicide_post_broadleaf",
  "herbicide_post_grassy",
  "herbicide_non_selective",
  "fungicide",
  "insecticide",
  "biostimulant",
  "soil_amendment",
  "surfactant",
  "wetting_agent",
  "dye_marker",
  "seed",
  "other",
] as const;
const UNITS = RATE_UNITS;

const schema = z.object({
  name: z.string().min(1),
  manufacturer: z.string().min(1),
  product_type: z.enum(PRODUCT_TYPES),
  label_rate: z.coerce.number().positive(),
  label_rate_unit: z.enum(UNITS),
  reentry_interval_hours: z.coerce.number().int().nonnegative().optional(),
  min_reapplication_days: z.coerce.number().int().nonnegative().optional(),
  max_annual_rate: z.coerce.number().positive().optional(),
  max_annual_rate_unit: z.enum(UNITS).optional(),
  current_inventory: z.coerce.number().nonnegative().optional(),
  current_inventory_unit: z.enum(UNITS).optional(),
  notes: z.string().optional(),
});

type FormValues = z.infer<typeof schema>;

type Props = {
  product?: Product;
  onSuccess?: () => void;
};

export function ProductForm({ product, onSuccess }: Props) {
  const router = useRouter();

  const form = useForm<FormValues>({
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    resolver: zodResolver(schema) as any,
    defaultValues: {
      name: product?.name ?? "",
      manufacturer: product?.manufacturer ?? "",
      product_type: (product?.product_type as typeof PRODUCT_TYPES[number]) ?? "fertilizer_synthetic",
      label_rate: product?.label_rate ?? undefined,
      label_rate_unit: (product?.label_rate_unit as typeof UNITS[number]) ?? "lb_per_1000",
      reentry_interval_hours: product?.reentry_interval_hours ?? undefined,
      min_reapplication_days: product?.min_reapplication_days ?? undefined,
      max_annual_rate: product?.max_annual_rate ?? undefined,
      max_annual_rate_unit: (product?.max_annual_rate_unit as typeof UNITS[number]) ?? undefined,
      current_inventory: product?.current_inventory ?? undefined,
      current_inventory_unit: (product?.current_inventory_unit as typeof UNITS[number]) ?? undefined,
      notes: product?.notes ?? "",
    },
  });

  async function onSubmit(values: FormValues) {
    const payload = {
      name: values.name,
      manufacturer: values.manufacturer,
      product_type: values.product_type,
      active_ingredients: product?.active_ingredients ?? null,
      guaranteed_analysis: product?.guaranteed_analysis ?? null,
      label_rate: values.label_rate,
      label_rate_unit: values.label_rate_unit,
      reentry_interval_hours: values.reentry_interval_hours ?? null,
      min_reapplication_days: values.min_reapplication_days ?? null,
      max_annual_rate: values.max_annual_rate ?? null,
      max_annual_rate_unit: values.max_annual_rate_unit ?? null,
      current_inventory: values.current_inventory ?? null,
      current_inventory_unit: values.current_inventory_unit ?? null,
      notes: values.notes || null,
    };

    const result = product
      ? await updateProduct(product.id, payload)
      : await addProduct(payload);

    if (!result.ok) {
      toast.error(result.error);
      return;
    }

    toast.success(product ? "Product updated." : "Product added.");
    onSuccess?.();
    if (!product) {
      router.push("/products");
    } else {
      router.refresh();
    }
  }

  return (
    <Form {...form}>
      <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
        <div className="grid gap-4 sm:grid-cols-2">
          <FormField control={form.control} name="name" render={({ field }) => (
            <FormItem>
              <FormLabel>Product name</FormLabel>
              <FormControl><Input {...field} /></FormControl>
              <FormMessage />
            </FormItem>
          )} />
          <FormField control={form.control} name="manufacturer" render={({ field }) => (
            <FormItem>
              <FormLabel>Manufacturer</FormLabel>
              <FormControl><Input {...field} /></FormControl>
              <FormMessage />
            </FormItem>
          )} />
          <FormField control={form.control} name="product_type" render={({ field }) => (
            <FormItem>
              <FormLabel>Type</FormLabel>
              <Select onValueChange={field.onChange} defaultValue={field.value}>
                <FormControl><SelectTrigger><SelectValue /></SelectTrigger></FormControl>
                <SelectContent>
                  {PRODUCT_TYPES.map((t) => <SelectItem key={t} value={t}>{t.replace(/_/g, " ")}</SelectItem>)}
                </SelectContent>
              </Select>
              <FormMessage />
            </FormItem>
          )} />
          <div className="flex gap-2">
            <FormField control={form.control} name="label_rate" render={({ field }) => (
              <FormItem className="flex-1">
                <FormLabel>Label rate</FormLabel>
                <FormControl><Input type="number" step="0.01" {...field} /></FormControl>
                <FormMessage />
              </FormItem>
            )} />
            <FormField control={form.control} name="label_rate_unit" render={({ field }) => (
              <FormItem className="w-44">
                <FormLabel>Unit</FormLabel>
                <Select value={field.value} onValueChange={field.onChange}>
                  <FormControl>
                    <SelectTrigger>
                      <SelectValue>{rateUnitLabel(field.value)}</SelectValue>
                    </SelectTrigger>
                  </FormControl>
                  <SelectContent>
                    {UNITS.map((u) => <SelectItem key={u} value={u}>{rateUnitLabel(u)}</SelectItem>)}
                  </SelectContent>
                </Select>
                <FormMessage />
              </FormItem>
            )} />
          </div>
          <FormField control={form.control} name="reentry_interval_hours" render={({ field }) => (
            <FormItem>
              <FormLabel>Re-entry interval (hrs)</FormLabel>
              <FormControl><Input type="number" placeholder="optional" {...field} /></FormControl>
              <FormMessage />
            </FormItem>
          )} />
          <FormField control={form.control} name="min_reapplication_days" render={({ field }) => (
            <FormItem>
              <FormLabel>Min reapplication (days)</FormLabel>
              <FormControl><Input type="number" placeholder="optional" {...field} /></FormControl>
              <FormMessage />
            </FormItem>
          )} />
          <div className="flex gap-2">
            <FormField control={form.control} name="max_annual_rate" render={({ field }) => (
              <FormItem className="flex-1">
                <FormLabel>Max annual rate</FormLabel>
                <FormControl><Input type="number" step="0.01" placeholder="optional" {...field} /></FormControl>
                <FormMessage />
              </FormItem>
            )} />
            <FormField control={form.control} name="max_annual_rate_unit" render={({ field }) => (
              <FormItem className="w-44">
                <FormLabel>Unit</FormLabel>
                <Select value={field.value ?? ""} onValueChange={field.onChange}>
                  <FormControl>
                    <SelectTrigger>
                      <SelectValue placeholder="–">
                        {field.value ? rateUnitLabel(field.value) : "–"}
                      </SelectValue>
                    </SelectTrigger>
                  </FormControl>
                  <SelectContent>
                    {UNITS.map((u) => <SelectItem key={u} value={u}>{rateUnitLabel(u)}</SelectItem>)}
                  </SelectContent>
                </Select>
                <FormMessage />
              </FormItem>
            )} />
          </div>
          <div className="flex gap-2">
            <FormField control={form.control} name="current_inventory" render={({ field }) => (
              <FormItem className="flex-1">
                <FormLabel>Current inventory</FormLabel>
                <FormControl><Input type="number" step="0.01" placeholder="optional" {...field} /></FormControl>
                <FormMessage />
              </FormItem>
            )} />
            <FormField control={form.control} name="current_inventory_unit" render={({ field }) => (
              <FormItem className="w-44">
                <FormLabel>Unit</FormLabel>
                <Select value={field.value ?? ""} onValueChange={field.onChange}>
                  <FormControl>
                    <SelectTrigger>
                      <SelectValue placeholder="–">
                        {field.value ? rateUnitLabel(field.value) : "–"}
                      </SelectValue>
                    </SelectTrigger>
                  </FormControl>
                  <SelectContent>
                    {UNITS.map((u) => <SelectItem key={u} value={u}>{rateUnitLabel(u)}</SelectItem>)}
                  </SelectContent>
                </Select>
                <FormMessage />
              </FormItem>
            )} />
          </div>
        </div>
        <FormField control={form.control} name="notes" render={({ field }) => (
          <FormItem>
            <FormLabel>Notes</FormLabel>
            <FormControl><Textarea rows={2} {...field} /></FormControl>
            <FormMessage />
          </FormItem>
        )} />
        <Button type="submit" disabled={form.formState.isSubmitting}>
          {form.formState.isSubmitting ? "Saving…" : product ? "Save changes" : "Add product"}
        </Button>
      </form>
    </Form>
  );
}
