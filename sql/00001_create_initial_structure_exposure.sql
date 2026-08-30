SET SEARCH_PATH TO exposure, public;

CREATE TABLE sources (
    id SMALLSERIAL PRIMARY KEY,
    name TEXT NOT NULL,  -- noqa: RF04
    uri TEXT,
    publication_date TIMESTAMP WITHOUT TIME ZONE
);
CREATE UNIQUE INDEX sources_name_publicationdate_idx ON sources (name, publication_date);

CREATE TABLE entities (
    id BIGSERIAL PRIMARY KEY,
    quadkey TEXT NOT NULL CHECK (char_length(quadkey) = 18),
    iso_3166 TEXT NOT NULL,
    category SMALLINT NOT NULL CHECK (category IN (0, 1, 2)),
    source_id SMALLINT,
    building_id TEXT,
    attributes JSONB,
    taxonomy JSONB,
    geometry GEOMETRY (MULTIPOLYGON, 4326) NOT NULL,  -- noqa: RF04
    geometry3d GEOMETRY (MULTIPOLYGONZ, 4979),
    FOREIGN KEY (source_id) REFERENCES sources (id)
);
CREATE UNIQUE INDEX entities_tile_quadkey_idx
ON entities (quadkey)
WHERE category = 0;

CREATE UNIQUE INDEX entities_buildingid_sourceid_idx
ON entities (building_id, source_id)
WHERE category != 0;

CREATE INDEX entities_quadkey_idx ON entities (quadkey);
CREATE INDEX entities_category_idx ON entities (category);
CREATE INDEX entities_geometry_idx ON entities USING gist (geometry);
CREATE INDEX entities_geometry3d_idx ON entities USING gist (geometry3d);
CREATE INDEX entities_iso3166_idx ON entities (iso_3166);
CREATE INDEX entities_sourceid_idx ON entities (source_id);

CREATE TABLE taxonomies (
    id SERIAL PRIMARY KEY,
    category SMALLINT NOT NULL,
    taxonomy JSONB NOT NULL,
    attributes JSONB
);

CREATE TABLE assets (
    id BIGSERIAL PRIMARY KEY,
    iso_3166 TEXT NOT NULL,
    taxonomy_id INTEGER NOT NULL REFERENCES taxonomies (id),
    tabula_taxonomy_id INTEGER REFERENCES taxonomies (id),
    average_net_floor_area REAL,
    attributes JSONB,
    baseline_attributes JSONB
);
CREATE INDEX assets_taxonomyid_idx ON assets (taxonomy_id);
CREATE INDEX assets_selection_idx ON assets (
    iso_3166, taxonomy_id, tabula_taxonomy_id, average_net_floor_area
);

CREATE TABLE metadata (
    tag_key TEXT PRIMARY KEY,
    tag_value TEXT,
    tag_comment TEXT,
    attributes JSONB
);

CREATE TABLE district_assets (
    asset_id BIGSERIAL NOT NULL REFERENCES assets (id) ON DELETE CASCADE,
    boundary_id TEXT,
    number REAL NOT NULL
);
CREATE INDEX districtassets_boundaryid_idx ON district_assets (boundary_id);
CREATE INDEX districtassets_assetid_idx ON district_assets (asset_id);

CREATE TABLE entity_assets (
    entity_id BIGSERIAL NOT NULL REFERENCES entities (id) ON DELETE CASCADE,
    asset_id BIGSERIAL NOT NULL REFERENCES assets (id) ON DELETE CASCADE,
    number REAL NOT NULL,
    relative_size REAL DEFAULT 1
);
CREATE INDEX entityassets_entityid_idx ON entity_assets (entity_id);
CREATE INDEX entityassets_assetid_idx ON entity_assets (asset_id);
