from typing import Optional
from enum import Enum
import json, sqlite3
from math import radians, sin, cos, asin, sqrt

from fastapi import FastAPI, Depends, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from pydantic import BaseModel
from etl.config import DB_PATH, STATE_ABBR, STATE_NAMES

app = FastAPI(title="German Accident Data Platform", version="2.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

@app.exception_handler(StarletteHTTPException)
async def http_err(req, exc):
    return JSONResponse(status_code=exc.status_code,
        content={"error":True,"status":exc.status_code,"detail":exc.detail,"path":req.url.path})

@app.exception_handler(RequestValidationError)
async def val_err(req, exc):
    return JSONResponse(status_code=422,
        content={"error":True,"status":422,"detail":jsonable_encoder(exc.errors()),"path":req.url.path})

class Level(str, Enum):
    state="state"; district="district"; municipality="municipality"
class Category(int, Enum):
    fatal=1; serious=2; light=3
class Order(str, Enum):
    desc="desc"; asc="asc"

def get_db():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False); conn.row_factory = sqlite3.Row
    try: yield conn
    finally: conn.close()

class Provenance(BaseModel):
    source: str; license: Optional[str]; license_url: Optional[str]
class CountResponse(BaseModel):
    query: dict; accident_count: int; provenance: list[Provenance]
class AccidentCount(BaseModel):
    ags: str; name: Optional[str]; level: str; year: Optional[int]=None; accident_count: int

FLAG_COLUMNS = {"pedestrian":"is_pedestrian","bicycle":"is_bicycle","car":"is_car",
                "motorcycle":"is_motorcycle","goods":"is_goods"}

def resolve_state_prefix(state):
    s = state.strip().upper()
    if s in STATE_ABBR: return STATE_ABBR[s]
    if s.isdigit() and s.zfill(2) in STATE_NAMES: return s.zfill(2)
    raise HTTPException(400, f"Unknown state '{state}'.")

def build_filters(year, month, weekday, hour, category, region, state, flags):
    c, p = [], []
    if state: c.append("municipality_ags LIKE ?"); p.append(resolve_state_prefix(state)+"%")
    elif region:
        if not region.isdigit(): raise HTTPException(400, "region must be numeric AGS.")
        c.append("municipality_ags LIKE ?"); p.append(region+"%")
    for col, val in (("year",year),("month",month),("weekday",weekday),("hour",hour),("category",category)):
        if val is not None: c.append(f"{col} = ?"); p.append(int(val))
    for name, on in flags.items():
        if on: c.append(f"{FLAG_COLUMNS[name]} = 1")
    return (" WHERE "+" AND ".join(c)) if c else "", p

def prov(db):
    return [Provenance(source=r["name"],license=r["license"],license_url=r["license_url"])
            for r in db.execute("SELECT name,license,license_url FROM data_sources").fetchall()]

def make_flags(ped,bic,car,mot,gds):
    return {"pedestrian":ped,"bicycle":bic,"car":car,"motorcycle":mot,"goods":gds}

# ---------- ENDPOINTS ----------

@app.get("/")
def root(): return {"name":app.title,"docs":"/docs"}

@app.get("/health")
def health(): return {"status":"ok"}

@app.get("/aggregates/accidents", response_model=CountResponse)
def agg_count(state:Optional[str]=None, region:Optional[str]=None,
    year:Optional[int]=None, month:Optional[int]=None, category:Optional[Category]=None,
    pedestrian:bool=False, bicycle:bool=False, car:bool=False,
    motorcycle:bool=False, goods:bool=False, db=Depends(get_db)):
    flags = make_flags(pedestrian,bicycle,car,motorcycle,goods)
    w, p = build_filters(year,month,None,None,category,region,state,flags)
    cnt = db.execute(f"SELECT COUNT(*) FROM accidents{w}", p).fetchone()[0]
    q = {k:v for k,v in {"state":state,"region":region,"year":year,"month":month,
         "category":int(category) if category else None,**flags}.items() if v not in (None,False)}
    return CountResponse(query=q, accident_count=cnt, provenance=prov(db))

