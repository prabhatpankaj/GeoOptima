"use client";

import { useState, useRef } from "react";
import { fetchGeocodeResults, GeocodeResult } from "../services/geocodeService";

interface SearchBarProps {
  onSelect: (pt: { name: string; lat: number; lng: number }) => void;
}

export default function SearchBar({ onSelect }: SearchBarProps) {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<GeocodeResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const handleSearch = (value: string) => {
    setQuery(value);
    setError(null);

    if (debounceRef.current) clearTimeout(debounceRef.current);

    if (value.trim().length < 3) {
      setResults([]);
      return;
    }

    debounceRef.current = setTimeout(async () => {
      try {
        setLoading(true);
        const data = await fetchGeocodeResults(value);
        setResults(data);
      } catch (err: any) {
        setError("Could not fetch results. Try again.");
        setResults([]);
      } finally {
        setLoading(false);
      }
    }, 600);
  };

  return (
    <div className="relative">
      <label className="block text-sm font-medium text-gray-700 mb-1">
        Search place
      </label>

      <input
        type="text"
        value={query}
        onChange={(e) => handleSearch(e.target.value)}
        placeholder="Search locations..."
        className="w-full p-2 border rounded-md text-sm focus:ring focus:ring-green-200"
      />

      {loading && (
        <div className="absolute right-3 top-2 text-gray-400 text-xs animate-pulse">
          ...
        </div>
      )}

      {error && (
        <div className="mt-1 text-xs text-red-500 font-medium">{error}</div>
      )}

      {results.length > 0 && (
        <ul className="absolute z-10 bg-white border rounded-md mt-1 w-full shadow text-sm">
          {results.map((r) => (
            <li
              key={r.name + r.lat}
              onClick={() => {
                onSelect({ name: r.name, lat: r.lat, lng: r.lng });
                setQuery(r.name);
                setResults([]);
              }}
              className="p-2 hover:bg-green-50 cursor-pointer truncate"
              title={r.name}
            >
              📍 {r.name}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
