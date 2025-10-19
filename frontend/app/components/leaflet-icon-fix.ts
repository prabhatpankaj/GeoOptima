import L from "leaflet";

// ✅ Reference assets directly (they’ll be served from /public)
L.Icon.Default.mergeOptions({
  iconRetinaUrl: "/leaflet-assets/marker-icon-2x.png",
  iconUrl: "/leaflet-assets/marker-icon.png",
  shadowUrl: "/leaflet-assets/marker-shadow.png",
});

export default L;
