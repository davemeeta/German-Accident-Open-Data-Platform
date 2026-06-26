# German Accident Open Data Platform
### Unfallatlas Risk Lens

A data-integration platform that harmonises official German road-accident open data across nine annual releases (2016–2024) into a single canonical database, exposed through a documented REST API and an interactive React dashboard.

---

## What it does

- Integrates **2,098,019 accident records** from four official German open sources
- Harmonises nine years of schema drift (column names, encodings, decimal formats)
- Joins all sources on the official **AGS region key** (no spatial joins needed)
- Exposes the data through a **15-endpoint REST API** with OpenAPI/Swagger docs
- Provides an interactive dashboard with hotspot maps, choropleth, rankings and trends

---

## Data Sources

| Source | Content | Format |
|---|---|---|
| [Unfallatlas](https://www.opengeodata.nrw.de/produkte/transport_verkehr/unfallatlas/) | Road accidents 2016–2024 | CSV |
| [GENESIS 46251](https://www.regionalstatistik.de/genesis/online) | Registered cars per district | CSV |
| [Regionalstatistik](https://www.regionalstatistik.de/genesis/online) | Accidents per 10k inhabitants | CSV |
| [isellsoap/deutschlandGeoJSON](https://github.com/isellsoap/deutschlandGeoJSON) | District boundaries | GeoJSON |

All sources: **Datenlizenz Deutschland – Namensnennung 2.0 (dl-de/by-2-0)**

---

## Tech Stack

**Backend:** Python · FastAPI · SQLite · pandas  
**Frontend:** React · Vite · TypeScript · Tailwind CSS · Leaflet · Recharts  
**Docs:** OpenAPI / Swagger (auto-generated at `/docs`)

---

## Project Structure

```
unfallatlas-risk-lens/
├── data/
│   ├── raw/
│   │   ├── unfallatlas/          # Accident CSVs (2016–2024, not in repo)
│   │   ├── regional-stats/       # Cars + per-10k CSVs
│   │   └── boundaries/           # districts.geojson
│   └── processed/                # Built SQLite DB (not in repo)
├── src/
│   ├── etl/                      # ETL pipeline
│   │   ├── config.py             # Paths + column-variant map
│   │   ├── run_import.py         # Orchestrator (one command to rebuild)
│   │   ├── load_accidents.py     # Unfallatlas loader
│   │   ├── load_indicators.py    # Cars + per-10k loader
│   │   ├── load_geometries.py    # GeoJSON boundary loader
│   │   ├── check_questions.py    # Verify mandatory answers
│   │   └── quality_checks.py    # 15 automated data-quality checks
│   ├── api/
│   │   └── main.py               # FastAPI application (15 endpoints)
│   ├── db/
│   │   └── schema.sql            # Canonical SQLite schema
│   └── frontend/                 # React + Vite dashboard
├── requirements.txt
└── README.md
```

---

## Prerequisites

| Software | Version | Purpose |
|---|---|---|
| Python | 3.10+ | ETL pipeline + API |
| Node.js | 18+ | Frontend build |
| npm | 9+ | Frontend dependencies |

---

## Setup

**1. Clone and create virtual environment**

```bash
git clone https://github.com/davemeeta/German-Accident-Open-Data-Platform.git
cd German-Accident-Open-Data-Platform
python3 -m venv .venv
source .venv/bin/activate
pip install fastapi "uvicorn[standard]" pandas
```

**2. Add raw data files**

Download and place the following in `data/raw/`:

```
data/raw/unfallatlas/2016/csv/Unfallorte_2016_LinRef.txt
data/raw/unfallatlas/2017/...
...  (2016–2024, one folder per year)
data/raw/regional-stats/registered_cars_2023.csv
data/raw/regional-stats/accident_per_10000_per_city.csv
data/raw/boundaries/districts.geojson
```

Download district boundaries:

```bash
curl -L -o data/raw/boundaries/districts.geojson \
  https://raw.githubusercontent.com/isellsoap/deutschlandGeoJSON/main/4_kreise/4_niedrig.geo.json
```

**3. Build the database**

```bash
cd src
python -m etl.run_import
```

Expected output:

```
loaded  2,098,019 accidents (9 files)
loaded        ~400 car rows
loaded        ~400 per-10k rows
loaded        ~400 district geometries
```

**4. Verify data quality**

```bash
python -m etl.quality_checks
# Expected: 0 FAIL · 1 WARN · 14 PASS
```

**5. Install frontend dependencies**

```bash
cd src/frontend
npm install
```

---

## Running the Platform

Open two terminals:

**Terminal 1 — API server**

```bash
cd src
uvicorn api.main:app --reload
# API:  http://127.0.0.1:8000
# Docs: http://127.0.0.1:8000/docs
```

**Terminal 2 — Frontend**

```bash
cd src/frontend
npm run dev
# Dashboard: http://localhost:5173
```

---

## API Endpoints

| Endpoint | Description |
|---|---|
| `GET /aggregates/accidents` | Accident count for any filter |
| `GET /aggregates/accidents/by-region` | Rankings by state/district |
| `GET /aggregates/rate` | Accidents per 100k cars/inhabitants |
| `GET /aggregates/hotspots` | Severity-ranked crash clusters |
| `GET /accidents/near` | Spatial radius query |
| `GET /regions/choropleth` | GeoJSON for choropleth maps |
| `GET /stats/first-year` | Earliest data year per state |
| `GET /stats/trend` | Year-over-year trend series |
| `GET /metadata/sources` | Integrated sources + licences |

Full interactive documentation: `http://127.0.0.1:8000/docs`

---

## Answering the Mandatory Questions

```bash
cd src
python -m etl.check_questions
```

```
1. Earliest accident year overall:     2016
2. Accidents in Saxony 2023:          12,513
3. First data year for NRW:           2019
4. First data year for MV:            2020
5. Pedestrian accidents Berlin 2023:  1,794
```

---

## Updating Data

To add a new year of Unfallatlas data:

1. Place the new CSV in `data/raw/unfallatlas/{year}/`
2. Re-run `python -m etl.run_import`

No code changes needed — the loader auto-discovers all files.

---

## Troubleshooting

| Problem | Solution |
|---|---|
| "Failed to fetch" in dashboard | Check uvicorn is running in Terminal 1 |
| Port 8000 already in use | `lsof -ti:8000 \| xargs kill -9` |
| Choropleth shows no districts | Ensure districts.geojson is in boundaries/ and re-run import |
| Maps blank after filter change | Hard refresh: Cmd+Shift+R |
| ModuleNotFoundError: etl | Run commands from inside `src/`, not the project root |

---

## Licence

Data: Datenlizenz Deutschland – Namensnennung 2.0 (dl-de/by-2-0)  
Code: MIT


Designed and Developed by MEETA DAVE
Visit my Portfolio @ https://davemeeta.github.io/
