"use client";

import { useFieldArray, useForm, type Resolver } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { useRouter } from "next/navigation";
import { toast } from "sonner";

import { addTreatment, updateTreatment } from "@/app/actions/treatment";
import { Button } from "@/components/ui/button";
import { Form, FormControl, FormField, FormItem, FormLabel, FormMessage } from "@/components/ui/form";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import type { Equipment, Product, Treatment } from "@/lib/api";
import { toLocalDatetimeInputValue } from "@/lib/datetime";
import { showGuardrailFindings } from "@/lib/guardrails";
import {
  AMOUNT_UNITS,
  APPLICATION_METHODS,
  APPLICATION_METHOD_LABELS,
  CALIBRATED_RATE_UNITS,
  MIX_VOLUME_UNITS,
  PER_AREA_RATE_UNITS,
  RATE_UNITS,
  type RateUnit,
  rateUnitLabel,
  readSprayerCalibration,
} from "@/lib/enums";
import { TankFillsField } from "@/components/forms/tank-fills-field";

const APPLICATORS = ["self", "spouse", "lawn_service", "other"] as const;
const NO_EQUIPMENT_VALUE = "__none__";

const PER_AREA_RATE_UNITS_SET = new Set<string>(PER_AREA_RATE_UNITS);

const granularProductSchema = z.object({
  product_id: z.string().uuid("Select a product"),
  rate_applied: z.coerce.number().positive("Rate must be positive"),
  rate_unit: z.enum(RATE_UNITS),
  position: z.coerce.number().int().nullable().optional(),
  notes: z.string().optional(),
});

const fillProductSchema = z.object({
  product_id: z.string().uuid("Select a product"),
  amount_used: z.coerce.number().positive("Amount must be positive"),
  amount_used_unit: z.enum(AMOUNT_UNITS),
  notes: z.string().optional(),
});

const tankFillSchema = z.object({
  total_mix_volume: z.coerce.number().positive("Tank volume must be positive"),
  total_mix_volume_unit: z.enum(MIX_VOLUME_UNITS),
  calibrated_rate_snapshot: z.coerce.number().positive("Sprayer rate must be positive"),
  calibrated_rate_unit_snapshot: z.enum(CALIBRATED_RATE_UNITS),
  products: z.array(fillProductSchema).min(1, "Each fill needs at least one product"),
  notes: z.string().optional(),
});

