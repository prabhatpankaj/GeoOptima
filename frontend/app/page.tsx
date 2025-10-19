"use client";

import { useState } from "react";
import dynamic from "next/dynamic";
import MarkerSidebar from "./components/MarkerSidebar";
import SearchBar from "./components/SearchBar";
import { runOptimization, getInsights } from "./services/darkstoreService";

const MapView = dynamic(() => import("./components/MapView"), { ssr: false });

export default function Page() {
  const [geoData, setGeoData] = useState<any>(null);
  const [stats, setStats] = useState<any>(null);
  const [insights, setInsights] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [loadingText, setLoadingText] = useState<string>("Processing... please wait");
  const [lastRun, setLastRun] = useState<Date | null>(null);

  // ---------------------------
  // 🔹 Run Optimization Handler
  // ---------------------------
  const handleRunOptimization = async () => {
    try {
      setLoading(true);
      setLoadingText("Running Optimization... please wait");
      setInsights(null);
      const data = await runOptimization({ max_time_min: 12, capacity: 150 });
      setGeoData(data.geojson);
      setStats(data.stats);
      setLastRun(new Date());
    } catch (err) {
      console.error("❌ Optimization failed:", err);
      alert("Optimization failed. Check backend or API connectivity.");
    } finally {
      setLoading(false);
    }
  };

  // ---------------------------
  // 🔹 Fetch Insights Handler
  // ---------------------------
  const handleViewInsights = async () => {
    try {
      setLoading(true);
      setLoadingText("Loading Insights... please wait");
      const data = await getInsights();
      setInsights(data);
    } catch (err) {
      console.error("❌ Failed to fetch insights:", err);
      alert("Could not fetch insights. Ensure optimization has completed.");
    } finally {
      setLoading(false);
    }
  };

  // ---------------------------
  // 🔹 UI Layout
  // ---------------------------
  return (
    <div className="relative flex h-screen w-screen overflow-hidden">
      {/* ✅ Full-Screen Overlay Loader (applies to entire app) */}
      {loading && (
        <div className="absolute inset-0 flex items-center justify-center bg-gray-800 bg-opacity-40 z-50">
          <div className="bg-white p-6 rounded-lg shadow-xl flex flex-col items-center justify-center space-y-3">
            <div className="w-8 h-8 border-4 border-gray-300 border-t-blue-600 rounded-full animate-spin"></div>
            <p className="text-gray-700 font-semibold text-base text-center">
              {loadingText}
            </p>
          </div>
        </div>
      )}

      {/* Sidebar */}
      <aside className="w-80 xl:w-96 p-4 border-r bg-white flex flex-col overflow-y-auto">
        <h2 className="text-lg font-semibold mb-3">Darkstore Optimizer</h2>
        <SearchBar onSelect={(pt) => console.log("Search selected:", pt)} />

        <button
          onClick={handleRunOptimization}
          disabled={loading}
          className={`mt-4 px-4 py-2 rounded-md text-white font-semibold transition-colors ${
            loading
              ? "bg-gray-400 cursor-not-allowed"
              : "bg-green-600 hover:bg-green-700"
          }`}
        >
          {loading ? "Running Optimization..." : "Run Optimization"}
        </button>

        <button
          onClick={handleViewInsights}
          disabled={loading}
          className={`mt-2 px-4 py-2 rounded-md text-white font-semibold transition-colors ${
            loading
              ? "bg-gray-400 cursor-not-allowed"
              : "bg-blue-600 hover:bg-blue-700"
          }`}
        >
          {loading ? "Loading Insights..." : "View Insights"}
        </button>

        {lastRun && (
          <div className="text-xs text-gray-400 mt-1">
            Last run: {lastRun.toLocaleTimeString()}
          </div>
        )}

        {/* Optimization Stats */}
        {stats && (
          <div className="mt-4 text-sm space-y-2 border-t pt-3">
            <div className="flex justify-between">
              <span>Open %:</span>
              <span>{stats.open_pct ?? "N/A"}%</span>
            </div>
            <div className="flex justify-between">
              <span>Avg Cost (open):</span>
              <span>
                {stats.avg_fixed_cost_open
                  ? stats.avg_fixed_cost_open.toFixed(2)
                  : "N/A"}
              </span>
            </div>
            <div className="flex justify-between">
              <span>Avg Cost (closed):</span>
              <span>
                {stats.avg_fixed_cost_closed
                  ? stats.avg_fixed_cost_closed.toFixed(2)
                  : "N/A"}
              </span>
            </div>
          </div>
        )}

        {/* Insights Section */}
        {insights && (
          <div className="mt-5 text-sm border-t pt-3">
            <h3 className="font-semibold mb-1">Insights</h3>

            {/* Coverage */}
            <div>
              <strong>Coverage:</strong>
              <div className="ml-2 space-y-1">
                <div>
                  Avg Travel:{" "}
                  {insights.coverage?.avg_travel_min?.toFixed(2) ?? "N/A"} min
                </div>
                <div>
                  P90 Travel:{" "}
                  {insights.coverage?.p90_travel_min?.toFixed(2) ?? "N/A"} min
                </div>
                <div>
                  Max Travel:{" "}
                  {insights.coverage?.max_travel_min?.toFixed(2) ?? "N/A"} min
                </div>
              </div>
            </div>

            {/* Clusters */}
            <div className="mt-3">
              <strong>Clusters:</strong>
              <ul className="ml-3 list-disc space-y-1">
                {insights.clusters?.length ? (
                  insights.clusters.map((c: any) => (
                    <li key={c.cluster_id}>
                      Zone {c.cluster_id + 1}: {c.count} stores (avg cost{" "}
                      {c.avg_fixed_cost.toFixed(2)})
                    </li>
                  ))
                ) : (
                  <li>No clusters found</li>
                )}
              </ul>
            </div>
          </div>
        )}

        <div className="flex-1 overflow-y-auto mt-4">
          <MarkerSidebar markers={[]} onRemove={() => {}} />
        </div>
      </aside>

      {/* Map Section */}
      <main className="flex-1 h-full">
        <MapView geojson={geoData} />
      </main>
    </div>
  );
}