@app.get("/aggregates/accidents/by-region", response_model=list[AccidentCount])
def agg_by_region(level:Level=Query(Level.state), year:Optional[int]=None,
    category:Optional[Category]=None,
    state:Optional[str]=None, region:Optional[str]=None,
    pedestrian:bool=False, bicycle:bool=False, car:bool=False,
    motorcycle:bool=False, goods:bool=False,
    order:Order=Query(Order.desc), limit:int=Query(20,ge=1,le=1000), db=Depends(get_db)):
    plen = {"state":2,"district":5,"municipality":8}[level.value]
    flags = make_flags(pedestrian,bicycle,car,motorcycle,goods)
    w, p = build_filters(year,None,None,None,category,region,state,flags)
    rows = db.execute(
        f"SELECT substr(a.municipality_ags,1,{plen}) AS ags, r.name, COUNT(*) AS accident_count "
        f"FROM accidents a LEFT JOIN regions r ON r.ags=substr(a.municipality_ags,1,{plen}) "
        f"{w} GROUP BY ags ORDER BY accident_count {'ASC' if order.value=='asc' else 'DESC'} LIMIT ?",
        p+[limit]).fetchall()
    return [AccidentCount(ags=r["ags"],name=r["name"],level=level.value,year=year,
            accident_count=r["accident_count"]) for r in rows]

@app.get("/aggregates/hotspots")
def hotspots(precision:int=Query(3,ge=2,le=4), min_count:int=Query(3,ge=1,le=100),
    year:Optional[int]=None, state:Optional[str]=None, region:Optional[str]=None,
    category:Optional[Category]=None,
    pedestrian:bool=False, bicycle:bool=False, motorcycle:bool=False,
    car:bool=False, goods:bool=False,
    weighted:bool=True, limit:int=Query(20,ge=1,le=500), db=Depends(get_db)):
    W = {"fatal":10,"serious":3,"light":1}
    flags = make_flags(pedestrian,bicycle,car,motorcycle,goods)
    w, p = build_filters(year,None,None,None,category,region,state,flags)
    w = (w+" AND " if w else " WHERE ")+"lon IS NOT NULL AND lat IS NOT NULL"
    rows = db.execute(
        f"SELECT ROUND(lon,?) AS rlon, ROUND(lat,?) AS rlat, COUNT(*) AS total, "
        f"SUM(category=1) AS fatal, SUM(category=2) AS serious, SUM(category=3) AS light, "
        f"SUM(is_pedestrian) AS pedestrian, SUM(is_bicycle) AS bicycle, "
        f"AVG(lon) AS clon, AVG(lat) AS clat, substr(MIN(municipality_ags),1,5) AS district_ags "
        f"FROM accidents{w} GROUP BY rlon,rlat HAVING COUNT(*)>=?",
        [precision,precision]+p+[min_count]).fetchall()
    names = {r["ags"]:r["name"] for r in db.execute(
        "SELECT ags,name FROM regions WHERE level='district'").fetchall()}
    out = []
    for r in rows:
        sc = r["fatal"]*W["fatal"]+r["serious"]*W["serious"]+r["light"]*W["light"]
        out.append({"lat":round(r["clat"],6),"lon":round(r["clon"],6),
            "district":names.get(r["district_ags"]),"district_ags":r["district_ags"],
            "total":r["total"],"fatal":r["fatal"],"serious":r["serious"],"light":r["light"],
            "pedestrian":r["pedestrian"],"bicycle":r["bicycle"],"severity_score":sc})
    out.sort(key=lambda x:(x["severity_score"] if weighted else x["total"],x["total"]),reverse=True)
    return {"ranked_by":"severity_score" if weighted else "total","severity_weights":W,
            "grid_precision":precision,"approx_cell_size_m":round(111_000/(10**precision)),
            "min_count":min_count,"hotspot_count":len(out),"hotspots":out[:limit],"provenance":prov(db)}

