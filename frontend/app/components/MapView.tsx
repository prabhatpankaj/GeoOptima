"use client";
import React, { useEffect, useRef } from "react";
import L from "../components/leaflet-icon-fix";
import "leaflet/dist/leaflet.css";
import "leaflet.heat";

interface MapViewProps {
  geojson: any;
  selectedLocation?: { lat: number; lng: number; name: string } | null;
}

export default function MapView({ geojson, selectedLocation }: MapViewProps) {
  const mapRef = useRef<L.Map | null>(null);
  const mapId = "darkstore-map";

  // -----------------------
  // Initialize map
  // -----------------------
  useEffect(() => {
    if (!mapRef.current) {
      const map = L.map(mapId, {
        center: [28.6139, 77.2167], // Delhi center
        zoom: 11,
        zoomControl: true,
      });

      L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
        attribution:
          '&copy; <a href="https://osm.org">OpenStreetMap</a> contributors',
        maxZoom: 19,
      }).addTo(map);

      mapRef.current = map;
    }

    return () => {
      mapRef.current?.remove();
      mapRef.current = null;
    };
  }, []);

  // -----------------------
  // Handle GeoJSON updates
  // -----------------------
  useEffect(() => {
    if (!geojson || !mapRef.current) return;
    const map = mapRef.current;

    // Clear previous non-tile layers
    map.eachLayer((layer: any) => {
      if (!(layer instanceof L.TileLayer)) map.removeLayer(layer);
    });

    // ✅ Add store markers
    const storeLayer = L.geoJSON(geojson, {
      pointToLayer: (feature, latlng) => {
        const open = feature.properties.open;
        const color = open ? "#22c55e" : "#ef4444"; // green or red
        const icon = L.divIcon({
          className: "",
          html: `<svg xmlns="http://www.w3.org/2000/svg" width="26" height="26">
                   <circle cx="13" cy="13" r="10" fill="${color}" stroke="#111" stroke-width="1.5"/>
                 </svg>`,
          iconSize: [26, 26],
          iconAnchor: [13, 13],
        });
        return L.marker(latlng, { icon });
      },
      onEachFeature: (feature, layer) => {
        const props = feature.properties;
        layer.bindPopup(`
          <strong>Store ID:</strong> ${props.id}<br/>
          <strong>Status:</strong> ${props.open ? "🟢 Open" : "🔴 Closed"}<br/>
          <strong>Fixed Cost:</strong> ${props.fixed_cost.toFixed(2)}
        `);
      },
    }).addTo(map);

    // ✅ Add heat layer (open stores only)
    const heatPoints = geojson.features
      .filter((f: any) => f.properties.open)
      .map((f: any) => [
        f.geometry.coordinates[1],
        f.geometry.coordinates[0],
        Math.min(f.properties.fixed_cost / 2, 1.0),
      ]);

    if (heatPoints.length > 0) {
      L.heatLayer(heatPoints, { radius: 25, blur: 15, maxZoom: 17 }).addTo(map);
    }

    // Fit to all markers
    const bounds = storeLayer.getBounds();
    if (bounds.isValid()) map.fitBounds(bounds, { padding: [50, 50] });
  }, [geojson]);

  // -----------------------
  // Handle Location Search (zoom + marker)
  // -----------------------
  useEffect(() => {
    if (!selectedLocation || !mapRef.current) return;
    const map = mapRef.current;

    const { lat, lng, name } = selectedLocation;
    const marker = L.marker([lat, lng]).addTo(map);
    marker.bindPopup(`<strong>${name}</strong>`).openPopup();

    // Smooth zoom + pan
    map.flyTo([lat, lng], 14, { animate: true, duration: 1.5 });

    // Cleanup (remove marker if new one selected)
    return () => {
      map.removeLayer(marker);
    };
  }, [selectedLocation]);

  return <div id={mapId} className="w-full h-full" />;
}
