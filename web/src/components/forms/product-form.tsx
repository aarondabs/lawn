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
import { AMOUNT_UNITS, RATE_UNITS, amountUnitLabel, rateUnitLabel } from "@/lib/enums";
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
  current_inventory_unit: z.enum(AMOUNT_UNITS).optional(),
  reorder_threshold: z.coerce.number().nonnegative().optional(),
  preemergent_blocking_days: z.coerce.number().int().positive().optional(),
  // Guaranteed analysis, flattened for the form and reassembled on submit.
  total_nitrogen_pct: z.coerce.number().min(0).max(100).optional(),
  phosphorus_pct: z.coerce.number().min(0).max(100).optional(),
  potassium_pct: z.coerce.number().min(0).max(100).optional(),
  lbs_n_per_gallon: z.coerce.number().positive().optional(),
  notes: z.string().optional(),
});

const FERTILIZER_TYPES = new Set(["fertilizer_synthetic", "fertilizer_organic"]);

/** Read the typed analysis fields out of the stored blob. */
function readAnalysis(analysis: Record<string, unknown> | null | undefined) {
  const num = (v: unknown) => (typeof v === "number" ? v : undefined);
  return {
    total_nitrogen_pct: num(analysis?.total_nitrogen_pct),
    phosphorus_pct: num(analysis?.phosphorus_pct),
    potassium_pct: num(analysis?.potassium_pct),
    lbs_n_per_gallon: num(analysis?.lbs_n_per_gallon),
  };
}

