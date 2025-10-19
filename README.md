docker compose up -d db


Import OSM data

Now your osm2pgsql command will work without errors:

docker compose run --rm osm2pgsql \
  -d geodb -U geo -H db -W \
  --create --slim --latlong --hstore \
  /data/delhi-latest.osm.pbf

and enter password geo


python -m app.db_init
python -m app.train_model