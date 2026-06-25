"""
Central configuration for the ETL pipeline.

Paths are anchored to the PROJECT ROOT via this file's location, so commands work
no matter which directory you run them from. Layout assumed:

    <project root>/
        data/raw/unfallatlas/<year>/.../Unfallorte*.{txt,csv}
        data/raw/regional-stats/registered_cars_2023.csv, accident_per_10000_per_city.csv
        data/raw/boundaries/districts.geojson
        data/raw/aggregates/...
        data/processed/accidents.db        <- the built database
        src/etl/config.py                  <- this file
        src/db/schema.sql
"""
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths (anchored to project root, regardless of current working directory)
# ---------------------------------------------------------------------------
SRC = Path(__file__).resolve().parents[1]      # .../src
ROOT = Path(__file__).resolve().parents[2]      # project root

SCHEMA_PATH = SRC / "db" / "schema.sql"
DB_PATH = ROOT / "data" / "processed" / "accidents.db"

RAW_DIR = ROOT / "data" / "raw"
UNFALLATLAS_DIR = RAW_DIR / "unfallatlas"
REGIONAL_STATS_DIR = RAW_DIR / "regional-stats"
BOUNDARIES_DIR = RAW_DIR / "boundaries"
AGGREGATES_DIR = RAW_DIR / "aggregates"

# Specific source files
CARS_FILE = REGIONAL_STATS_DIR / "registered_cars_2023.csv"
CARS_YEAR = 2024   # file reference date is 01.01.2025 -> proxy for the 2024 fleet
PER10K_FILE = REGIONAL_STATS_DIR / "accident_per_10000_per_city.csv"
PER10K_YEAR = 2023
DISTRICTS_GEOJSON = BOUNDARIES_DIR / "districts.geojson"

DB_PATH.parent.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# Licences
# ---------------------------------------------------------------------------
DL_DE_BY_2_0 = "Datenlizenz Deutschland Namensnennung 2.0 (dl-de/by-2-0)"
DL_DE_BY_2_0_URL = "https://www.govdata.de/dl-de/by-2-0"

# ---------------------------------------------------------------------------
# Unfallatlas accident column map  (canonical field -> possible source names)
# Verified against the real 2016-2024 headers; matching is case-insensitive.
#   id:    FID/OBJECTID (2016), OBJECTID/UIDENTSTLA (2017), OBJECTID_1 (2018),
#          OBJECTID (2019), OBJECTID/UIDENTSTLAE (2020), OID_/UIDENTSTLAE (2021,23,24)
#   light: ULICHTVERH everywhere except 2017 (LICHT)
#   road:  IstStrasse (2016), STRZUSTAND (2017-20), IstStrassenzustand (2021+)
#   other: IstSonstig (2016-18), IstSonstige (2019+)
#   goods: IstGkfz present every year EXCEPT 2017 -> defaults to 0
# ---------------------------------------------------------------------------
UNFALLATLAS_COLUMN_MAP: dict[str, list[str]] = {
    "source_uid":     ["UIDENTSTLAE", "UIDENTSTLA", "OBJECTID", "OBJECTID_1", "OID_", "FID"],
    "uland":          ["ULAND"],
    "uregbez":        ["UREGBEZ"],
    "ukreis":         ["UKREIS"],
    "ugemeinde":      ["UGEMEINDE"],
    "year":           ["UJAHR"],
    "month":          ["UMONAT"],
    "hour":           ["USTUNDE"],
    "weekday":        ["UWOCHENTAG"],
    "category":       ["UKATEGORIE"],
    "kind":           ["UART"],
    "type":           ["UTYP1"],
    "light":          ["ULICHTVERH", "LICHT"],
    "road_condition": ["IstStrassenzustand", "USTRZUSTAND", "STRZUSTAND", "IstStrasse"],
    "is_bicycle":     ["IstRad"],
    "is_car":         ["IstPKW", "IstPkw"],
    "is_pedestrian":  ["IstFuss", "IstFuß"],
    "is_motorcycle":  ["IstKrad"],
    "is_goods":       ["IstGkfz"],
    "is_other":       ["IstSonstige", "IstSonstig", "IstSonstiges"],
    "lon":            ["XGCSWGS84", "LINREFX_WGS84"],
    "lat":            ["YGCSWGS84", "LINREFY_WGS84"],
}
# UKATEGORIE: 1=fatal, 2=serious injury, 3=light injury (see DSB_Unfallatlas.pdf)

UNFALLATLAS_LICENSE = DL_DE_BY_2_0
UNFALLATLAS_LICENSE_URL = DL_DE_BY_2_0_URL

# ---------------------------------------------------------------------------
# States (AGS land codes) — fixed official reference data
# ---------------------------------------------------------------------------
STATE_NAMES: dict[str, str] = {
    "01": "Schleswig-Holstein", "02": "Hamburg", "03": "Niedersachsen",
    "04": "Bremen", "05": "Nordrhein-Westfalen", "06": "Hessen",
    "07": "Rheinland-Pfalz", "08": "Baden-Württemberg", "09": "Bayern",
    "10": "Saarland", "11": "Berlin", "12": "Brandenburg",
    "13": "Mecklenburg-Vorpommern", "14": "Sachsen", "15": "Sachsen-Anhalt",
    "16": "Thüringen",
}

STATE_ABBR: dict[str, str] = {
    "SH": "01", "HH": "02", "NI": "03", "HB": "04", "NW": "05", "HE": "06",
    "RP": "07", "BW": "08", "BY": "09", "SL": "10", "BE": "11", "BB": "12",
    "MV": "13", "SN": "14", "ST": "15", "TH": "16",
}