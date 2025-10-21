docker compose down -v --remove-orphans

docker compose up -d db

docker compose logs db

Import OSM data

Now your osm2pgsql command will work without errors:

docker compose run osm2pgsql bash

bash import_ncr.sh

validate data in any database

SELECT
    COUNT(*) AS total_points,
    COUNT(name) FILTER (WHERE name IS NOT NULL) AS named_places,
    COUNT(DISTINCT place) AS unique_place_types
FROM planet_osm_point;

select * from planet_osm_point limit 10;

