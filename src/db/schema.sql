-- ============================================================================
--  DBW Project — Canonical schema for German accident-data integration
--  Target DBMS: SQLite (portable, file-based, reproducible).
--  Design follows the suggested schema but adds clean provenance + indexing.
--
--  Modelling decisions (explain these in the term paper):
--   * AGS is the single hierarchical join key (state=2, district=5, mun.=8 digits).
--   * Population is NOT a static column on regions: it changes per year and is
--     needed per-year for "rate per 100k", so it lives in indicator_values.
--   * Accidents store BOTH a region_id FK (clean model) AND a denormalised
--     municipality_ags string, so every count is a fast prefix filter.
--   * Provenance (data_sources + import_runs) is separated from payload data,
--     and licences are stored so the API can return them with responses.
-- ============================================================================

PRAGMA foreign_keys = ON;

-- ----------------------------------------------------------------------------
--  REGIONS  — hierarchy: country > state > district > municipality
-- ----------------------------------------------------------------------------
CREATE TABLE regions (
    region_id        INTEGER PRIMARY KEY,
    ags              TEXT    NOT NULL UNIQUE,   -- '14' state, '14612' district, '14612000' mun.
    name             TEXT,                       -- NULL until enriched from a name reference
    level            TEXT    NOT NULL CHECK (level IN ('country','state','district','municipality')),
    parent_region_id INTEGER REFERENCES regions(region_id),
    geometry         TEXT                       -- optional GeoJSON (for map demo); NULL is fine
);

-- ----------------------------------------------------------------------------
--  DATA SOURCES  — provenance + licence (returned to clients with responses)
-- ----------------------------------------------------------------------------
CREATE TABLE data_sources (
    source_id    INTEGER PRIMARY KEY,
    name         TEXT NOT NULL,         -- 'Unfallatlas', 'Gemeindeverzeichnis', 'GENESIS 46251'
    url          TEXT NOT NULL,
    license      TEXT,                  -- e.g. 'dl-de/by-2-0'
    license_url  TEXT
);

-- ----------------------------------------------------------------------------
--  IMPORT RUNS  — every ETL execution; lets you trace + reproduce a load
-- ----------------------------------------------------------------------------
CREATE TABLE import_runs (
    import_run_id INTEGER PRIMARY KEY,
    source_id     INTEGER NOT NULL REFERENCES data_sources(source_id),
    retrieved_at  TEXT    NOT NULL,     -- ISO timestamp of download
    snapshot      TEXT,                 -- e.g. file name / year / version downloaded
    record_count  INTEGER,
    notes         TEXT
);

-- ----------------------------------------------------------------------------
--  ACCIDENTS  — one row = one accident with personal injury (Unfallatlas)
-- ----------------------------------------------------------------------------
CREATE TABLE accidents (
    accident_id      INTEGER PRIMARY KEY,
    source_uid       TEXT,              -- original OBJECTID/UIDENTSTLAE, used for de-dup
    region_id        INTEGER REFERENCES regions(region_id),
    municipality_ags TEXT NOT NULL,     -- denormalised 8-digit AGS for fast prefix filtering
    year             INTEGER NOT NULL,
    month            INTEGER,
    hour             INTEGER,
    weekday          INTEGER,
    category         INTEGER,           -- UKATEGORIE: 1=fatal, 2=serious injury, 3=light injury
    type             INTEGER,           -- UTYP1 (accident type)
    kind             INTEGER,           -- UART  (accident kind)
    light            INTEGER,           -- ULICHTVERH / LICHT (light conditions)
    road_condition   INTEGER,           -- IstStrassenzustand / STRZUSTAND / IstStrasse (drifts by year)
    is_bicycle       INTEGER DEFAULT 0, -- IstRad
    is_car           INTEGER DEFAULT 0, -- IstPKW
    is_pedestrian    INTEGER DEFAULT 0, -- IstFuss
    is_motorcycle    INTEGER DEFAULT 0, -- IstKrad
    is_goods         INTEGER DEFAULT 0, -- IstGkfz
    is_other         INTEGER DEFAULT 0, -- IstSonstige / IstSonstig
    lon              REAL,              -- XGCSWGS84
    lat              REAL,              -- YGCSWGS84
    import_run_id    INTEGER REFERENCES import_runs(import_run_id)
);

-- ----------------------------------------------------------------------------
--  INDICATORS + VALUES  — population, registered cars, any contextual stat
--  (per region, per year) — powers the multi-source "rate per 100k" questions
-- ----------------------------------------------------------------------------
CREATE TABLE indicators (
    indicator_id  INTEGER PRIMARY KEY,
    code          TEXT NOT NULL UNIQUE,  -- e.g. 'POP', 'CARS' or the GENESIS table code
    name          TEXT NOT NULL,
    unit          TEXT,                  -- 'persons', 'vehicles'
    source_system TEXT                   -- 'GENESIS 12411', 'Gemeindeverzeichnis'
);

CREATE TABLE indicator_values (
    region_id     INTEGER NOT NULL REFERENCES regions(region_id),
    indicator_id  INTEGER NOT NULL REFERENCES indicators(indicator_id),
    year          INTEGER NOT NULL,
    value         REAL,
    import_run_id INTEGER REFERENCES import_runs(import_run_id),
    PRIMARY KEY (region_id, indicator_id, year)
);

-- ----------------------------------------------------------------------------
--  INDEXES  — the queries the examiner asks are count/filter by region+year
-- ----------------------------------------------------------------------------
CREATE INDEX idx_acc_year         ON accidents(year);
CREATE INDEX idx_acc_ags          ON accidents(municipality_ags);
CREATE INDEX idx_acc_ags_year     ON accidents(municipality_ags, year);
CREATE INDEX idx_acc_region       ON accidents(region_id);
CREATE INDEX idx_regions_level    ON regions(level);
CREATE INDEX idx_indval_year      ON indicator_values(year);