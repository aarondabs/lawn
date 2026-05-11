"use client";

import { useFieldArray, useForm, type Resolver } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { useRouter } from "next/navigation";
import { toast } from "sonner";
import { Plus, X } from "lucide-react";

import { addTreatment, updateTreatment } from "@/app/actions/treatment";
import { Button } from "@/components/ui/button";
import { Form, FormControl, FormField, FormItem, FormLabel, FormMessage } from "@/components/ui/form";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import type { Equipment, Product, Treatment } from "@/lib/api";
import { toLocalDatetimeInputValue } from "@/lib/datetime";

const RATE_UNITS = [
  "lb_per_1000",
  "oz_per_1000",
  "fl_oz_per_1000",
  "gal_per_1000",
  "fl_oz_per_gal",
  "pct_vv",
  "lb_per_acre",
] as const;

const PER_AREA_RATE_UNITS = [
  "lb_per_1000",
  "oz_per_1000",
  "fl_oz_per_1000",
  "gal_per_1000",
  "lb_per_acre",
] as const;

const APPLICATORS = ["self", "spouse", "lawn_service", "other"] as const;
const NO_EQUIPMENT_VALUE = "__none__";

type RateUnit = (typeof RATE_UNITS)[number];
const PER_AREA_RATE_UNITS_SET = new Set<string>(PER_AREA_RATE_UNITS);

const tankMixProductSchema = z.object({
  product_id: z.string().uuid("Select a product"),
  rate_applied: z.coerce.number().positive("Rate must be positive"),
  rate_unit: z.enum(RATE_UNITS),
  position: z.coerce.number().int().nullable().optional(),
  notes: z.string().optional(),
});

const schema = z
  .object({
    applied_at: z.string().min(1),
    products: z.array(tankMixProductSchema).min(1, "At least one product is required"),
    area_treated_sqft: z.coerce.number().int().positive(),
    equipment_id: z.string().optional(),
    applicator: z.enum(APPLICATORS),
    weather_temp_f: z.coerce.number().optional(),
    weather_wind_mph: z.coerce.number().nonnegative().optional(),
    weather_conditions: z.string().optional(),
    target: z.string().optional(),
    notes: z.string().optional(),
  })
  .refine(
    (data) => data.products.some((p) => PER_AREA_RATE_UNITS_SET.has(p.rate_unit)),
    { message: "At least one product must use a per-area rate unit", path: ["products"] },
  );

