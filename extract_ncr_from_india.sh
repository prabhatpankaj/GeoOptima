#!/usr/bin/env bash
# ============================================================
# Extract NCR Cities (Delhi, Noida, Gurgaon, Faridabad, Ghaziabad)
# from full india-latest.osm.pbf file using osmium
# ------------------------------------------------------------
# Author: GeoOptima | Prabhat
# Version: 1.4 (macOS safe: no bash 4+ substitutions)
# ============================================================

set -e
set -o pipefail

SRC="./india-latest.osm.pbf"
OUT_DIR="./data"
LOG_FILE="./extract_log.txt"

mkdir -p "$OUT_DIR"
: > "$LOG_FILE"  # clear log file

if [ ! -f "$SRC" ]; then
  echo "❌ Source file not found: $SRC"
  exit 1
fi

# ------------------------------------------------------------
# City Names and Corresponding Bounding Boxes
# ------------------------------------------------------------
CITIES=("delhi" "noida" "gurgaon" "faridabad" "ghaziabad")
BBOXES=(
  "76.84,28.38,77.38,28.88"  # Delhi
  "77.28,28.45,77.45,28.63"  # Noida
  "76.92,28.36,77.10,28.53"  # Gurgaon
  "77.25,28.33,77.45,28.52"  # Faridabad
  "77.35,28.60,77.55,28.78"  # Ghaziabad
)

# Helper: capitalize first letter (for macOS Bash 3)
capitalize() {
  echo "$1" | awk '{print toupper(substr($0,1,1)) substr($0,2)}'
}

# ------------------------------------------------------------
# Banner
# ------------------------------------------------------------
echo "🌏 GeoOptima | NCR City Extractor"
echo "-------------------------------------------"
echo "Source File  : $SRC"
echo "Output Folder: $OUT_DIR"
echo "Log File     : $LOG_FILE"
echo "-------------------------------------------"
sleep 1

# ------------------------------------------------------------
# Extraction Loop
# ------------------------------------------------------------
for i in "${!CITIES[@]}"; do
  city="${CITIES[$i]}"
  city_capitalized=$(capitalize "$city")
  bbox="${BBOXES[$i]}"
  output="${OUT_DIR}/${city}-city.osm.pbf"

  echo "🗺️  Extracting $city_capitalized..."
  echo "   Bounding Box: $bbox"

  if osmium extract --strategy=smart --set-bounds -b "$bbox" "$SRC" -o "$output" >>"$LOG_FILE" 2>&1; then
    size=$(du -h "$output" | cut -f1)
    echo "✅ $city_capitalized extract complete → ${output} (${size})"
  else
    echo "⚠️  Extraction failed for $city (check $LOG_FILE)"
  fi

  echo "-------------------------------------------"
  sleep 0.5
done

# ------------------------------------------------------------
# Summary Table
# ------------------------------------------------------------
echo ""
echo "📊 Extraction Summary"
echo "-------------------------------------------"
printf "%-12s | %-10s | %-30s\n" "City" "Size" "Output File"
echo "-------------------------------------------"

for i in "${!CITIES[@]}"; do
  city="${CITIES[$i]}"
  city_capitalized=$(capitalize "$city")
  output="${OUT_DIR}/${city}-city.osm.pbf"
  if [ -f "$output" ]; then
    size=$(du -h "$output" | cut -f1)
    printf "%-12s | %-10s | %-30s\n" "$city_capitalized" "$size" "$(basename "$output")"
  else
    printf "%-12s | %-10s | %-30s\n" "$city_capitalized" "FAILED" "-"
  fi
done

echo "-------------------------------------------"
echo "🏁 All NCR extracts completed successfully."
echo "📂 Files saved in: $OUT_DIR"
echo "🧾 Log file: $LOG_FILE"
echo ""
echo "Tip: Run 'osmium fileinfo ./data/delhi-city.osm.pbf | grep Bounding' to verify bounding boxes."
