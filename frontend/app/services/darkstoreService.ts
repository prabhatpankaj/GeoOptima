// app/services/darkstoreService.ts

/* ---------------------------------------------------
 *  📦 Type Definitions
 * --------------------------------------------------- */

export interface OptimizationParams {
  max_time_min?: number;
  capacity?: number;
  city?: string;
}

export interface OptimizationStats {
  stores_open: number;
  avg_travel_min: number;
  total_customers: number;
  open_pct?: number;
  avg_fixed_cost_open?: number;
  avg_fixed_cost_closed?: number;
  execution_time_sec?: number;
  city?: string;
}

export interface OptimizationResponse {
  city?: string;
  geojson: any;
  stats: OptimizationStats;
}

export interface InsightsResponse {
  summary: {
    total_candidates: number;
    open_stores: number;
    closed_stores: number;
    open_pct: number;
    avg_fixed_cost_open: number;
    avg_fixed_cost_closed: number;
  };
  coverage: {
    avg_travel_min: number;
    p90_travel_min: number;
    max_travel_min: number;
  };
  clusters: {
    cluster_id: number;
    count: number;
    center_lat: number;
    center_lon: number;
    avg_fixed_cost: number;
  }[];
}

export interface CityInfo {
  city: string;
  osm_file: string;
}

export interface CityListResponse {
  available_cities: CityInfo[];
}

/* ---------------------------------------------------
 *  🌍 API Base
 * --------------------------------------------------- */

const API_BASE = process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, "") || "http://localhost:8000";

/* ---------------------------------------------------
 *  🏙️ Fetch Available Cities
 * --------------------------------------------------- */
export async function getCities(): Promise<CityListResponse> {
  const url = `${API_BASE}/plan/cities`;

  try {
    const res = await fetch(url, { method: "GET" });
    if (!res.ok) {
      const msg = await res.text();
      throw new Error(`Backend error ${res.status}: ${msg}`);
    }

    return (await res.json()) as CityListResponse;
  } catch (error) {
    console.error("⚠️ Failed to fetch available cities:", error);
    // Graceful fallback
    return { available_cities: [{ city: "delhi", osm_file: "" }] };
  }
}

/* ---------------------------------------------------
 *  🚀 Run Darkstore Optimization (per city)
 * --------------------------------------------------- */
export async function runOptimization(
  params: OptimizationParams = { max_time_min: 12, capacity: 150, city: "delhi" }
): Promise<OptimizationResponse> {
  const city = params.city || "delhi";
  const url = `${API_BASE}/plan/darkstores?city=${encodeURIComponent(city)}`;

  try {
    const res = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        max_time_min: params.max_time_min,
        capacity: params.capacity,
      }),
    });

    if (!res.ok) {
      const msg = await res.text();
      throw new Error(`Backend error ${res.status}: ${msg}`);
    }

    const data = (await res.json()) as OptimizationResponse;
    return { ...data, city };
  } catch (error) {
    console.error(`❌ Failed to call Darkstore API for city=${city}:`, error);
    throw error;
  }
}

/**
 * ✅ Alias for backward compatibility
 */
export const runDarkstoreOptimization = runOptimization;

/* ---------------------------------------------------
 *  📊 Fetch Insights After Optimization
 * --------------------------------------------------- */
export async function getInsights(): Promise<InsightsResponse> {
  const url = `${API_BASE}/plan/insights`;

  try {
    const res = await fetch(url, { method: "GET" });
    if (!res.ok) {
      const msg = await res.text();
      throw new Error(`Backend error ${res.status}: ${msg}`);
    }

    return (await res.json()) as InsightsResponse;
  } catch (error) {
    console.error("❌ Failed to fetch Insights:", error);
    throw error;
  }
}

/* ---------------------------------------------------
 *  🧠 Utility: Reset/Reload (optional)
 * --------------------------------------------------- */
export async function resetState(): Promise<void> {
  const url = `${API_BASE}/state/reset`;

  try {
    await fetch(url, { method: "POST" });
    console.info("✅ Backend STATE cleared.");
  } catch (error) {
    console.warn("⚠️ Failed to reset backend state:", error);
  }
}
