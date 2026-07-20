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

// ─── Application method ───────────────────────────────────────────────────────

export const APPLICATION_METHODS = ["granular", "liquid", "other"] as const;
export type ApplicationMethod = (typeof APPLICATION_METHODS)[number];

export const APPLICATION_METHOD_LABELS: Record<ApplicationMethod, string> = {
  granular: "Granular (spreader)",
  liquid: "Liquid (sprayer)",
  other: "Other",
};

// ─── Amount units ─────────────────────────────────────────────────────────────
// A quantity of product, as opposed to a rate. Mirrors AMOUNT_UNITS in
// constants.py; conversions live server-side in services/units.py.

export const AMOUNT_UNITS = ["fl_oz", "pt", "qt", "gal", "oz", "lb"] as const;
export type AmountUnit = (typeof AMOUNT_UNITS)[number];

export const AMOUNT_UNIT_LABELS: Record<AmountUnit, string> = {
  fl_oz: "fl oz",
  pt: "pt",
  qt: "qt",
  gal: "gal",
  oz: "oz",
  lb: "lb",
};

export function amountUnitLabel(unit: string): string {
  return AMOUNT_UNIT_LABELS[unit as AmountUnit] ?? unit;
}

/** Volume units, offered first for liquid products. */
export const VOLUME_AMOUNT_UNITS = ["fl_oz", "pt", "qt", "gal"] as const;

export const MIX_VOLUME_UNITS = ["gal", "l"] as const;
export type MixVolumeUnit = (typeof MIX_VOLUME_UNITS)[number];

export const MIX_VOLUME_UNIT_LABELS: Record<MixVolumeUnit, string> = {
  gal: "gal",
  l: "L",
};

export const CALIBRATED_RATE_UNITS = ["gal_per_1000", "fl_oz_per_1000"] as const;
export type CalibratedRateUnit = (typeof CALIBRATED_RATE_UNITS)[number];

/** Sprayer calibration as stored in equipment.calibration. */
export type SprayerCalibration = {
  application_rate?: number;
  application_rate_unit?: CalibratedRateUnit;
  nozzle_count?: number;
  pressure_psi?: number;
};

export function readSprayerCalibration(
  calibration: Record<string, unknown> | null | undefined,
): SprayerCalibration {
  if (!calibration) return {};
  const rate = calibration.application_rate;
  const unit = calibration.application_rate_unit;
  const nozzles = calibration.nozzle_count;
  const psi = calibration.pressure_psi;
  return {
    application_rate: typeof rate === "number" ? rate : undefined,
    application_rate_unit:
      typeof unit === "string" && (CALIBRATED_RATE_UNITS as readonly string[]).includes(unit)
        ? (unit as CalibratedRateUnit)
        : undefined,
    nozzle_count: typeof nozzles === "number" ? nozzles : undefined,
    pressure_psi: typeof psi === "number" ? psi : undefined,
  };
}

/**
 * Area a tank fill covers, mirroring services/units.area_covered_sqft so the
 * form can show the number before the server confirms it. The server value is
 * authoritative; this is for immediate feedback while typing.
 */
export function previewAreaCoveredSqft(
  mixVolume: number,
  mixVolumeUnit: string,
  calibratedRate: number,
  calibratedRateUnit: string,
): number | null {
  if (!(mixVolume > 0) || !(calibratedRate > 0)) return null;
  const volumeGal = mixVolumeUnit === "l" ? mixVolume * 0.264172 : mixVolume;
  const rateGalPer1000 = calibratedRateUnit === "fl_oz_per_1000" ? calibratedRate / 128 : calibratedRate;
  return (volumeGal / rateGalPer1000) * 1000;
}

/**
 * Amount of product a granular application consumed, mirroring
 * services/inventory._granular_amount. Returns null for rate units that are not
 * area-based, which have no meaning without a mix volume.
 */
export function granularAmountUsed(
  rateApplied: number,
  rateUnit: string,
  areaSqft: number,
): { amount: number; unit: AmountUnit } | null {
  const perThousand: Record<string, AmountUnit> = {
    lb_per_1000: "lb",
    oz_per_1000: "oz",
    fl_oz_per_1000: "fl_oz",
    gal_per_1000: "gal",
  };
  if (rateUnit in perThousand) {
    return { amount: (rateApplied * areaSqft) / 1000, unit: perThousand[rateUnit] };
  }
  if (rateUnit === "lb_per_acre") {
    return { amount: (rateApplied * areaSqft) / 43560, unit: "lb" };
  }
  return null;
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
