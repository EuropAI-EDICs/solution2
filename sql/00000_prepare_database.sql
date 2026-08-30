-- Copyright (c) 2024:
--   Helmholtz-Zentrum Potsdam Deutsches GeoForschungsZentrum GFZ
--
-- This program is free software: you can redistribute it and/or modify it
-- under the terms of the GNU Affero General Public License as published by
-- the Free Software Foundation, either version 3 of the License, or (at
-- your option) any later version.
--
-- This program is distributed in the hope that it will be useful, but
-- WITHOUT ANY WARRANTY; without even the implied warranty of
-- MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU Affero
-- General Public License for more details.
--
-- You should have received a copy of the GNU Affero General Public License
-- along with this program. If not, see http://www.gnu.org/licenses/.

-- Create extension `postgis`.
CREATE EXTENSION IF NOT EXISTS postgis;

-- Create extension `postgis_cfcgal` for 3D processing.
CREATE EXTENSION IF NOT EXISTS postgis_sfcgal;

ALTER ROLE consumer
SET search_path = "$user", exposure, sources, sources_3d, osm_replication, public; -- noqa: RF05
ALTER ROLE contributor
SET search_path = "$user", exposure, sources, sources_3d, osm_replication, public; -- noqa: RF05
CREATE SCHEMA IF NOT EXISTS exposure;
CREATE SCHEMA IF NOT EXISTS sources;
CREATE SCHEMA IF NOT EXISTS sources_3d;
CREATE SCHEMA IF NOT EXISTS osm_import;
CREATE SCHEMA IF NOT EXISTS osm_replication;
CREATE SCHEMA IF NOT EXISTS osm_backup;
CREATE SCHEMA IF NOT EXISTS monitoring;

-- Schema usage privileges for both roles.
GRANT USAGE ON SCHEMA public TO read_only, read_write;
GRANT USAGE ON SCHEMA exposure TO read_only, read_write;
GRANT USAGE ON SCHEMA sources TO read_only, read_write;
GRANT USAGE ON SCHEMA sources_3d TO read_only, read_write;
GRANT USAGE ON SCHEMA osm_import TO read_only, read_write;
GRANT USAGE ON SCHEMA osm_replication TO read_only, read_write;
GRANT USAGE ON SCHEMA osm_backup TO read_only, read_write;
GRANT USAGE ON SCHEMA monitoring TO read_only, read_write;
-- Set default privileges for read-only role.
ALTER DEFAULT PRIVILEGES
GRANT SELECT ON TABLES TO read_only;
ALTER DEFAULT PRIVILEGES
GRANT USAGE, SELECT ON SEQUENCES TO read_only;
ALTER DEFAULT PRIVILEGES IN SCHEMA exposure
GRANT SELECT ON TABLES TO read_only;
ALTER DEFAULT PRIVILEGES IN SCHEMA exposure
GRANT USAGE, SELECT ON SEQUENCES TO read_only;
ALTER DEFAULT PRIVILEGES IN SCHEMA sources
GRANT SELECT ON TABLES TO read_only;
ALTER DEFAULT PRIVILEGES IN SCHEMA sources
GRANT USAGE, SELECT ON SEQUENCES TO read_only;
ALTER DEFAULT PRIVILEGES IN SCHEMA sources_3d
GRANT SELECT ON TABLES TO read_only;
ALTER DEFAULT PRIVILEGES IN SCHEMA sources_3d
GRANT USAGE, SELECT ON SEQUENCES TO read_only;

-- Default privileges for read_write role.
ALTER DEFAULT PRIVILEGES
GRANT SELECT, INSERT, UPDATE, DELETE, TRUNCATE ON TABLES TO read_write;
ALTER DEFAULT PRIVILEGES
GRANT ALL ON SEQUENCES TO read_write;
ALTER DEFAULT PRIVILEGES
GRANT ALL ON FUNCTIONS TO read_write;

-- Apply privileges to existing tables.
GRANT SELECT ON ALL TABLES IN SCHEMA public TO read_only;
GRANT SELECT ON ALL TABLES IN SCHEMA exposure TO read_only;
GRANT SELECT ON ALL TABLES IN SCHEMA sources TO read_only;
GRANT SELECT ON ALL TABLES IN SCHEMA sources_3d TO read_only;
GRANT SELECT ON ALL TABLES IN SCHEMA osm_import TO read_only;
GRANT SELECT ON ALL TABLES IN SCHEMA osm_replication TO read_only;
GRANT SELECT ON ALL TABLES IN SCHEMA osm_backup TO read_only;
GRANT SELECT ON ALL TABLES IN SCHEMA monitoring TO read_only;
GRANT SELECT,
INSERT,
UPDATE,
DELETE,
TRUNCATE ON ALL TABLES IN SCHEMA exposure TO read_write;
GRANT SELECT,
INSERT,
UPDATE,
DELETE,
TRUNCATE ON ALL TABLES IN SCHEMA sources TO read_write;
GRANT SELECT,
INSERT,
UPDATE,
DELETE,
TRUNCATE ON ALL TABLES IN SCHEMA sources_3d TO read_write;
GRANT SELECT,
INSERT,
UPDATE,
DELETE,
TRUNCATE ON ALL TABLES IN SCHEMA osm_import TO read_write;
GRANT SELECT,
INSERT,
UPDATE,
DELETE,
TRUNCATE ON ALL TABLES IN SCHEMA osm_replication TO read_write;
GRANT SELECT,
INSERT,
UPDATE,
DELETE,
TRUNCATE ON ALL TABLES IN SCHEMA osm_backup TO read_write;
GRANT SELECT,
INSERT,
UPDATE,
DELETE,
TRUNCATE ON ALL TABLES IN SCHEMA monitoring TO read_write;

-- Permission to create tables
GRANT CREATE ON SCHEMA exposure TO read_write;
GRANT CREATE ON SCHEMA sources TO read_write;
GRANT CREATE ON SCHEMA sources_3d TO read_write;
GRANT CREATE ON SCHEMA osm_replication TO read_write;
GRANT CREATE ON SCHEMA monitoring TO read_write;
-- Default privileges
ALTER DEFAULT PRIVILEGES IN SCHEMA exposure
GRANT SELECT, INSERT, UPDATE, DELETE, TRUNCATE ON TABLES TO read_write;

ALTER DEFAULT PRIVILEGES IN SCHEMA sources
GRANT SELECT, INSERT, UPDATE, DELETE, TRUNCATE ON TABLES TO read_write;
ALTER DEFAULT PRIVILEGES IN SCHEMA sources
GRANT ALL ON SEQUENCES TO read_write;

ALTER DEFAULT PRIVILEGES IN SCHEMA sources_3d
GRANT SELECT, INSERT, UPDATE, DELETE, TRUNCATE ON TABLES TO read_write;
ALTER DEFAULT PRIVILEGES IN SCHEMA sources_3d
GRANT ALL ON SEQUENCES TO read_write;

ALTER DEFAULT PRIVILEGES IN SCHEMA osm_replication
GRANT SELECT, INSERT, UPDATE, DELETE, TRUNCATE ON TABLES TO read_write;

ALTER DEFAULT PRIVILEGES IN SCHEMA monitoring
GRANT SELECT, INSERT, UPDATE, DELETE, TRUNCATE ON TABLES TO read_write;