/** Fold the form's analysis fields back in, preserving any other label detail. */
function buildAnalysis(
  values: FormValues,
  existing: Record<string, unknown> | null | undefined,
): Record<string, unknown> | null {
  const analysis: Record<string, unknown> = { ...(existing ?? {}) };
  for (const key of ["total_nitrogen_pct", "phosphorus_pct", "potassium_pct", "lbs_n_per_gallon"]) {
    delete analysis[key];
  }
  if (values.total_nitrogen_pct !== undefined) analysis.total_nitrogen_pct = values.total_nitrogen_pct;
  if (values.phosphorus_pct !== undefined) analysis.phosphorus_pct = values.phosphorus_pct;
  if (values.potassium_pct !== undefined) analysis.potassium_pct = values.potassium_pct;
  if (values.lbs_n_per_gallon !== undefined) analysis.lbs_n_per_gallon = values.lbs_n_per_gallon;
  return Object.keys(analysis).length > 0 ? analysis : null;
}

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
      current_inventory_unit: (product?.current_inventory_unit as typeof AMOUNT_UNITS[number]) ?? undefined,
      reorder_threshold: product?.reorder_threshold ?? undefined,
      preemergent_blocking_days: product?.preemergent_blocking_days ?? undefined,
      ...readAnalysis(product?.guaranteed_analysis),
      notes: product?.notes ?? "",
    },
  });

  const productType = form.watch("product_type");
  const isFertilizer = FERTILIZER_TYPES.has(productType);
  const isPreEmergent = productType === "herbicide_pre";

  async function onSubmit(values: FormValues) {
    const payload = {
      name: values.name,
      manufacturer: values.manufacturer,
      product_type: values.product_type,
      active_ingredients: product?.active_ingredients ?? null,
      guaranteed_analysis: buildAnalysis(values, product?.guaranteed_analysis),
      label_rate: values.label_rate,
      label_rate_unit: values.label_rate_unit,
      reentry_interval_hours: values.reentry_interval_hours ?? null,
      min_reapplication_days: values.min_reapplication_days ?? null,
      max_annual_rate: values.max_annual_rate ?? null,
      max_annual_rate_unit: values.max_annual_rate_unit ?? null,
      current_inventory: values.current_inventory ?? null,
      current_inventory_unit: values.current_inventory_unit ?? null,
      reorder_threshold: values.reorder_threshold ?? null,
      preemergent_blocking_days: values.preemergent_blocking_days ?? null,
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
          <div className="flex items-start gap-2">
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
          <div className="flex items-start gap-2">
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
          {/* items-start plus non-wrapping labels: a label that wraps to two lines
              pushes its own input down out of line with its neighbours. */}
          <div className="flex items-start gap-2">
            <FormField control={form.control} name="current_inventory" render={({ field }) => (
              <FormItem className="flex-1">
                <FormLabel className="whitespace-nowrap">In stock</FormLabel>
                <FormControl><Input type="number" step="0.01" placeholder="optional" {...field} /></FormControl>
                <FormMessage />
              </FormItem>
            )} />
            <FormField control={form.control} name="current_inventory_unit" render={({ field }) => (
              <FormItem className="w-32">
                <FormLabel className="whitespace-nowrap">Unit</FormLabel>
                <Select value={field.value ?? ""} onValueChange={field.onChange}>
                  <FormControl>
                    <SelectTrigger>
                      <SelectValue placeholder="–">
                        {field.value ? amountUnitLabel(field.value) : "–"}
                      </SelectValue>
                    </SelectTrigger>
                  </FormControl>
                  <SelectContent>
                    {AMOUNT_UNITS.map((u) => (
                      <SelectItem key={u} value={u}>{amountUnitLabel(u)}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                <FormMessage />
              </FormItem>
            )} />
            <FormField control={form.control} name="reorder_threshold" render={({ field }) => (
              <FormItem className="flex-1">
                <FormLabel className="whitespace-nowrap">Reorder at</FormLabel>
                <FormControl>
                  <Input type="number" step="0.01" placeholder="optional" {...field} />
                </FormControl>
                <FormMessage />
              </FormItem>
            )} />
          </div>
          <p className="-mt-2 text-xs text-muted-foreground">
            Stock and reorder point share the unit above. Match the family to how you apply it — a
            liquid poured in fluid ounces needs a volume unit, or the decrement can&apos;t reconcile.
          </p>

          {isFertilizer && (
            <div className="rounded-lg border bg-muted/40 p-4">
              <div className="mb-3">
                <h3 className="font-medium">Guaranteed analysis</h3>
                <p className="text-xs text-muted-foreground">
                  From the label. The nitrogen guardrail needs this — without it, it reports
                  &quot;cannot evaluate&quot; rather than assuming zero.
                </p>
              </div>
              <div className="grid gap-4 sm:grid-cols-3">
                <FormField control={form.control} name="total_nitrogen_pct" render={({ field }) => (
                  <FormItem>
                    <FormLabel>N %</FormLabel>
                    <FormControl>
                      <Input type="number" step="0.1" placeholder="e.g. 32" {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )} />
                <FormField control={form.control} name="phosphorus_pct" render={({ field }) => (
                  <FormItem>
                    <FormLabel>P %</FormLabel>
                    <FormControl>
                      <Input type="number" step="0.1" placeholder="e.g. 0" {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )} />
                <FormField control={form.control} name="potassium_pct" render={({ field }) => (
                  <FormItem>
                    <FormLabel>K %</FormLabel>
                    <FormControl>
                      <Input type="number" step="0.1" placeholder="e.g. 4" {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )} />
              </div>
              <FormField control={form.control} name="lbs_n_per_gallon" render={({ field }) => (
                <FormItem className="mt-4">
                  <FormLabel>lbs N per gallon (liquids only)</FormLabel>
                  <FormControl>
                    <Input type="number" step="0.01" placeholder="e.g. 2.97" {...field} />
                  </FormControl>
                  <p className="text-xs text-muted-foreground">
                    Required for liquid fertilizers. Amounts are measured by volume but the analysis
                    is by weight, and converting between them needs density — which is never guessed.
                    Liquid labels print this number directly.
                  </p>
                  <FormMessage />
                </FormItem>
              )} />
            </div>
          )}

          {isPreEmergent && (
            <FormField control={form.control} name="preemergent_blocking_days" render={({ field }) => (
              <FormItem>
                <FormLabel>Germination blocking window (days)</FormLabel>
                <FormControl>
                  <Input type="number" placeholder="from the label" {...field} />
                </FormControl>
                <p className="text-xs text-muted-foreground">
                  How long this pre-emergent blocks seed germination. Used to warn when an overseed
                  falls inside the window. Left blank, a conservative default is assumed and flagged.
                </p>
                <FormMessage />
              </FormItem>
            )} />
          )}
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
