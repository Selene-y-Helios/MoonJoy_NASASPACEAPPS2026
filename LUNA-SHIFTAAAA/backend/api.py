"""Stateless NASA LOLA + JPL SPICE web API for arbitrary covered south-pole sites."""
from __future__ import annotations

import importlib.util
import io
import threading
from collections import OrderedDict
from datetime import timedelta
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field
from fastapi.responses import FileResponse, Response, HTMLResponse
from fastapi.staticfiles import StaticFiles

from .dynamic_site import (
    build_terrain_mesh, dem_paths, get_or_compute_horizon, latlon_from_regional_xy,
    map_metadata, map_png, resolve_site,
)
from .spice_visibility import KERNEL_NAMES, calculate_visibility, parse_utc
from .horizon_utils import check_observer_match
from .site_comparison import intersect_opportunities, site_comparison_metrics
from .mission_rules import evaluate_mission_windows
from .orbit_ephemeris import calculate_orbit_ephemeris

ROOT = Path(__file__).resolve().parents[1]
WEB_DIR = ROOT / "frontend"
APP_DIST = ROOT / "web" / "dist"
KERNELS = ROOT / "data" / "kernels"
REFERENCE = ROOT / "data" / "test_south_pole"
SPICE_LOCK = threading.Lock()
SPICE_CACHE: OrderedDict[tuple, dict] = OrderedDict()
SPICE_CACHE_LIMIT = 8

app = FastAPI(title="LUNA SHIFT - Dynamic South Pole Explorer", version="0.5.0")
app.mount("/static", StaticFiles(directory=WEB_DIR), name="static")

# Historical NASA landing catalog for Student mode; separate from polar DEM coverage.
from .education_missions import router as education_router
app.include_router(education_router)


def site_from_query(latitude_deg: float, longitude_deg_east: float, observer_height_m: float):
    try:
        return resolve_site(latitude_deg, longitude_deg_east, observer_height_m)
    except FileNotFoundError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    except (ValueError, OSError, RuntimeError) as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


def profile_for(site):
    try:
        return get_or_compute_horizon(site)
    except (FileNotFoundError, ValueError, OSError, RuntimeError) as error:
        raise HTTPException(status_code=422, detail=f"Horizon calculation failed: {error}") from error


def utc_date(text: str):
    if not (text.endswith("Z") or text.endswith("+00:00") or text.endswith(" UTC")):
        raise HTTPException(422, detail="A UTC timezone suffix is required (Z or +00:00).")
    try:
        return parse_utc(text)
    except ValueError as error:
        raise HTTPException(422, detail=str(error)) from error


def run_spice(start, end, step, horizon_file):
    """Cache repeated UTC/site simulations; avoid recalculating SPICE during playback.

    The key includes the horizon and kernel file signatures, so a changed DEM
    horizon or updated kernel cannot reuse an old result. Requests are still
    serialized because the SpiceyPy kernel pool is process-global.
    """
    missing = [p for p in KERNEL_NAMES if not (KERNELS / p).is_file()]
    if missing or importlib.util.find_spec("spiceypy") is None:
        raise HTTPException(status_code=503, detail=(
            "The JPL SPICE engine is not ready. Install requirements.txt and copy "
            "the five NASA kernels to data/kernels. Missing: " + ", ".join(missing)
        ))
    try:
        source = Path(horizon_file).resolve()
        signature = (
            source.stat().st_size, source.stat().st_mtime_ns,
            tuple((KERNELS / p).stat().st_mtime_ns for p in KERNEL_NAMES),
        )
        key = (start.isoformat(), end.isoformat(), float(step), str(source), signature)
        with SPICE_LOCK:
            if key in SPICE_CACHE:
                SPICE_CACHE.move_to_end(key)
                return SPICE_CACHE[key]
            result = calculate_visibility(
                start.isoformat(), end.isoformat(),
                step_minutes=step, horizon_path=source,
                kernel_dir=KERNELS,
            )
            SPICE_CACHE[key] = result
            while len(SPICE_CACHE) > SPICE_CACHE_LIMIT:
                SPICE_CACHE.popitem(last=False)
            return result
    except (ValueError, RuntimeError, OSError) as error:
        raise HTTPException(status_code=422, detail=f"SPICE simulation failed: {error}") from error