type FormValues = z.infer<typeof schema>;

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
    resolver: zodResolver(schema) as Resolver<FormValues>,
    defaultValues: {
      applied_at: treatment
        ? toLocalDatetimeInputValue(treatment.applied_at)
        : toLocalDatetimeInputValue(new Date()),
      products:
        treatment?.products && treatment.products.length > 0
          ? treatment.products
              .slice()
              .sort((a, b) => (a.position ?? 0) - (b.position ?? 0))
              .map((p, idx) => ({
                product_id: p.product_id,
                rate_applied: p.rate_applied,
                rate_unit: (p.rate_unit as RateUnit) ?? "lb_per_1000",
                position: p.position ?? idx,
                notes: p.notes ?? "",
              }))
          : [
              {
                product_id: "",
                rate_applied: 0,
                rate_unit: "lb_per_1000",
                position: 0,
                notes: "",
              },
            ],
      area_treated_sqft: treatment?.area_treated_sqft ?? defaultSqft ?? undefined,
      equipment_id: treatment?.equipment_id ?? "",
      applicator: (treatment?.applicator as (typeof APPLICATORS)[number]) ?? "self",
      weather_temp_f: treatment?.weather_temp_f ?? undefined,
      weather_wind_mph: treatment?.weather_wind_mph ?? undefined,
      weather_conditions: treatment?.weather_conditions ?? "",
      target: treatment?.target ?? "",
      notes: treatment?.notes ?? "",
    },
  });

  const { fields, append, remove } = useFieldArray({
    control: form.control,
    name: "products",
  });

  const selectedEquipment = equipment.find((e) => e.id === form.watch("equipment_id"));
  const watchedProducts = form.watch("products");
  const lastProductFilled = !!watchedProducts[watchedProducts.length - 1]?.product_id;

  async function onSubmit(values: FormValues) {
    const payload = {
      applied_at: new Date(values.applied_at).toISOString(),
      products: values.products.map((p, idx) => ({
        product_id: p.product_id,
        rate_applied: p.rate_applied,
        rate_unit: p.rate_unit,
        position: p.position ?? idx,
        notes: p.notes?.trim() ? p.notes : null,
      })),
      area_treated_sqft: values.area_treated_sqft,
      equipment_id: values.equipment_id || null,
      applicator: values.applicator,
      weather_temp_f: values.weather_temp_f ?? null,
      weather_wind_mph: values.weather_wind_mph ?? null,
      weather_conditions: values.weather_conditions?.trim() ? values.weather_conditions : null,
      target: values.target?.trim() ? values.target : null,
      notes: values.notes?.trim() ? values.notes : null,
    };

    const result = treatment ? await updateTreatment(treatment.id, payload) : await addTreatment(payload);

    if (!result.ok) {
      toast.error(result.error);
      return;
    }

    toast.success(treatment ? "Treatment updated." : "Treatment logged.");
    onSuccess?.();

    if (!treatment) {
      router.push("/treatments");
      return;
    }

    router.refresh();
  }

  return (
    <Form {...form}>
      <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-6">
        <div className="grid gap-4 sm:grid-cols-2">
          <FormField
            control={form.control}
            name="applied_at"
            render={({ field }) => (
              <FormItem>
                <FormLabel>Applied at</FormLabel>
                <FormControl>
                  <Input type="datetime-local" {...field} />
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />

          <FormField
            control={form.control}
            name="area_treated_sqft"
            render={({ field }) => (
              <FormItem>
                <FormLabel>Area treated (sq ft)</FormLabel>
                <FormControl>
                  <Input type="number" {...field} />
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />

          <FormField
            control={form.control}
            name="equipment_id"
            render={({ field }) => (
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
            )}
          />

          <FormField
            control={form.control}
            name="applicator"
            render={({ field }) => (
              <FormItem>
                <FormLabel>Applicator</FormLabel>
                <Select onValueChange={field.onChange} value={field.value}>
                  <FormControl>
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                  </FormControl>
                  <SelectContent>
                    {APPLICATORS.map((a) => (
                      <SelectItem key={a} value={a}>
                        {a}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                <FormMessage />
              </FormItem>
            )}
          />

          <FormField
            control={form.control}
            name="target"
            render={({ field }) => (
              <FormItem>
                <FormLabel>Target (what for?)</FormLabel>
                <FormControl>
                  <Input placeholder="e.g. broadleaf weeds" {...field} />
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />

          <FormField
            control={form.control}
            name="weather_temp_f"
            render={({ field }) => (
              <FormItem>
                <FormLabel>Temp (F)</FormLabel>
                <FormControl>
                  <Input type="number" placeholder="optional" {...field} />
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />

          <FormField
            control={form.control}
            name="weather_wind_mph"
            render={({ field }) => (
              <FormItem>
                <FormLabel>Wind (mph)</FormLabel>
                <FormControl>
                  <Input type="number" placeholder="optional" {...field} />
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />

          <FormField
            control={form.control}
            name="weather_conditions"
            render={({ field }) => (
              <FormItem>
                <FormLabel>Weather conditions</FormLabel>
                <FormControl>
                  <Input placeholder="optional" {...field} />
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />
        </div>

        <div className="border-t pt-6">
          <div className="mb-4">
            <h3 className="text-lg font-semibold">Products in tank mix</h3>
            <p className="text-sm text-muted-foreground">Add one or more products for the same treatment.</p>
          </div>

          {fields.map((field, index) => (
            <div key={field.id} className="mb-4 rounded-lg border bg-muted/40 p-4">
              <div className="grid gap-4 sm:grid-cols-4">
                <FormField
                  control={form.control}
                  name={`products.${index}.product_id`}
                  render={({ field: productField }) => (
                    <FormItem className="sm:col-span-2">
                      <FormLabel>Product</FormLabel>
                      <Select value={productField.value} onValueChange={productField.onChange}>
                        <FormControl>
                          <SelectTrigger>
                            <SelectValue placeholder="Select product">
                              {products.find((p) => p.id === productField.value)?.name ?? "Select product"}
                            </SelectValue>
                          </SelectTrigger>
                        </FormControl>
                        <SelectContent className="max-h-[300px]">
                          {products.map((p) => (
                            <SelectItem key={p.id} value={p.id} className="max-w-[32rem] truncate">
                              {p.name}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                      <FormMessage />
                    </FormItem>
                  )}
                />

                <FormField
                  control={form.control}
                  name={`products.${index}.rate_applied`}
                  render={({ field: rateField }) => (
                    <FormItem>
                      <FormLabel>Rate</FormLabel>
                      <FormControl>
                        <Input type="number" step="0.01" {...rateField} />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />

                <FormField
                  control={form.control}
                  name={`products.${index}.rate_unit`}
                  render={({ field: unitField }) => (
                    <FormItem>
                      <FormLabel>Unit</FormLabel>
                      <Select onValueChange={unitField.onChange} value={unitField.value}>
                        <FormControl>
                          <SelectTrigger>
                            <SelectValue />
                          </SelectTrigger>
                        </FormControl>
                        <SelectContent>
                          {RATE_UNITS.map((u) => (
                            <SelectItem key={u} value={u}>
                              {u}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                      <FormMessage />
                    </FormItem>
                  )}
                />
              </div>

              <div className="mt-3 flex items-center justify-between gap-4">
                <FormField
                  control={form.control}
                  name={`products.${index}.notes`}
                  render={({ field: notesField }) => (
                    <FormItem className="flex-1">
                      <FormLabel>Product notes (optional)</FormLabel>
                      <FormControl>
                        <Input placeholder="e.g. order in mix" {...notesField} />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />

                <Button
                  type="button"
                  variant="ghost"
                  size="icon"
                  onClick={() => remove(index)}
                  disabled={fields.length <= 1}
                  aria-label="Remove product"
                >
                  <X className="h-4 w-4" />
                </Button>
              </div>
            </div>
          ))}

          {lastProductFilled && (
            <Button
              type="button"
              variant="outline"
              className="w-full sm:w-auto"
              onClick={() =>
                append({
                  product_id: "",
                  rate_applied: 0,
                  rate_unit: "lb_per_1000",
                  position: fields.length,
                  notes: "",
                })
              }
            >
              <Plus className="mr-2 h-4 w-4" />
              Add another product
            </Button>
          )}

          {form.formState.errors.products?.message ? (
            <p className="text-sm font-medium text-destructive">{form.formState.errors.products.message}</p>
          ) : null}
        </div>

        <FormField
          control={form.control}
          name="notes"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Treatment notes</FormLabel>
              <FormControl>
                <Textarea rows={2} placeholder="optional" {...field} />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />

        <Button type="submit" disabled={form.formState.isSubmitting} className="w-full sm:w-auto">
          {form.formState.isSubmitting ? "Saving..." : treatment ? "Save changes" : "Log treatment"}
        </Button>
      </form>
    </Form>
  );
}
