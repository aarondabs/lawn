"use client";

import { useFieldArray, useFormContext } from "react-hook-form";
import { Copy, Plus, X } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { FormControl, FormField, FormItem, FormLabel, FormMessage } from "@/components/ui/form";
import {
  AMOUNT_UNITS,
  MIX_VOLUME_UNITS,
  MIX_VOLUME_UNIT_LABELS,
  amountUnitLabel,
  previewAreaCoveredSqft,
  rateUnitLabel,
} from "@/lib/enums";
import type { Product } from "@/lib/api";

type Props = {
  products: Product[];
  /** Calibrated rate from the selected sprayer, used for new fills. */
  defaultRate: number;
  defaultRateUnit: string;
};

const emptyFillProduct = { product_id: "", amount_used: 0, amount_used_unit: "fl_oz" as const, notes: "" };

function formatSqft(value: number) {
  return `${Math.round(value).toLocaleString()} sq ft`;
}

/** Products within a single fill. */
function FillProducts({ fillIndex, products }: { fillIndex: number; products: Product[] }) {
  const form = useFormContext();
  const { fields, append, remove } = useFieldArray({
    control: form.control,
    name: `fills.${fillIndex}.products`,
  });

  const watched = form.watch(`fills.${fillIndex}.products`) ?? [];
  const lastFilled = !!watched[watched.length - 1]?.product_id;

  return (
    <div className="space-y-3">
      {fields.map((field, productIndex) => (
        // items-start, not items-end: bottom-aligning fields of unequal height
        // drops the shorter one's label out of line with its neighbours.
        <div key={field.id} className="grid items-start gap-3 sm:grid-cols-[1fr_6rem_7rem_auto]">
          <FormField
            control={form.control}
            name={`fills.${fillIndex}.products.${productIndex}.product_id`}
            render={({ field: productField }) => (
              <FormItem>
                <FormLabel className="text-xs">Product</FormLabel>
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
            name={`fills.${fillIndex}.products.${productIndex}.amount_used`}
            render={({ field: amountField }) => (
              <FormItem>
                <FormLabel className="text-xs">Amount</FormLabel>
                <FormControl>
                  <Input type="number" step="0.01" inputMode="decimal" {...amountField} />
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />

          <FormField
            control={form.control}
            name={`fills.${fillIndex}.products.${productIndex}.amount_used_unit`}
            render={({ field: unitField }) => (
              <FormItem>
                <FormLabel className="text-xs">Unit</FormLabel>
                <Select value={unitField.value} onValueChange={unitField.onChange}>
                  <FormControl>
                    <SelectTrigger>
                      <SelectValue>{amountUnitLabel(unitField.value)}</SelectValue>
                    </SelectTrigger>
                  </FormControl>
                  <SelectContent>
                    {AMOUNT_UNITS.map((u) => (
                      <SelectItem key={u} value={u}>
                        {amountUnitLabel(u)}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                <FormMessage />
              </FormItem>
            )}
          />

          <Button
            type="button"
            variant="ghost"
            size="icon"
            // Nudged down past the label row so it sits level with the inputs.
            className="mt-6"
            onClick={() => remove(productIndex)}
            disabled={fields.length <= 1}
            aria-label="Remove product from fill"
          >
            <X className="h-4 w-4" />
          </Button>
        </div>
      ))}

      {lastFilled && (
        <Button type="button" variant="ghost" size="sm" onClick={() => append({ ...emptyFillProduct })}>
          <Plus className="mr-1 h-3 w-3" /> Add product to this fill
        </Button>
      )}
    </div>
  );
}

export function TankFillsField({ products, defaultRate, defaultRateUnit }: Props) {
  const form = useFormContext();
  const { fields, append, remove } = useFieldArray({ control: form.control, name: "fills" });
  const watchedFills = form.watch("fills") ?? [];

  const totalArea = watchedFills.reduce((sum: number, fill: Record<string, unknown>) => {
    const area = previewAreaCoveredSqft(
      Number(fill?.total_mix_volume) || 0,
      String(fill?.total_mix_volume_unit ?? "gal"),
      Number(fill?.calibrated_rate_snapshot) || 0,
      String(fill?.calibrated_rate_unit_snapshot ?? "gal_per_1000"),
    );
    return sum + (area ?? 0);
  }, 0);

  function newFill() {
    return {
      total_mix_volume: 0,
      total_mix_volume_unit: "gal",
      calibrated_rate_snapshot: defaultRate,
      calibrated_rate_unit_snapshot: defaultRateUnit,
      products: [{ ...emptyFillProduct }],
      notes: "",
    };
  }

  /** A multi-tank job is usually the same mix twice; copying beats retyping. */
  function duplicateLastFill() {
    const last = watchedFills[watchedFills.length - 1];
    if (!last) return append(newFill());
    append({
      ...last,
      products: (last.products ?? []).map((p: Record<string, unknown>) => ({ ...p })),
    });
  }

  return (
    <div className="border-t pt-6">
      <div className="mb-4">
        <h3 className="text-lg font-semibold">Tank fills</h3>
        <p className="text-sm text-muted-foreground">
          Enter what you mixed. Area is calculated from the tank volume and the sprayer&apos;s rate.
        </p>
      </div>

      {fields.map((field, index) => {
        const fill = watchedFills[index] ?? {};
        const area = previewAreaCoveredSqft(
          Number(fill.total_mix_volume) || 0,
          String(fill.total_mix_volume_unit ?? "gal"),
          Number(fill.calibrated_rate_snapshot) || 0,
          String(fill.calibrated_rate_unit_snapshot ?? "gal_per_1000"),
        );

        return (
          <div key={field.id} className="mb-4 rounded-lg border bg-muted/40 p-4">
            <div className="mb-3 flex items-center justify-between">
              <h4 className="font-medium">Fill {index + 1}</h4>
              <Button
                type="button"
                variant="ghost"
                size="icon"
                onClick={() => remove(index)}
                disabled={fields.length <= 1}
                aria-label="Remove fill"
              >
                <X className="h-4 w-4" />
              </Button>
            </div>

            <div className="grid items-start gap-3 sm:grid-cols-[1fr_5rem_1.6fr_1fr]">
              <FormField
                control={form.control}
                name={`fills.${index}.total_mix_volume`}
                render={({ field: volumeField }) => (
                  <FormItem>
                    <FormLabel className="text-xs">Tank volume</FormLabel>
                    <FormControl>
                      <Input type="number" step="0.1" inputMode="decimal" {...volumeField} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <FormField
                control={form.control}
                name={`fills.${index}.total_mix_volume_unit`}
                render={({ field: unitField }) => (
                  <FormItem>
                    <FormLabel className="text-xs">Unit</FormLabel>
                    <Select value={unitField.value} onValueChange={unitField.onChange}>
                      <FormControl>
                        <SelectTrigger>
                          <SelectValue>
                            {MIX_VOLUME_UNIT_LABELS[unitField.value as keyof typeof MIX_VOLUME_UNIT_LABELS]}
                          </SelectValue>
                        </SelectTrigger>
                      </FormControl>
                      <SelectContent>
                        {MIX_VOLUME_UNITS.map((u) => (
                          <SelectItem key={u} value={u}>
                            {MIX_VOLUME_UNIT_LABELS[u]}
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
                name={`fills.${index}.calibrated_rate_snapshot`}
                render={({ field: rateField }) => (
                  <FormItem>
                    {/* The unit comes from the sprayer's calibration and is
                        snapshotted per fill, so it is shown rather than picked --
                        but a bare "1" tells you nothing without it. */}
                    <FormLabel className="text-xs">
                      Sprayer rate ({rateUnitLabel(
                        String(fill.calibrated_rate_unit_snapshot ?? "gal_per_1000"),
                      )})
                    </FormLabel>
                    <FormControl>
                      <Input type="number" step="0.01" inputMode="decimal" {...rateField} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <FormItem>
                <FormLabel className="text-xs">Covers</FormLabel>
                <p className="flex h-9 items-center text-sm font-medium tabular-nums">
                  {area ? formatSqft(area) : "–"}
                </p>
              </FormItem>
            </div>

            <div className="mt-4">
              <FillProducts fillIndex={index} products={products} />
            </div>

            <FormField
              control={form.control}
              name={`fills.${index}.notes`}
              render={({ field: notesField }) => (
                <FormItem className="mt-3">
                  <FormLabel className="text-xs">Fill notes (optional)</FormLabel>
                  <FormControl>
                    <Input placeholder="e.g. ran 2 oz short" {...notesField} />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
          </div>
        );
      })}

      <div className="flex flex-wrap gap-2">
        <Button type="button" variant="outline" onClick={() => append(newFill())}>
          <Plus className="mr-2 h-4 w-4" /> Add fill
        </Button>
        {fields.length > 0 && (
          <Button type="button" variant="ghost" onClick={duplicateLastFill}>
            <Copy className="mr-2 h-4 w-4" /> Duplicate last fill
          </Button>
        )}
      </div>

      {totalArea > 0 && (
        <p className="mt-4 text-sm text-muted-foreground">
          Total area covered: <span className="font-medium text-foreground">{formatSqft(totalArea)}</span>
          {fields.length > 1 && ` across ${fields.length} fills`}
        </p>
      )}

      {typeof form.formState.errors.fills?.message === "string" && (
        <p className="mt-2 text-sm font-medium text-destructive">{form.formState.errors.fills.message}</p>
      )}
    </div>
  );
}
