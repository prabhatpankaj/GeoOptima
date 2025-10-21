#!/bin/sh
set -e

DB_USER="geo"
DB_HOST="0.0.0.0"
DB_PORT="5432"

declare -A MAPS
MAPS[delhi]="delhi-city.osm.pbf"
MAPS[noida]="noida-city.osm.pbf"
MAPS[gurgaon]="gurgaon-city.osm.pbf"
MAPS[faridabad]="faridabad-city.osm.pbf"
MAPS[ghaziabad]="ghaziabad-city.osm.pbf"

echo "🌍 Starting OSM import for NCR cities..."
for city in "${!MAPS[@]}"; do
  FILE="/data/${MAPS[$city]}"
  DB="geodb_${city}"

  if [ ! -f "$FILE" ]; then
    echo "⚠️  Skipping $city — file not found ($FILE)"
    continue
  fi

  echo "🗺️  Importing $FILE → $DB ..."
  osm2pgsql \
    --create \
    --database="$DB" \
    --username="$DB_USER" \
    --host="$DB_HOST" \
    --port="$DB_PORT" \
    --hstore \
    --latlong \
    --number-processes=4 \
    "$FILE"

  echo "✅ $city import complete!"
done

echo "🏁 All NCR city imports done."
