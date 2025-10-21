-- =============================================================
-- 🗺️ GeoOptima | Multi-city PostGIS Initialization Script
-- -------------------------------------------------------------
-- Creates:
--   • Base database: geodb
--   • Default user DB: geo        (prevents connection warning)
--   • NCR city databases:
--       geodb_delhi, geodb_noida, geodb_gurgaon,
--       geodb_faridabad, geodb_ghaziabad
-- Enables PostGIS, HSTORE, and DBLINK in all.
-- =============================================================

-- -------------------------------------
-- 1️⃣ Base Extensions in default DB
-- -------------------------------------
CREATE DATABASE geo;  -- Prevents "database 'geo' does not exist" error

CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS hstore;
CREATE EXTENSION IF NOT EXISTS dblink;

-- -------------------------------------
-- 2️⃣ Create City Databases via DBLink
-- -------------------------------------
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_database WHERE datname = 'geodb_delhi') THEN
        PERFORM dblink_exec('dbname=postgres', 'CREATE DATABASE geodb_delhi');
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_database WHERE datname = 'geodb_noida') THEN
        PERFORM dblink_exec('dbname=postgres', 'CREATE DATABASE geodb_noida');
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_database WHERE datname = 'geodb_gurgaon') THEN
        PERFORM dblink_exec('dbname=postgres', 'CREATE DATABASE geodb_gurgaon');
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_database WHERE datname = 'geodb_faridabad') THEN
        PERFORM dblink_exec('dbname=postgres', 'CREATE DATABASE geodb_faridabad');
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_database WHERE datname = 'geodb_ghaziabad') THEN
        PERFORM dblink_exec('dbname=postgres', 'CREATE DATABASE geodb_ghaziabad');
    END IF;
END
$$ LANGUAGE plpgsql;

-- -------------------------------------
-- 3️⃣ Enable PostGIS + HSTORE in each city DB
-- -------------------------------------
\c geodb_delhi
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS hstore;

\c geodb_noida
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS hstore;

\c geodb_gurgaon
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS hstore;

\c geodb_faridabad
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS hstore;

\c geodb_ghaziabad
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS hstore;

-- -------------------------------------
-- ✅ Verification Output
-- -------------------------------------
\echo '✅ GeoOptima multi-city PostGIS databases initialized successfully!'
\echo '   Created DBs: geo, geodb_delhi, geodb_noida, geodb_gurgaon, geodb_faridabad, geodb_ghaziabad'
\echo '   Extensions: postgis, hstore, dblink'