@app.get("/")
def home():
    if (APP_DIST / "index.html").is_file():
        return FileResponse(APP_DIST / "index.html")
    return HTMLResponse('<!doctype html><html lang="en"><meta charset="utf-8"><title>LUNA SHIFT API</title><body style="font-family:system-ui;background:#07111e;color:#e6f6ff;padding:40px"><h1>LUNA SHIFT API is running</h1><p>Start START_WEBSITE.bat and open the <b>Local</b> URL printed by Vite (such as <a style="color:#80dbed" href="http://localhost:5173/">http://localhost:5173/</a>).</p><p>Backend check: <a style="color:#80dbed" href="/api/health">/api/health</a></p></body></html>')


@app.get("/api/health")
def health():
    local, regional = dem_paths_safe()
    return {
        "status": "ok",
        "coverage": "Moon south pole, valid pixels in regional 80 m/pixel LOLA DEM",
        "regional_dem_ready": bool(regional),
        "local_shackleton_dem_ready": bool(local),
        "spice_ready": bool(importlib.util.find_spec("spiceypy")) and all(
            (KERNELS / name).is_file() for name in KERNEL_NAMES
        ),
        "notes": "Preliminary research model; valid terrain coverage is not a safe landing certification.",
    }


def dem_paths_safe():
    try:
        return dem_paths()
    except (FileNotFoundError, ValueError):
        return None, None


# Approximate named craters and location-specific LOLA elevation image crops.
from .polar_craters import catalog as crater_catalog, preview as crater_preview, CRATERS

@app.get('/api/craters')
def list_south_polar_craters():
    try:
        return crater_catalog()
    except (OSError, ValueError, FileNotFoundError) as error:
        raise HTTPException(503, detail=str(error)) from error

@app.get('/api/craters/{crater_id}/preview')
def south_polar_crater_preview(crater_id: str):
    if not any(c['id']==crater_id for c in CRATERS):
        raise HTTPException(404, detail='Unknown lunar crater.')
    try:
        _, path = dem_paths()
        return Response(content=crater_preview(crater_id,(path.stat().st_size,path.stat().st_mtime_ns)),media_type='image/png')
    except (OSError, ValueError, FileNotFoundError) as error:
        raise HTTPException(503, detail=str(error)) from error


@app.get("/api/map/metadata")
def get_map_metadata():
    try:
        return map_metadata()
    except (OSError, ValueError, FileNotFoundError) as error:
        raise HTTPException(503, detail=str(error)) from error


@app.get("/api/map/preview")
def get_map_preview():
    try:
        return Response(content=map_png(), media_type="image/png")
    except (OSError, ValueError, FileNotFoundError) as error:
        raise HTTPException(503, detail=str(error)) from error


@app.get("/api/site")
def get_site(
    latitude_deg: float = Query(..., ge=-90, le=-80),
    longitude_deg_east: float = Query(...),
    observer_height_m: float = Query(1.5, ge=0, le=20),
):
    return site_from_query(latitude_deg, longitude_deg_east, observer_height_m)


@app.get("/api/site/from-map")
def get_site_from_map(x_m: float, y_m: float, observer_height_m: float = 1.5):
    try:
        return latlon_from_regional_xy(x_m, y_m, observer_height_m)
    except FileNotFoundError as error:
        raise HTTPException(503, detail=str(error)) from error
    except (ValueError, OSError, RuntimeError) as error:
        raise HTTPException(422, detail=str(error)) from error


@app.get("/api/horizon")
def get_horizon(
    latitude_deg: float, longitude_deg_east: float,
    observer_height_m: float = 1.5,
):
    site = site_from_query(latitude_deg, longitude_deg_east, observer_height_m)
    data, path = profile_for(site)
    return data


@app.get("/api/terrain")
def get_terrain(
    latitude_deg: float, longitude_deg_east: float,
    observer_height_m: float = 1.5,
):
    site = site_from_query(latitude_deg, longitude_deg_east, observer_height_m)
    try:
        return build_terrain_mesh(site)
    except (ValueError, RuntimeError, OSError) as error:
        raise HTTPException(422, detail=f"Terrain mesh failed: {error}") from error


@app.get("/api/snapshot")
def get_snapshot(
    latitude_deg: float, longitude_deg_east: float,
    observer_height_m: float = 1.5,
    at: str = "2026-11-14T12:00:00Z",
):
    when = utc_date(at)
    site = site_from_query(latitude_deg, longitude_deg_east, observer_height_m)
    _, horizon_file = profile_for(site)
    result = run_spice(when, when + timedelta(minutes=1), 1, horizon_file)
    sample = result["timeline"][0]
    return {
        "date_utc": sample["time_utc"],
        "site": site,
        "source_mode": "dynamic_spice_terrain_visibility",
        "bodies": {"sun": sample["sun"], "earth": sample["earth"]},
        "warnings": result["metadata"]["warnings"],
    }


