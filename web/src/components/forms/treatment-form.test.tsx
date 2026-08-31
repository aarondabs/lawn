/**
 * Regression coverage for the liquid-form silent-submit bug (commit 53597f9):
 * the form seeds a hidden empty granular row, and on a liquid treatment that
 * row must never block submit. It did, silently, for weeks — because the only
 * tests hit the API. These drive the real component through submit.
 */
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { TreatmentForm } from "@/components/forms/treatment-form";
import { addTreatment, updateTreatment } from "@/app/actions/treatment";
import { toast } from "sonner";
import type { Product, Treatment } from "@/lib/api";

vi.mock("@/app/actions/treatment", () => ({
  addTreatment: vi.fn(),
  updateTreatment: vi.fn(),
}));

vi.mock("@/lib/guardrails", () => ({
  showGuardrailFindings: vi.fn(),
}));

vi.mock("sonner", () => ({
  toast: { error: vi.fn(), success: vi.fn(), warning: vi.fn() },
}));

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), refresh: vi.fn() }),
}));

const mockedUpdate = vi.mocked(updateTreatment);
const mockedAdd = vi.mocked(addTreatment);

const product: Product = {
  id: "11111111-1111-4111-8111-111111111111",
  name: "3-Way Max",
  manufacturer: "Acme",
  product_type: "herbicide_post_broadleaf",
  active_ingredients: null,
  guaranteed_analysis: null,
  label_rate: 1.5,
  label_rate_unit: "fl_oz_per_1000",
  reentry_interval_hours: null,
  min_reapplication_days: null,
  max_annual_rate: null,
  max_annual_rate_unit: null,
  current_inventory: null,
  current_inventory_unit: null,
  reorder_threshold: null,
  preemergent_blocking_days: null,
  notes: null,
  created_at: "2026-05-01T00:00:00Z",
  updated_at: "2026-05-01T00:00:00Z",
};

const liquidTreatment: Treatment = {
  id: "22222222-2222-4222-8222-222222222222",
  applied_at: "2026-07-28T23:00:00Z",
  application_method: "liquid",
  // Liquid: the granular product list is empty, so the form seeds its hidden
  // default row — the exact condition that used to kill the submit.
  products: [],
  fills: [
    {
      id: "33333333-3333-4333-8333-333333333333",
      fill_number: 1,
      total_mix_volume: 4,
      total_mix_volume_unit: "gal",
      calibrated_rate_snapshot: 0.133,
      calibrated_rate_unit_snapshot: "gal_per_1000",
      area_covered_sqft: 30075,
      products: [
        {
          product_id: product.id,
          amount_used: 6,
          amount_used_unit: "fl_oz",
          notes: null,
          effective_rate_per_1000: 0.2,
        },
      ],
      notes: null,
    },
  ],
  area_treated_sqft: 30075,
  equipment_id: null,
  applicator: "self",
  weather_temp_f: null,
  weather_wind_mph: null,
  weather_conditions: null,
  target: "broadleaf weeds",
  notes: null,
  created_at: "2026-07-28T23:05:00Z",
  updated_at: "2026-07-28T23:05:00Z",
};

beforeEach(() => {
  vi.clearAllMocks();
});

describe("TreatmentForm — liquid submit regression", () => {
  it("submits a liquid treatment despite the hidden empty granular row", async () => {
    mockedUpdate.mockResolvedValue({ ok: true, data: { ...liquidTreatment } });

    const user = userEvent.setup();
    render(
      <TreatmentForm treatment={liquidTreatment} products={[product]} equipment={[]} />,
    );

    await user.click(screen.getByRole("button", { name: "Save changes" }));

    expect(mockedUpdate).toHaveBeenCalledTimes(1);
    const [, payload] = mockedUpdate.mock.calls[0];
    // The liquid branch is sent; the hidden granular row never leaks out.
    expect(payload.products).toEqual([]);
    expect(payload.fills).toHaveLength(1);
    expect(payload.fills?.[0].products[0]).toMatchObject({
      product_id: product.id,
      amount_used: 6,
      amount_used_unit: "fl_oz",
    });
    expect(payload.area_treated_sqft).toBeNull();
    expect(vi.mocked(toast.error)).not.toHaveBeenCalled();
  });

  it("a blocked submit is audible, never a silently dead button", async () => {
    const user = userEvent.setup();
    // Fresh granular form: the seeded empty product row is genuinely invalid here.
    render(<TreatmentForm products={[product]} equipment={[]} defaultSqft={47000} />);

    await user.click(screen.getByRole("button", { name: "Log treatment" }));

    expect(mockedAdd).not.toHaveBeenCalled();
    expect(vi.mocked(toast.error)).toHaveBeenCalledWith(
      "Some fields need attention — check for highlighted errors above.",
    );
  });
});
