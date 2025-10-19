// /app/services/geocodeService.ts
export interface GeocodeResult {
  name: string;
  lat: number;
  lng: number;
  raw: any;
}

/**
 * Fetches location results from OpenStreetMap Nominatim API
 * with retries and rate-limit friendly headers.
 */
export async function fetchGeocodeResults(
  query: string,
  attempt = 1
): Promise<GeocodeResult[]> {
  if (!query || query.trim().length < 3) return [];

  try {
    const res = await fetch(
      `https://nominatim.openstreetmap.org/search?format=json&q=${encodeURIComponent(
        query
      )}&addressdetails=1&limit=5`,
      {
        headers: {
          "Accept-Language": "en",
          "User-Agent": "Darkstore-Optimizer/1.0 (contact@example.com)",
        },
      }
    );

    if (!res.ok) throw new Error(`Nominatim error ${res.status}`);
    const data = await res.json();

    return data.map((d: any) => ({
      name: d.display_name,
      lat: parseFloat(d.lat),
      lng: parseFloat(d.lon),
      raw: d,
    }));
  } catch (err: any) {
    // Retry for transient issues like REFUSED_STREAM or connection reset
    if (
      attempt < 3 &&
      (err.message.includes("Failed to fetch") ||
        err.message.includes("REFUSED_STREAM") ||
        err.message.includes("NetworkError"))
    ) {
      console.warn(`🌐 Nominatim retry #${attempt}`);
      await new Promise((r) => setTimeout(r, 800 * attempt));
      return fetchGeocodeResults(query, attempt + 1);
    }

    console.error("❌ Geocode fetch failed:", err.message);
    throw err;
  }
}