@app.get("/api/visibility")
def get_visibility(
    latitude_deg: float, longitude_deg_east: float,
    observer_height_m: float = 1.5,
    start: str = "2026-11-14T00:00:00Z",
    end: str = "2026-11-15T00:00:00Z",
    step_minutes: float = Query(15, gt=0, le=1440),
):
    begin, finish = utc_date(start), utc_date(end)
    if finish <= begin:
        raise HTTPException(422, detail="End time must be after start time.")
    if finish - begin > timedelta(days=31):
        raise HTTPException(422, detail="Select a range of 31 days or fewer.")
    if (finish - begin).total_seconds() / (step_minutes * 60) > 3000:
        raise HTTPException(422, detail="Too many time samples; increase the sampling interval.")
    site = site_from_query(latitude_deg, longitude_deg_east, observer_height_m)
    _, horizon_file = profile_for(site)
    return run_spice(begin, finish, step_minutes, horizon_file)


@app.get("/api/compare")
def compare_sites(
    a_latitude_deg: float = Query(..., ge=-90, le=-80),
    a_longitude_deg_east: float = Query(...),
    b_latitude_deg: float = Query(..., ge=-90, le=-80),
    b_longitude_deg_east: float = Query(...),
    a_observer_height_m: float = Query(1.5, ge=0, le=20),
    b_observer_height_m: float = Query(1.5, ge=0, le=20),
    start: str = "2026-11-14T00:00:00Z",
    end: str = "2026-11-15T00:00:00Z",
    step_minutes: float = Query(15, gt=0, le=1440),
):
    """Compare independent terrain-aware Sun/Earth visibility at sites A and B."""
    begin, finish = utc_date(start), utc_date(end)
    if finish <= begin:
        raise HTTPException(422, detail="End time must be after start time.")
    if finish - begin > timedelta(days=31):
        raise HTTPException(422, detail="Select a range of 31 days or fewer.")
    if (finish - begin).total_seconds() / (step_minutes * 60) > 3000:
        raise HTTPException(422, detail="Too many time samples; increase the sampling interval.")

    site_a = site_from_query(a_latitude_deg, a_longitude_deg_east, a_observer_height_m)
    site_b = site_from_query(b_latitude_deg, b_longitude_deg_east, b_observer_height_m)
    if (site_a["latitude_deg"] == site_b["latitude_deg"]
            and site_a["longitude_deg_east"] == site_b["longitude_deg_east"]
            and site_a["observer_height_m"] == site_b["observer_height_m"]):
        raise HTTPException(422, detail="Points A and B must be different observers.")

    profile_a, horizon_a = profile_for(site_a)
    profile_b, horizon_b = profile_for(site_b)
    try:
        check_observer_match(profile_a["metadata"], site_a)
        check_observer_match(profile_b["metadata"], site_b)
    except (KeyError, TypeError, ValueError) as error:
        raise HTTPException(422, detail=f"Horizon observer mismatch: {error}") from error

    result_a = run_spice(begin, finish, step_minutes, horizon_a)
    result_b = run_spice(begin, finish, step_minutes, horizon_b)
    points = {
        "A": site_comparison_metrics(site_a, result_a),
        "B": site_comparison_metrics(site_b, result_b),
    }
    shared = intersect_opportunities(
        result_a["windows"]["both"], result_b["windows"]["both"]
    )
    return {
        "comparison_method": "Body centers above each site's own terrain horizon",
        "start_utc": result_a["metadata"]["start_utc"],
        "end_utc": result_a["metadata"]["end_utc"],
        "step_minutes": step_minutes,
        "points": points,
        "shared_opportunity": shared,
        "warnings": result_a["metadata"]["warnings"],
    }


@app.get("/api/reference/test-south-pole")
def engineering_reference():
    return {
        "site_id": "test_south_pole",
        "can_merge_with_shackleton": False,
        "note": "The historical engineering Horizons series uses a different observer. "
                "It is retained solely for cross-checks and is not used by dynamic site selection.",
    }


