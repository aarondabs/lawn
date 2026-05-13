const DEFAULT_API_BASE_URL = "http://lawn-api:8000";

export type ApiMethod = "GET" | "POST" | "PATCH" | "PUT" | "DELETE";

export class ApiError extends Error {
  readonly status: number;
  readonly payload: unknown;

  constructor(message: string, status: number, payload: unknown) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.payload = payload;
  }
}

function getApiBaseUrl() {
  return process.env.NEXT_PUBLIC_API_BASE_URL?.replace(/\/$/, "") ?? DEFAULT_API_BASE_URL;
}

type RequestOptions<TBody> = {
  method?: ApiMethod;
  body?: TBody;
  headers?: HeadersInit;
  cache?: RequestCache;
  next?: NextFetchRequestConfig;
};

export async function apiRequest<TResponse, TBody = unknown>(
  path: string,
  options: RequestOptions<TBody> = {},
): Promise<TResponse> {
  const { method = "GET", body, headers, cache = "no-store", next } = options;

  const response = await fetch(`${getApiBaseUrl()}${path}`, {
    method,
    headers: {
      "Content-Type": "application/json",
      ...headers,
    },
    body: body === undefined ? undefined : JSON.stringify(body),
    cache,
    next,
  });

  if (response.status === 204) {
    if (!response.ok) {
      throw new ApiError(`API request failed: ${method} ${path}`, response.status, "");
    }
    return undefined as TResponse;
  }

  const contentType = response.headers.get("content-type") ?? "";
  const isJson = contentType.includes("application/json");
  const payload = isJson ? await response.json() : await response.text();

  if (!response.ok) {
    throw new ApiError(`API request failed: ${method} ${path}`, response.status, payload);
  }

  return payload as TResponse;
}

export async function getHealth() {
  return apiRequest<{ status: string; db?: string }>("/health", { method: "GET" });
}

// ─── Types ────────────────────────────────────────────────────────────────────

export type LawnProfile = {
  id: string;
  total_sqft: number;
  grass_type: string;
  establishment_date: string | null;
  target_mow_height_inches: number;
  latitude: number;
  longitude: number;
  usda_zone: string;
  climate_notes: string | null;
  soil_type: string;
  water_source: string;
  created_at: string;
  updated_at: string;
};

export type IrrigationZone = {
  id: string;
  rachio_zone_id: string | null;
  is_enabled: boolean;
  zone_category: "turf" | "trees_shrubs" | "ornamental" | "inactive";
  zone_number: number;
  name: string;
  sqft: number | null;
  head_type: string;
  nozzle_gpm: number | null;
  precipitation_rate_in_per_hr: number | null;
  sun_exposure: string;
  slope: string;
  soil_type_override: string | null;
  notes: string | null;
  created_at: string;
  updated_at: string;
};

export type IrrigationZoneInput = Omit<IrrigationZone, "id" | "created_at" | "updated_at" | "is_enabled"> & {
  is_enabled?: boolean;
};

export type Equipment = {
  id: string;
  type: string;
  make: string;
  model: string;
  calibration: Record<string, unknown> | null;
  last_calibration_date: string | null;
  notes: string | null;
  created_at: string;
  updated_at: string;
};

export type Product = {
  id: string;
  name: string;
  manufacturer: string;
  product_type: string;
  active_ingredients: Record<string, unknown> | null;
  guaranteed_analysis: Record<string, unknown> | null;
  label_rate: number;
  label_rate_unit: string;
  reentry_interval_hours: number | null;
  min_reapplication_days: number | null;
  max_annual_rate: number | null;
  max_annual_rate_unit: string | null;
  current_inventory: number | null;
  current_inventory_unit: string | null;
  notes: string | null;
  created_at: string;
  updated_at: string;
};

export type TreatmentProduct = {
  product_id: string;
  rate_applied: number;
  rate_unit: string;
  position: number | null;
  notes: string | null;
  created_at: string;
  updated_at: string;
};

