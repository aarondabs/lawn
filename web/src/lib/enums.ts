// Display labels for enum-like values. The values themselves mirror
// api/src/lawn_api/models/constants.py -- keep the two in lockstep.

export const RATE_UNITS = [
  "lb_per_1000",
  "oz_per_1000",
  "fl_oz_per_1000",
  "gal_per_1000",
  "fl_oz_per_gal",
  "pct_vv",
  "lb_per_acre",
] as const;

export type RateUnit = (typeof RATE_UNITS)[number];

/** Rate units that are not per-area. Mirrors NON_AREA_RATE_UNITS in constants.py. */
export const NON_AREA_RATE_UNITS = ["fl_oz_per_gal", "pct_vv"] as const;

export const PER_AREA_RATE_UNITS = RATE_UNITS.filter(
  (u) => !(NON_AREA_RATE_UNITS as readonly string[]).includes(u),
);

export const RATE_UNIT_LABELS: Record<RateUnit, string> = {
  lb_per_1000: "lb / 1,000 sq ft",
  oz_per_1000: "oz / 1,000 sq ft",
  fl_oz_per_1000: "fl oz / 1,000 sq ft",
  gal_per_1000: "gal / 1,000 sq ft",
  fl_oz_per_gal: "fl oz / gal of mix",
  pct_vv: "% by volume",
  lb_per_acre: "lb / acre",
};

/** Human-readable label for a stored rate unit, falling back to the raw value. */
export function rateUnitLabel(unit: string): string {
  return RATE_UNIT_LABELS[unit as RateUnit] ?? unit;
}

export const MOW_ORIENTATIONS = [
  "north_south",
  "east_west",
  "diagonal_ne_sw",
  "diagonal_nw_se",
  "other",
] as const;

export type MowOrientation = (typeof MOW_ORIENTATIONS)[number];

export const MOW_ORIENTATION_LABELS: Record<MowOrientation, string> = {
  north_south: "North ↔ South",
  east_west: "East ↔ West",
  diagonal_ne_sw: "Diagonal (NE ↔ SW)",
  diagonal_nw_se: "Diagonal (NW ↔ SE)",
  other: "Other",
};

export type MowDetails = {
  cut_height_inches?: number;
  mow_orientation?: MowOrientation;
  mow_orientation_other?: string;
};

/** Read the structured mow fields out of a cultural_practice.details blob. */
export function readMowDetails(details: Record<string, unknown> | null | undefined): MowDetails {
  if (!details) return {};
  const height = details.cut_height_inches;
  const orientation = details.mow_orientation;
  const orientationOther = details.mow_orientation_other;
  return {
    cut_height_inches: typeof height === "number" ? height : undefined,
    mow_orientation:
      typeof orientation === "string" && (MOW_ORIENTATIONS as readonly string[]).includes(orientation)
        ? (orientation as MowOrientation)
        : undefined,
    mow_orientation_other: typeof orientationOther === "string" ? orientationOther : undefined,
  };
}

/**
 * Height to prefill a new mow with: the most recent logged mow height, falling
 * back to the profile target when there is no prior mow to learn from.
 */
export function defaultCutHeight(
  practices: { practice_type: string; performed_at: string; details: Record<string, unknown> | null }[],
  targetMowHeightInches?: number | null,
): number | undefined {
  const lastMow = practices
    .filter((p) => p.practice_type === "mow" && readMowDetails(p.details).cut_height_inches !== undefined)
    .sort((a, b) => b.performed_at.localeCompare(a.performed_at))[0];
  return readMowDetails(lastMow?.details).cut_height_inches ?? targetMowHeightInches ?? undefined;
}

/** One-line summary of a mow for list/detail views, e.g. `4" · East ↔ West`. */
export function formatMowSummary(details: Record<string, unknown> | null | undefined): string | null {
  const { cut_height_inches, mow_orientation, mow_orientation_other } = readMowDetails(details);
  const parts: string[] = [];
  if (cut_height_inches !== undefined) parts.push(`${cut_height_inches}"`);
  if (mow_orientation) {
    parts.push(
      mow_orientation === "other" && mow_orientation_other
        ? mow_orientation_other
        : MOW_ORIENTATION_LABELS[mow_orientation],
    );
  }
  return parts.length > 0 ? parts.join(" · ") : null;
}