class MissionEvaluationRequest(BaseModel):
    latitude_deg: float = Field(ge=-90, le=-80)
    longitude_deg_east: float
    observer_height_m: float = Field(default=1.5, ge=0, le=20)
    analysis_start: str
    analysis_end: str
    operation_start: str
    duration_hours: float = Field(default=2.0, ge=0.25, le=24)
    delay_hours: float = Field(default=12.0, ge=0, le=72)
    step_minutes: float = Field(default=15, gt=0, le=1440)


@app.post('/api/mission/evaluate')
def evaluate_mission(request: MissionEvaluationRequest):
    """Evaluate one selected site with the existing LOLA/SPICE visibility engine."""
    begin, finish = utc_date(request.analysis_start), utc_date(request.analysis_end)
    utc_date(request.operation_start)
    if finish <= begin or finish - begin > timedelta(days=31):
        raise HTTPException(422, detail='Select an analysis interval between 0 and 31 days.')
    if (finish - begin).total_seconds() / (request.step_minutes * 60) > 3000:
        raise HTTPException(422, detail='Too many samples; increase the sampling interval.')
    site = site_from_query(request.latitude_deg, request.longitude_deg_east, request.observer_height_m)
    _, horizon_file = profile_for(site)
    result = run_spice(begin, finish, request.step_minutes, horizon_file)
    try:
        assessment = evaluate_mission_windows(
            analysis_start=request.analysis_start,
            analysis_end=request.analysis_end,
            operation_start=request.operation_start,
            duration_hours=request.duration_hours,
            delay_hours=request.delay_hours,
            windows=result['windows']['both'],
        )
    except ValueError as error:
        raise HTTPException(422, detail=str(error)) from error
    return {
        **assessment,
        'site': site,
        'sun_visible_hours': result['summary']['sun']['visible_hours'],
        'earth_visible_hours': result['summary']['earth']['visible_hours'],
        'overlap_hours': result['summary']['both']['visible_hours'],
        'warnings': result['metadata']['warnings'],
    }


@app.get('/api/reference/shackleton/summary')
def supplied_shackleton_summary():
    """Uploaded, fixed-location scientific reference, NOT an A/B calculation."""
    import json
    path = ROOT / 'data' / 'reference' / 'shackleton' / 'visibility_results.json'
    if not path.is_file():
        raise HTTPException(status_code=404, detail='Reference file is missing.')
    data = json.loads(path.read_text(encoding='utf-8'))
    meta = data['metadata']
    return {'kind':'static_research_reference', 'site_name': meta['site_name'],
        'site_latitude_deg': meta['site_latitude_deg'],
        'site_longitude_deg_east': meta['site_longitude_deg_east'],
        'start_utc': meta['start_utc'], 'end_utc': meta['end_utc'],
        'step_minutes': meta['step_minutes'], 'summary': data['summary'],
        'warnings': meta.get('warnings',[]),
        'note':'These values apply ONLY to this particular Shackleton observer and interval; dynamic A/B results come from /api/visibility and /api/compare.'}


@app.get("/api/orbits")
def get_orbits(date: str = Query(..., description="UTC date in YYYY-MM-DD format")):
    """NASA/JPL DE440 geometric positions and orbital path samples.

    The shared lock prevents kernel-pool races with Sun/Earth visibility requests.
    This endpoint does not compute, alter, or cache any landing-site horizons.
    """
    if importlib.util.find_spec("spiceypy") is None:
        raise HTTPException(503, detail="SPICE is not installed on the server.")
    try:
        with SPICE_LOCK:
            return calculate_orbit_ephemeris(date, KERNELS)
    except FileNotFoundError as error:
        raise HTTPException(503, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(422, detail=str(error)) from error
    except Exception as error:
        # Includes SpiceyError for dates outside DE440 kernel coverage.
        raise HTTPException(422, detail=f"NASA DE440 orbit lookup failed: {error}") from error


@app.get('/{asset_path:path}')
def react_site_asset(asset_path: str):
    """Serve Daniela's built React site from FastAPI after npm run build."""
    if not (APP_DIST / 'index.html').is_file():
        raise HTTPException(404, detail='Build the React site or open http://localhost:5173 in development.')
    root = APP_DIST.resolve()
    target = (APP_DIST / asset_path).resolve()
    if target.is_relative_to(root) and target.is_file():
        return FileResponse(target)
    if asset_path.startswith('api/'):
        raise HTTPException(404, detail='Unknown API route.')
    return FileResponse(APP_DIST / 'index.html')