export type TreatmentProductInput = {
  product_id: string;
  rate_applied: number;
  rate_unit: string;
  position?: number | null;
  notes?: string | null;
};

export type Treatment = {
  id: string;
  applied_at: string;
  products: TreatmentProduct[];
  area_treated_sqft: number;
  equipment_id: string | null;
  applicator: string;
  weather_temp_f: number | null;
  weather_wind_mph: number | null;
  weather_conditions: string | null;
  target: string | null;
  notes: string | null;
  created_at: string;
  updated_at: string;
};

export type TreatmentInput = {
  applied_at: string;
  products: TreatmentProductInput[];
  area_treated_sqft: number;
  equipment_id: string | null;
  applicator: string;
  weather_temp_f: number | null;
  weather_wind_mph: number | null;
  weather_conditions: string | null;
  target: string | null;
  notes: string | null;
};

export type CulturalPractice = {
  id: string;
  performed_at: string;
  practice_type: string;
  details: Record<string, unknown> | null;
  equipment_id: string | null;
  notes: string | null;
  created_at: string;
  updated_at: string;
};

export type SoilTest = {
  id: string;
  sample_date: string;
  lab_name: string;
  ph: number | null;
  organic_matter_pct: number | null;
  phosphorus_ppm: number | null;
  potassium_ppm: number | null;
  calcium_ppm: number | null;
  magnesium_ppm: number | null;
  sulfur_ppm: number | null;
  iron_ppm: number | null;
  manganese_ppm: number | null;
  zinc_ppm: number | null;
  copper_ppm: number | null;
  boron_ppm: number | null;
  cec: number | null;
  base_saturation: Record<string, unknown> | null;
  lab_recommendations: string | null;
  pdf_path: string | null;
  notes: string | null;
  created_at: string;
  updated_at: string;
};

export type DashboardSummary = {
  weather: {
    current: {
      observed_at: string | null;
      temp_f: number | null;
      humidity_pct: number | null;
      wind_mph: number | null;
      precip_in: number | null;
    };
    today_forecast: {
      date: string | null;
      temp_high_f: number | null;
      temp_low_f: number | null;
      precip_probability_pct: number | null;
      precip_amount_in: number | null;
      conditions: string | null;
    };
    next_7_days: Array<{
      date: string;
      temp_high_f: number | null;
      temp_low_f: number | null;
      precip_probability_pct: number | null;
      precip_amount_in: number | null;
      wind_mph: number | null;
      conditions: string | null;
    }>;
    forecast_rainfall_7d_in: number;
    rainfall_7d_in: number;
  };
  irrigation: {
    total_water_7d_in: number;
    turf_avg_7d_in: number;
    all_zones_total_7d_in: number;
    zones_with_events_7d: number;
    excluded_zone_numbers: number[];
    calibration_note: string;
    zones: Array<{
      zone_id: string;
      zone_number: number;
      zone_name: string;
      sqft: number | null;
      inches: number;
      zone_category: "turf" | "trees_shrubs" | "ornamental" | "inactive";
      included_in_turf_budget: boolean;
    }>;
  };
  last_treatment: {
    id: string;
    applied_at: string;
    product_name: string | null;
    days_ago: number;
  } | null;
  last_cultural_by_type: Array<{
    id: string;
    practice_type: string;
    performed_at: string;
    days_ago: number;
  }>;
  last_soil_test: {
    id: string;
    sample_date: string;
    ph: number | null;
    organic_matter_pct: number | null;
    phosphorus_ppm: number | null;
    potassium_ppm: number | null;
    cec: number | null;
  } | null;
  active_reminders: Array<{
    id: string;
    due_date: string;
    reminder_type: string;
    description: string;
  }>;
  quick_actions: Array<{
    label: string;
    href: string;
  }>;
};

