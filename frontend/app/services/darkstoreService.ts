// app/services/darkstoreService.ts

export interface OptimizationParams {
  max_time_min?: number;
  capacity?: number;
}

export interface OptimizationStats {
  stores_open: number;
  avg_travel_min: number;
  total_customers: number;
  open_pct?: number;
  avg_fixed_cost_open?: number;
  avg_fixed_cost_closed?: number;
  execution_time_sec?: number;
}

export interface OptimizationResponse {
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

const API_BASE =
  process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, "") || "http://localhost:8000";

/* ---------------------------------------------------
 *  🔹 Run Darkstore Optimization
 * --------------------------------------------------- */
export async function runOptimization(
  params: OptimizationParams = { max_time_min: 12, capacity: 150 }
): Promise<OptimizationResponse> {
  const url = `${API_BASE}/plan/darkstores`;

  try {
    const res = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(params),
    });

    if (!res.ok) {
      const msg = await res.text();
      throw new Error(`Backend error ${res.status}: ${msg}`);
    }

    return (await res.json()) as OptimizationResponse;
  } catch (error) {
    console.error("❌ Failed to call Darkstore API:", error);
    throw error;
  }
}

/**
 * Alias for naming consistency with older code
 */
export const runDarkstoreOptimization = runOptimization;

/* ---------------------------------------------------
 *  🔹 Fetch Insights after Optimization
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