const schema = z
  .object({
    applied_at: z.string().min(1),
    application_method: z.enum(APPLICATION_METHODS),
    products: z.array(granularProductSchema),
    fills: z.array(tankFillSchema),
    // Granular only. Liquid derives it from the fills, so it is not required.
    area_treated_sqft: z.coerce.number().int().positive().optional(),
    equipment_id: z.string().optional(),
    applicator: z.enum(APPLICATORS),
    weather_temp_f: z.coerce.number().optional(),
    weather_wind_mph: z.coerce.number().nonnegative().optional(),
    weather_conditions: z.string().optional(),
    target: z.string().optional(),
    notes: z.string().optional(),
  })
  .superRefine((data, ctx) => {
    if (data.application_method === "liquid") {
      if (data.fills.length === 0) {
        ctx.addIssue({ code: "custom", message: "Add at least one tank fill", path: ["fills"] });
      }
      return;
    }

    if (data.products.length === 0) {
      ctx.addIssue({ code: "custom", message: "At least one product is required", path: ["products"] });
      return;
    }
    if (!data.products.some((p) => PER_AREA_RATE_UNITS_SET.has(p.rate_unit))) {
      ctx.addIssue({
        code: "custom",
        message: "At least one product must use a per-area rate unit",
        path: ["products"],
      });
    }
    if (data.area_treated_sqft === undefined) {
      ctx.addIssue({ code: "custom", message: "Area treated is required", path: ["area_treated_sqft"] });
    }
  });

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
      application_method:
        (treatment?.application_method as (typeof APPLICATION_METHODS)[number]) ?? "granular",
      fills:
        treatment?.fills?.map((f) => ({
          total_mix_volume: f.total_mix_volume,
          total_mix_volume_unit: f.total_mix_volume_unit as (typeof MIX_VOLUME_UNITS)[number],
          calibrated_rate_snapshot: f.calibrated_rate_snapshot,
          calibrated_rate_unit_snapshot:
            f.calibrated_rate_unit_snapshot as (typeof CALIBRATED_RATE_UNITS)[number],
          products: f.products.map((fp) => ({
            product_id: fp.product_id,
            amount_used: fp.amount_used,
            amount_used_unit: fp.amount_used_unit as (typeof AMOUNT_UNITS)[number],
            notes: fp.notes ?? "",
          })),
          notes: f.notes ?? "",
        })) ?? [],
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

  // Granular is one product per treatment, but the field array is retained so
  // the existing rendering and validation paths stay unchanged.
  const { fields } = useFieldArray({
    control: form.control,
    name: "products",
  });

  const applicationMethod = form.watch("application_method");
  const isLiquid = applicationMethod === "liquid";

  const selectedEquipment = equipment.find((e) => e.id === form.watch("equipment_id"));
  // Sprayers are the only equipment that can supply a calibrated rate, so the
  // liquid path narrows the picker rather than offering a mower as a choice.
  const equipmentChoices = isLiquid ? equipment.filter((e) => e.type === "sprayer") : equipment;
  const calibration = readSprayerCalibration(selectedEquipment?.calibration);
  const defaultRate = calibration.application_rate ?? 1;
  const defaultRateUnit = calibration.application_rate_unit ?? "gal_per_1000";
  const missingCalibration = isLiquid && !!selectedEquipment && calibration.application_rate === undefined;


  async function onSubmit(values: FormValues) {
    const liquid = values.application_method === "liquid";

    const payload = {
      applied_at: new Date(values.applied_at).toISOString(),
      application_method: values.application_method,
      // Only one branch is sent. The API rejects a liquid payload that carries
      // per-treatment rates or an area, rather than quietly ignoring them.
      products: liquid
        ? []
        : values.products.map((p, idx) => ({
            product_id: p.product_id,
            rate_applied: p.rate_applied,
            rate_unit: p.rate_unit,
            position: p.position ?? idx,
            notes: p.notes?.trim() ? p.notes : null,
          })),
      fills: liquid
        ? values.fills.map((f) => ({
            total_mix_volume: f.total_mix_volume,
            total_mix_volume_unit: f.total_mix_volume_unit,
            calibrated_rate_snapshot: f.calibrated_rate_snapshot,
            calibrated_rate_unit_snapshot: f.calibrated_rate_unit_snapshot,
            products: f.products.map((fp) => ({
              product_id: fp.product_id,
              amount_used: fp.amount_used,
              amount_used_unit: fp.amount_used_unit,
              notes: fp.notes?.trim() ? fp.notes : null,
            })),
            notes: f.notes?.trim() ? f.notes : null,
          }))
        : [],
      area_treated_sqft: liquid ? null : values.area_treated_sqft,
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

    const warnings = result.data?.inventory_warnings ?? [];
    if (warnings.length > 0) {
      // A skipped decrement means recorded stock is now wrong -- say so loudly
      // rather than letting the success toast imply everything reconciled.
      for (const warning of warnings) {
        toast.warning(warning.message, { duration: 10000 });
      }
    } else {
      toast.success(treatment ? "Treatment updated." : "Treatment logged.");
    }
    // Guardrail cautions are advisory: the save already happened, so these
    // inform rather than block.
    showGuardrailFindings(result.data?.guardrail_findings);
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
        <FormField
          control={form.control}
          name="application_method"
          render={({ field }) => (
            <FormItem>
              <FormLabel>How was it applied?</FormLabel>
              <Select value={field.value} onValueChange={field.onChange}>
                <FormControl>
                  <SelectTrigger className="w-full">
                    <SelectValue>
                      {APPLICATION_METHOD_LABELS[field.value as keyof typeof APPLICATION_METHOD_LABELS]}
                    </SelectValue>
                  </SelectTrigger>
                </FormControl>
                <SelectContent>
                  {APPLICATION_METHODS.map((m) => (
                    <SelectItem key={m} value={m}>
                      {APPLICATION_METHOD_LABELS[m]}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <FormMessage />
            </FormItem>
          )}
        />

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

          {!isLiquid && (
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
          )}

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
                    {equipmentChoices.map((e) => (
                      <SelectItem key={e.id} value={e.id} className="max-w-[32rem] truncate">
                        {e.make} {e.model}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                {missingCalibration && (
                  <p className="text-xs text-muted-foreground">
                    No calibration recorded for this sprayer — fills default to 1 gal / 1,000 sq ft.
                    Set the real rate on the equipment record so it prefills correctly.
                  </p>
                )}
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

        {isLiquid && (
          <TankFillsField products={products} defaultRate={defaultRate} defaultRateUnit={defaultRateUnit} />
        )}

        {!isLiquid && (
        <div className="border-t pt-6">
          <div className="mb-4">
            <h3 className="text-lg font-semibold">Product</h3>
            <p className="text-sm text-muted-foreground">
              One product per granular application — a spreader has a single setting, so it can only
              deliver one product at its label rate. Applying two means two treatments.
            </p>
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
                            <SelectValue>{rateUnitLabel(unitField.value)}</SelectValue>
                          </SelectTrigger>
                        </FormControl>
                        <SelectContent>
                          {RATE_UNITS.map((u) => (
                            <SelectItem key={u} value={u}>
                              {rateUnitLabel(u)}
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
                        <Input placeholder="e.g. spreader setting 4.5" {...notesField} />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />

              </div>
            </div>
          ))}

          {form.formState.errors.products?.message ? (
            <p className="text-sm font-medium text-destructive">{form.formState.errors.products.message}</p>
          ) : null}
        </div>
        )}

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
