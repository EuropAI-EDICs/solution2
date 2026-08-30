SET SEARCH_PATH TO sources, public;

CREATE TABLE google_buildings (
    id BIGSERIAL PRIMARY KEY,
    confidence REAL,
    area REAL,
    geometry GEOMETRY (MULTIPOLYGON, 4326) NOT NULL,  -- noqa: RF04
    plus_code TEXT
);
CREATE INDEX googlebuildings_geometry_idx ON google_buildings USING gist (geometry);
CREATE INDEX googlebuildings_pluscode_idx ON google_buildings (plus_code);

CREATE TABLE microsoft_buildings (
    id BIGSERIAL PRIMARY KEY,
    confidence REAL,
    geometry GEOMETRY (MULTIPOLYGON, 4326) NOT NULL,  -- noqa: RF04
    quadkey TEXT NOT NULL,
    height REAL
);
CREATE INDEX microsoftbuildings_geometry_idx ON microsoft_buildings USING gist (
    geometry
);

CREATE TABLE boundaries (
    id TEXT PRIMARY KEY,
    total_builtup_area REAL,
    attributes JSONB,
    geometry GEOMETRY (MULTIPOLYGON, 4326) NOT NULL  -- noqa: RF04
);
CREATE INDEX boundaries_geometry_idx ON boundaries USING gist (geometry);

CREATE TABLE ghsl_characteristics (
    id SERIAL PRIMARY KEY,
    category INTEGER,
    geometry GEOMETRY (MULTIPOLYGON, 4326) NOT NULL  -- noqa: RF04
);
CREATE INDEX ghslcharacteristics_geometry_idx ON ghsl_characteristics USING gist (geometry);

CREATE TABLE ghsl_age (
    id SERIAL PRIMARY KEY,
    age_class INTEGER,
    geometry GEOMETRY (POLYGON, 4326)  -- noqa: RF04
);
CREATE INDEX ghsl_age_geometry_idx ON ghsl_age USING gist (geometry);

CREATE TABLE ghsl_height (
    id SERIAL PRIMARY KEY,
    height REAL,
    geometry GEOMETRY (POLYGON, 4326)  -- noqa: RF04
);
CREATE INDEX ghsl_height_geometry_idx ON ghsl_height USING gist (geometry);

CREATE TABLE ghsl_wup (
    id SERIAL PRIMARY KEY,
    density_class INTEGER,
    geometry GEOMETRY (POLYGON, 4326)  -- noqa: RF04
);
CREATE INDEX ghsl_wup_geometry_idx ON ghsl_wup USING gist (geometry);

CREATE TABLE tabula (
    id SERIAL PRIMARY KEY,
    iso_3166_2 TEXT,
    taxonomy TEXT,
    attributes JSONB NOT NULL
);

CREATE TABLE oceans_seas (
    id SERIAL PRIMARY KEY,
    geometry GEOMETRY (MULTIPOLYGON, 4326) NOT NULL  -- noqa: RF04
);
CREATE INDEX oceansseas_geometry_idx ON oceans_seas USING gist (geometry);

ALTER TABLE ONLY exposure.district_assets
ADD CONSTRAINT districtassets_boundariesid_fkey FOREIGN KEY (
    boundary_id
) REFERENCES boundaries (id);