// ─── Lawn Profile ─────────────────────────────────────────────────────────────

export async function getLawnProfile() {
  return apiRequest<LawnProfile>("/api/v1/lawn-profile");
}

export async function upsertLawnProfile(body: Omit<LawnProfile, "id" | "created_at" | "updated_at">) {
  return apiRequest<LawnProfile>("/api/v1/lawn-profile", { method: "POST", body });
}

export async function patchLawnProfile(body: Partial<Omit<LawnProfile, "id" | "created_at" | "updated_at">>) {
  return apiRequest<LawnProfile>("/api/v1/lawn-profile", { method: "PATCH", body });
}

// ─── Irrigation Zones ─────────────────────────────────────────────────────────

export async function listIrrigationZones(options?: { includeDisabled?: boolean }) {
  const includeDisabled = options?.includeDisabled ? "?include_disabled=true" : "";
  return apiRequest<IrrigationZone[]>(`/api/v1/irrigation-zones${includeDisabled}`);
}

export async function getIrrigationZone(id: string) {
  return apiRequest<IrrigationZone>(`/api/v1/irrigation-zones/${id}`);
}

export async function createIrrigationZone(body: IrrigationZoneInput) {
  return apiRequest<IrrigationZone>("/api/v1/irrigation-zones", { method: "POST", body });
}

export async function patchIrrigationZone(id: string, body: Partial<IrrigationZoneInput>) {
  return apiRequest<IrrigationZone>(`/api/v1/irrigation-zones/${id}`, { method: "PATCH", body });
}

export async function deleteIrrigationZone(id: string) {
  return apiRequest<void>(`/api/v1/irrigation-zones/${id}`, { method: "DELETE" });
}

// ─── Equipment ────────────────────────────────────────────────────────────────

export async function listEquipment() {
  return apiRequest<Equipment[]>("/api/v1/equipment");
}

export async function getEquipment(id: string) {
  return apiRequest<Equipment>(`/api/v1/equipment/${id}`);
}

export async function createEquipment(body: Omit<Equipment, "id" | "created_at" | "updated_at">) {
  return apiRequest<Equipment>("/api/v1/equipment", { method: "POST", body });
}

export async function patchEquipment(id: string, body: Partial<Omit<Equipment, "id" | "created_at" | "updated_at">>) {
  return apiRequest<Equipment>(`/api/v1/equipment/${id}`, { method: "PATCH", body });
}

export async function deleteEquipment(id: string) {
  return apiRequest<void>(`/api/v1/equipment/${id}`, { method: "DELETE" });
}

// ─── Products ─────────────────────────────────────────────────────────────────

export async function listProducts() {
  return apiRequest<Product[]>("/api/v1/products");
}

export async function getProduct(id: string) {
  return apiRequest<Product>(`/api/v1/products/${id}`);
}

export async function createProduct(body: Omit<Product, "id" | "created_at" | "updated_at">) {
  return apiRequest<Product>("/api/v1/products", { method: "POST", body });
}

export async function patchProduct(id: string, body: Partial<Omit<Product, "id" | "created_at" | "updated_at">>) {
  return apiRequest<Product>(`/api/v1/products/${id}`, { method: "PATCH", body });
}

export async function deleteProduct(id: string) {
  return apiRequest<void>(`/api/v1/products/${id}`, { method: "DELETE" });
}

// ─── Treatments ───────────────────────────────────────────────────────────────

export async function listTreatments() {
  return apiRequest<Treatment[]>("/api/v1/treatments");
}

export async function getTreatment(id: string) {
  return apiRequest<Treatment>(`/api/v1/treatments/${id}`);
}

export async function createTreatment(body: TreatmentInput) {
  return apiRequest<Treatment>("/api/v1/treatments", { method: "POST", body });
}

export async function patchTreatment(id: string, body: Partial<TreatmentInput>) {
  return apiRequest<Treatment>(`/api/v1/treatments/${id}`, { method: "PATCH", body });
}