@app.get("/regions/choropleth")
def choropleth(metric:str=Query("count"), year:int=Query(...),
    state:Optional[str]=None, category:Optional[Category]=None,
    pedestrian:bool=False, bicycle:bool=False, car:bool=False,
    motorcycle:bool=False, goods:bool=False, db=Depends(get_db)):
    if state:
        pfx = resolve_state_prefix(state)
        geo = db.execute("SELECT ags,name,geometry FROM regions WHERE level='district' AND geometry IS NOT NULL AND ags LIKE ?",
                         (pfx+"%",)).fetchall()
    else:
        geo = db.execute("SELECT ags,name,geometry FROM regions WHERE level='district' AND geometry IS NOT NULL").fetchall()
    if not geo: raise HTTPException(404,"No district geometries loaded.")
    values = {}
    if metric=="count":
        flags = make_flags(pedestrian,bicycle,car,motorcycle,goods)
        w, p = build_filters(year,None,None,None,category,None,state,flags)
        for r in db.execute(f"SELECT substr(municipality_ags,1,5) AS ags, COUNT(*) AS c FROM accidents{w} GROUP BY ags",p):
            values[r["ags"]] = r["c"]
        vlabel = "accidents"
    elif metric=="rate10k":
        ind = db.execute("SELECT indicator_id FROM indicators WHERE code='ACC_PER_10K'").fetchone()
        if ind:
            for r in db.execute("SELECT reg.ags AS ags, iv.value AS v FROM indicator_values iv "
                "JOIN regions reg ON reg.region_id=iv.region_id WHERE iv.indicator_id=? AND iv.year=?",
                (ind["indicator_id"],year)):
                values[r["ags"]] = r["v"]
        vlabel = "accidents per 10k"
    else: raise HTTPException(400,"metric must be count or rate10k")
    feats = [{"type":"Feature","geometry":json.loads(g["geometry"]),
              "properties":{"ags":g["ags"],"name":g["name"],"value":values.get(g["ags"])}} for g in geo]
    return {"type":"FeatureCollection","metric":metric,"value_label":vlabel,"year":year,
            "feature_count":len(feats),"features":feats,"provenance":prov(db)}

@app.get("/stats/trend")
def trend(state:Optional[str]=None, category:Optional[Category]=None, db=Depends(get_db)):
    c, p = [], []
    if state: c.append("municipality_ags LIKE ?"); p.append(resolve_state_prefix(state)+"%")
    if category is not None: c.append("category = ?"); p.append(int(category))
    w = (" WHERE "+" AND ".join(c)) if c else ""
    rows = db.execute(f"SELECT year, COUNT(*) AS accident_count FROM accidents{w} GROUP BY year ORDER BY year",p).fetchall()
    return {"state":state,"series":[dict(r) for r in rows],"provenance":prov(db)}

@app.get("/stats/first-year")
def first_year(state:Optional[str]=None, db=Depends(get_db)):
    if state:
        pfx = resolve_state_prefix(state)
        y = db.execute("SELECT MIN(year) FROM accidents WHERE municipality_ags LIKE ?",(pfx+"%",)).fetchone()[0]
        return {"state":state,"first_year":y}
    return {"scope":"overall","first_year":db.execute("SELECT MIN(year) FROM accidents").fetchone()[0]}

@app.get("/accidents")
def list_accidents(state:Optional[str]=None, region:Optional[str]=None,
    year:Optional[int]=None, month:Optional[int]=Query(None,ge=1,le=12),
    weekday:Optional[int]=Query(None,ge=1,le=7), hour:Optional[int]=Query(None,ge=0,le=23),
    category:Optional[Category]=None,
    pedestrian:bool=False, bicycle:bool=False, car:bool=False,
    motorcycle:bool=False, goods:bool=False,
    limit:int=Query(50,ge=1,le=1000), offset:int=Query(0,ge=0), db=Depends(get_db)):
    flags = make_flags(pedestrian,bicycle,car,motorcycle,goods)
    w, p = build_filters(year,month,weekday,hour,category,region,state,flags)
    total = db.execute(f"SELECT COUNT(*) FROM accidents{w}",p).fetchone()[0]
    rows = db.execute(
        f"SELECT accident_id,municipality_ags,year,month,hour,weekday,category,"
        f"is_pedestrian,is_bicycle,is_car,is_motorcycle,is_goods,lon,lat "
        f"FROM accidents{w} ORDER BY accident_id LIMIT ? OFFSET ?",p+[limit,offset]).fetchall()
    return {"total":total,"limit":limit,"offset":offset,"items":[dict(r) for r in rows],"provenance":prov(db)}

@app.get("/metadata/sources", response_model=list[Provenance])
def sources(db=Depends(get_db)): return prov(db)

@app.get("/import-runs")
def import_runs(db=Depends(get_db)):
    return [dict(r) for r in db.execute(
        "SELECT ir.import_run_id, ds.name AS source, ir.retrieved_at, ir.snapshot, ir.record_count "
        "FROM import_runs ir JOIN data_sources ds ON ds.source_id=ir.source_id ORDER BY ir.import_run_id").fetchall()]
