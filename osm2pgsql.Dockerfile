FROM debian:bullseye-slim

# Install osm2pgsql and dependencies
RUN apt-get update && apt-get install -y \
    osm2pgsql \
    postgresql-client \
    curl \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /data
ENTRYPOINT ["osm2pgsql"]