export async function deleteTreatment(id: string) {
  return apiRequest<void>(`/api/v1/treatments/${id}`, { method: "DELETE" });
}

// ─── Cultural Practices ───────────────────────────────────────────────────────

export async function listCulturalPractices() {
  return apiRequest<CulturalPractice[]>("/api/v1/cultural-practices");
}

export async function getCulturalPractice(id: string) {
  return apiRequest<CulturalPractice>(`/api/v1/cultural-practices/${id}`);
}

export async function createCulturalPractice(body: Omit<CulturalPractice, "id" | "created_at" | "updated_at">) {
  return apiRequest<CulturalPractice>("/api/v1/cultural-practices", { method: "POST", body });
}

export async function patchCulturalPractice(id: string, body: Partial<Omit<CulturalPractice, "id" | "created_at" | "updated_at">>) {
  return apiRequest<CulturalPractice>(`/api/v1/cultural-practices/${id}`, { method: "PATCH", body });
}

export async function deleteCulturalPractice(id: string) {
  return apiRequest<void>(`/api/v1/cultural-practices/${id}`, { method: "DELETE" });
}

// ─── Soil Tests ───────────────────────────────────────────────────────────────

export async function listSoilTests() {
  return apiRequest<SoilTest[]>("/api/v1/soil-tests");
}

export async function getSoilTest(id: string) {
  return apiRequest<SoilTest>(`/api/v1/soil-tests/${id}`);
}

export async function createSoilTest(body: Omit<SoilTest, "id" | "created_at" | "updated_at">) {
  return apiRequest<SoilTest>("/api/v1/soil-tests", { method: "POST", body });
}

export async function patchSoilTest(id: string, body: Partial<Omit<SoilTest, "id" | "created_at" | "updated_at">>) {
  return apiRequest<SoilTest>(`/api/v1/soil-tests/${id}`, { method: "PATCH", body });
}

export async function deleteSoilTest(id: string) {
  return apiRequest<void>(`/api/v1/soil-tests/${id}`, { method: "DELETE" });
}

// ─── Dashboard ───────────────────────────────────────────────────────────────

export async function getDashboardSummary() {
  return apiRequest<DashboardSummary>("/api/v1/dashboard/summary");
}

// ─── Reminders ────────────────────────────────────────────────────────────────

export type Reminder = {
  id: string;
  due_date: string;
  reminder_type: string;
  description: string;
  completed: boolean;
  completed_at: string | null;
  completed_treatment_id: string | null;
  completed_cultural_id: string | null;
  created_at: string;
  updated_at: string;
};

export type ReminderInput = {
  due_date: string;
  reminder_type: string;
  description: string;
};

export async function listReminders(opts?: { completed?: boolean }) {
  const params = opts?.completed !== undefined ? `?completed=${opts.completed}` : "";
  return apiRequest<Reminder[]>(`/api/v1/reminders${params}`);
}

export async function createReminder(body: ReminderInput) {
  return apiRequest<Reminder>("/api/v1/reminders", { method: "POST", body });
}

export async function patchReminder(id: string, body: Partial<ReminderInput>) {
  return apiRequest<Reminder>(`/api/v1/reminders/${id}`, { method: "PATCH", body });
}

export async function completeReminder(
  id: string,
  opts?: { completed_treatment_id?: string; completed_cultural_id?: string },
) {
  return apiRequest<Reminder>(`/api/v1/reminders/${id}/complete`, {
    method: "POST",
    body: opts ?? {},
  });
}

export async function snoozeReminder(id: string, new_due_date: string) {
  return apiRequest<Reminder>(`/api/v1/reminders/${id}/snooze`, {
    method: "POST",
    body: { new_due_date },
  });
}

export async function deleteReminder(id: string) {
  return apiRequest<void>(`/api/v1/reminders/${id}`, { method: "DELETE" });
}