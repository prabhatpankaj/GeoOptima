"use client";
import { useEffect, useState } from "react";

export default function CitySelector({ selectedCity, onChange }: any) {
  const [cities, setCities] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchCities() {
      try {
        const res = await fetch("http://localhost:8000/plan/cities");
        const data = await res.json();
        setCities(data.cities || []);
      } catch (err) {
        console.error("❌ Failed to fetch cities:", err);
        setCities(["delhi"]); // fallback
      } finally {
        setLoading(false);
      }
    }
    fetchCities();
  }, []);

  return (
    <div className="mb-3">
      <label className="block text-sm font-medium text-gray-700 mb-1">Select City</label>
      <select
        value={selectedCity}
        onChange={(e) => onChange(e.target.value)}
        disabled={loading}
        className="w-full p-2 border rounded-md text-sm"
      >
        {loading ? (
          <option>Loading...</option>
        ) : (
          cities.map((city) => (
            <option key={city} value={city}>
              {city.toUpperCase()}
            </option>
          ))
        )}
      </select>
    </div>
  );
}
