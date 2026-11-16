"""NASA LOLA site selection, per-site horizon calculation, and local terrain mesh.

All output fields, warnings, and code identifiers are in English.
This module contains no invented fallback terrain values.
"""
from __future__ import annotations

import hashlib
import io
import json
import math
import threading
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path

import numpy as np
import rasterio
from PIL import Image
from pyproj import CRS, Transformer
from rasterio.enums import Resampling
from rasterio.windows import Window

from .compute_horizon import read_subset, lookup_nearest, radial_distances, unit_basis

ROOT = Path(__file__).resolve().parents[1]
DEM_DIR = ROOT / "data" / "dem"
CACHE_DIR = ROOT / "data" / "cache" / "horizons"
MOON_RADIUS_M = 1_737_400.0
MAX_SEARCH_KM = 120.0
AZIMUTH_STEP_DEG = 1.0
CACHE_VERSION = "dynamic-site-horizon-v1"
CACHE_LOCK = threading.Lock()


def find_dem(stem: str, required: bool = True) -> Path | None:
    if DEM_DIR.is_dir():
        candidates = sorted(
            p for p in DEM_DIR.iterdir()
            if p.is_file() and p.stem.casefold() == stem.casefold()
            and p.suffix.casefold() in {".tif", ".tiff"}
        )
    else:
        candidates = []
    if len(candidates) > 1:
        raise ValueError(f"Multiple files match {stem}; keep only one TIFF file.")
    if not candidates and required:
        raise FileNotFoundError(
            f"Missing NASA LOLA DEM: {stem}.tif/.tiff in {DEM_DIR}. "
            "The regional 80 m/pixel DEM is required for dynamic site selection."
        )
    return candidates[0] if candidates else None


def dem_paths():
    return find_dem("Site04_final_adj_5mpp_surf", required=False), find_dem("LDEM_80S_80MPP_ADJ")


def _check_spheres(local_crs, regional_crs):
    for crs in (local_crs, regional_crs):
        ellipsoid = crs.geodetic_crs.ellipsoid
        if abs(ellipsoid.semi_major_metre - MOON_RADIUS_M) > 0.01 or abs(ellipsoid.semi_minor_metre - MOON_RADIUS_M) > 0.01:
            raise ValueError("DEM is not in the expected lunar sphere of radius 1,737,400 m.")
    # Identical sphere radius does not certify the same body-fixed frame and vertical datum.


def _project_to(crs, lat_deg, lon_deg):
    transformer = Transformer.from_crs(crs.geodetic_crs, crs, always_xy=True)
    return transformer.transform(lon_deg, lat_deg)


def _site_sample(src, lat_deg, lon_deg):
    x, y = _project_to(CRS.from_wkt(src.crs.to_wkt()), lat_deg, lon_deg)
    if not (src.bounds.left <= x < src.bounds.right and src.bounds.bottom < y <= src.bounds.top):
        return None
    row, col = src.index(x, y)
    if not (0 <= row < src.height and 0 <= col < src.width):
        return None
    pixel = src.read(1, window=Window(col, row, 1, 1), masked=True)[0, 0]
    if np.ma.is_masked(pixel) or not math.isfinite(float(pixel)):
        return None
    return {"x_m": float(x), "y_m": float(y), "elevation_m": float(pixel), "resolution_m": max(map(abs, src.res))}


def resolve_site(lat_deg: float, lon_deg: float, observer_height_m: float = 1.5) -> dict:
    lat_deg = float(lat_deg)
    lon_deg = float(lon_deg) % 360.0
    observer_height_m = float(observer_height_m)
    if not all(map(math.isfinite, (lat_deg, lon_deg, observer_height_m))):
        raise ValueError("Site coordinates and observer height must be finite numbers.")
    if not (-90 <= lat_deg <= -80):
        raise ValueError("This prototype only supports the Moon's south polar DEM coverage, from 90 S to 80 S.")
    if not (0 <= observer_height_m <= 20):
        raise ValueError("Observer height must be between 0 and 20 meters.")

    local_path, regional_path = dem_paths()
    with rasterio.open(regional_path) as regional:
        if regional.crs is None:
            raise ValueError("Regional DEM is missing its lunar CRS.")
        r_crs = CRS.from_wkt(regional.crs.to_wkt())
        _check_spheres(r_crs, r_crs)
        regional_sample = _site_sample(regional, lat_deg, lon_deg)
    if regional_sample is None:
        raise ValueError("The selected coordinate has no valid regional NASA LOLA elevation data.")
    selected = regional_sample
    source_name = regional_path.name
    if local_path:
        with rasterio.open(local_path) as local:
            if local.crs is None:
                raise ValueError("Local DEM is missing its lunar CRS.")
            _check_spheres(CRS.from_wkt(local.crs.to_wkt()), r_crs)
            local_sample = _site_sample(local, lat_deg, lon_deg)
            if local_sample is not None:
                selected = local_sample
                source_name = local_path.name
    return {
        "name": "Lunar South Pole - Selected Coordinate",
        "latitude_deg": round(lat_deg, 8),
        "longitude_deg_east": round(lon_deg, 8),
        "observer_height_m": round(observer_height_m, 3),
        "dem_elevation_m": selected["elevation_m"],
        "site_x_m": selected["x_m"],
        "site_y_m": selected["y_m"],
        "map_x_m": regional_sample["x_m"],
        "map_y_m": regional_sample["y_m"],
        "elevation_dem": source_name,
        "terrain_resolution_m": selected["resolution_m"],
        "local_regional_elevation_difference_m": (
            round(float(local_sample["elevation_m"] - regional_sample["elevation_m"]), 3)
            if local_path and "Site04" in source_name else None
        ),
        "data_status": "preliminary",
    }


def latlon_from_regional_xy(x_m: float, y_m: float, observer_height_m: float = 1.5) -> dict:
    _, regional_path = dem_paths()
    with rasterio.open(regional_path) as src:
        if src.crs is None:
            raise ValueError("Regional DEM has no CRS.")
        to_geographic = Transformer.from_crs(
            CRS.from_wkt(src.crs.to_wkt()), CRS.from_wkt(src.crs.to_wkt()).geodetic_crs,
            always_xy=True,
        )
        lon, lat = to_geographic.transform(x_m, y_m)
    return resolve_site(float(lat), float(lon), observer_height_m)


def map_metadata():
    _, path = dem_paths()
    with rasterio.open(path) as src:
        return {"source": path.name, "bounds_projected_m": {
            "left": src.bounds.left, "bottom": src.bounds.bottom,
            "right": src.bounds.right, "top": src.bounds.top,
        }, "width": src.width, "height": src.height,
            "projection": "Lunar south polar stereographic", "url": "/api/map/preview"}


@lru_cache(maxsize=2)
def map_png() -> bytes:
    _, path = dem_paths()
    with rasterio.open(path) as src:
        width, height = 800, 800
        grid = src.read(1, out_shape=(height, width), masked=True, resampling=Resampling.nearest)
    values = np.ma.filled(grid.astype(float), np.nan)
    valid = np.isfinite(values)
    if not valid.any():
        raise ValueError("The regional DEM has no valid pixels to preview.")
    lo, hi = np.percentile(values[valid], [2, 98])
    normalized = np.clip((values - lo) / max(hi - lo, 1.0), 0, 1)
    # Neutral monochrome height shading; it is a DEM preview, not optical imagery.
    gray = np.nan_to_num(0.12 + normalized * 0.83, nan=0)
    rgba = np.zeros((height, width, 4), dtype=np.uint8)
    rgba[:, :, :3] = (gray[:, :, None] * 255).astype(np.uint8)
    rgba[:, :, 3] = np.where(valid, 255, 0).astype(np.uint8)
    buffer = io.BytesIO()
    Image.fromarray(rgba, mode="RGBA").save(buffer, format="PNG")
    return buffer.getvalue()


def _cache_key(site: dict, paths: tuple[Path | None, Path]):
    key_parts = [CACHE_VERSION, site["latitude_deg"], site["longitude_deg_east"],
                 site["observer_height_m"], MAX_SEARCH_KM, AZIMUTH_STEP_DEG]
    for p in paths:
        key_parts.append((str(p), p.stat().st_size, p.stat().st_mtime_ns) if p else None)
    return hashlib.sha256(json.dumps(key_parts, sort_keys=True).encode()).hexdigest()[:20]


def horizon_cache_file(site: dict):
    return CACHE_DIR / ("horizon_" + _cache_key(site, dem_paths()) + ".json")


def compute_horizon(site: dict) -> dict:
    """Calculate the site-specific sampled terrain horizon with lunar curvature."""
    local_path, regional_path = dem_paths()
    lat0, lon0 = site["latitude_deg"], site["longitude_deg_east"]
    elev0, obs_h = site["dem_elevation_m"], site["observer_height_m"]

    with rasterio.open(regional_path) as src:
        regional_crs = CRS.from_wkt(src.crs.to_wkt())
    local_crs = None
    if local_path:
        with rasterio.open(local_path) as src:
            local_crs = CRS.from_wkt(src.crs.to_wkt())
            _check_spheres(local_crs, regional_crs)
    _check_spheres(regional_crs, regional_crs)

    to_regional = Transformer.from_crs(regional_crs.geodetic_crs, regional_crs, always_xy=True)
    x0, y0 = to_regional.transform(lon0, lat0)
    regional = read_subset(regional_path, x0, y0, MAX_SEARCH_KM * 1100 + 1000)
    if regional is None:
        raise ValueError("Regional NASA DEM does not cover the selected horizon.")

    local = None
    if local_crs is not None:
        to_local = Transformer.from_crs(local_crs.geodetic_crs, local_crs, always_xy=True)
        lx, ly = to_local.transform(lon0, lat0)
        local = read_subset(local_path, lx, ly, 7000)

    up, east, north = unit_basis(lat0, lon0)
    observer = (MOON_RADIUS_M + elev0 + obs_h) * up
    azimuths = np.arange(0, 360, AZIMUTH_STEP_DEG, dtype=float)
    distances = radial_distances(MAX_SEARCH_KM * 1000)
    delta = distances / MOON_RADIUS_M
    # Shape: [azimuth, radial distance].
    a = np.deg2rad(azimuths)[:, None, None]
    directions = np.cos(a) * north + np.sin(a) * east
    unit_points = np.cos(delta)[None, :, None] * up + np.sin(delta)[None, :, None] * directions
    lat_grid = np.degrees(np.arcsin(np.clip(unit_points[..., 2], -1, 1)))
    lon_grid = np.degrees(np.arctan2(unit_points[..., 1], unit_points[..., 0]))
    rx, ry = to_regional.transform(lon_grid, lat_grid)
    heights = lookup_nearest(*regional, rx, ry)
    if local is not None:
        lx, ly = to_local.transform(lon_grid, lat_grid)
        local_heights = lookup_nearest(*local, lx, ly)
        heights = np.where(np.isfinite(local_heights), local_heights, heights)
    valid = np.isfinite(heights)
    targets = unit_points * (MOON_RADIUS_M + np.where(valid, heights, 0))[:, :, None]
    look = targets - observer
    vertical = np.einsum("ijk,k->ij", look, up)
    lateral = np.linalg.norm(look - vertical[:, :, None] * up, axis=-1)
    angles = np.degrees(np.arctan2(vertical, lateral))
    angles[~valid] = -np.inf
    best = np.argmax(angles, axis=1)
    max_angles = angles[np.arange(len(best)), best]
    missing_fraction = 1 - np.mean(valid, axis=1)
    results = []
    for i, azimuth in enumerate(azimuths):
        ok = bool(valid[i].any())
        results.append({
            "azimuth_deg": float(azimuth),
            "horizon_elevation_deg": float(max_angles[i]) if ok else None,
            "obstacle_distance_m": float(distances[best[i]]) if ok else None,
            "missing_sample_fraction": round(float(missing_fraction[i]), 5),
        })
    return {"metadata": {
        "product": "Lunar terrain horizon profile",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "site_name": site["name"],
        "latitude_deg": lat0, "longitude_deg_east": lon0,
        "site_x_m": site["site_x_m"], "site_y_m": site["site_y_m"],
        "dem_elevation_m": elev0, "observer_height_m": obs_h,
        "moon_reference_radius_m": MOON_RADIUS_M,
        "horizon_reference": "Local spherical tangent plane",
        "azimuth_convention": "0=north, 90=east, clockwise",
        "maximum_search_distance_km": MAX_SEARCH_KM,
        "azimuth_step_deg": AZIMUTH_STEP_DEG,
        "local_dem": str(local_path) if local_path else None,
        "regional_dem": str(regional_path),
        "method": "Spherical curvature; radial nearest-neighbor LOLA DEM sampling",
        "limitations": [
            "Not mission-qualified; no source DEM/frame or vertical datum cross-validation.",
            "Missing terrain samples are unknown, not clear sky.",
            "Small obstacles can be missed by DEM resolution and sampling step.",
            "Terrain beyond the 120 km search radius is not included.",
        ],
    }, "samples": results}


def get_or_compute_horizon(site: dict) -> tuple[dict, Path]:
    path = horizon_cache_file(site)
    if path.is_file():
        return json.loads(path.read_text(encoding="utf-8")), path
    with CACHE_LOCK:
        # Another request may have finished calculating this site while waiting.
        if path.is_file():
            return json.loads(path.read_text(encoding="utf-8")), path
        data = compute_horizon(site)
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        # Cache by coordinate and input DEM fingerprint, never mix different observers.
        pending = path.with_suffix(".tmp")
        pending.write_text(json.dumps(data, allow_nan=False), encoding="utf-8")
        pending.replace(path)
        return data, path


def build_terrain_mesh(site: dict, width_m: float = 1800.0, max_resolution: int = 155) -> dict:
    """Export a true elevation mesh near the selected coordinate; no synthetic fills."""
    local_path, regional_path = dem_paths()
    selected_file = local_path if local_path and site["elevation_dem"] == local_path.name else regional_path
    with rasterio.open(selected_file) as src:
        site_x, site_y = _project_to(
            CRS.from_wkt(src.crs.to_wkt()), site["latitude_deg"], site["longitude_deg_east"]
        )
        row, col = src.index(site_x, site_y)
        half_cols = max(1, int((width_m / 2) / abs(src.transform.a)))
        half_rows = max(1, int((width_m / 2) / abs(src.transform.e)))
        r0, r1 = max(0, row-half_rows), min(src.height, row+half_rows+1)
        c0, c1 = max(0, col-half_cols), min(src.width, col+half_cols+1)
        window = Window(c0, r0, c1-c0, r1-r0)
        rows, cols = min(max_resolution, int(window.height)), min(max_resolution, int(window.width))
        if rows < 2 or cols < 2:
            raise ValueError("Insufficient elevation cells for a 3D terrain mesh.")
        grid = src.read(1, window=window, out_shape=(rows, cols), masked=True,
                        resampling=Resampling.nearest)
        heights = np.ma.filled(grid.astype(np.float64), np.nan)
        sampling = src.window_transform(window) * rasterio.Affine.scale(window.width/cols, window.height/rows)
        cgrid, rgrid = np.meshgrid(np.arange(cols)+0.5, np.arange(rows)+0.5)
        xs = sampling.c + sampling.a*cgrid
        ys = sampling.f + sampling.e*rgrid
        pcrs = CRS.from_wkt(src.crs.to_wkt())
        to_geo = Transformer.from_crs(pcrs, pcrs.geodetic_crs, always_xy=True)
        lons, lats = to_geo.transform(xs, ys)
    up, east, north = unit_basis(site["latitude_deg"], site["longitude_deg_east"])
    p0 = (MOON_RADIUS_M + site["dem_elevation_m"]) * up
    lat, lon = np.deg2rad(lats), np.deg2rad(lons)
    r = MOON_RADIUS_M + np.where(np.isfinite(heights), heights, 0)
    xyz = r[:, :, None] * np.stack([
        np.cos(lat)*np.cos(lon), np.cos(lat)*np.sin(lon), np.sin(lat)
    ], axis=-1)
    difference = xyz - p0
    # +X east, +Y up, -Z north.
    xx = np.einsum("ijk,k->ij", difference, east)
    yy = np.einsum("ijk,k->ij", difference, up)
    zz = -np.einsum("ijk,k->ij", difference, north)
    vertices, indices = [], []
    lookup = np.full((rows, cols), -1, dtype=int)
    for row in range(rows):
        for col in range(cols):
            if np.isfinite(heights[row, col]):
                lookup[row, col] = len(vertices)//3
                vertices += [round(float(xx[row,col]), 3), round(float(yy[row,col]), 3), round(float(zz[row,col]), 3)]
    for row in range(rows-1):
        for col in range(cols-1):
            a,b,c,d = lookup[row,col],lookup[row,col+1],lookup[row+1,col],lookup[row+1,col+1]
            if min(a,b,c)>=0: indices.extend([int(a),int(b),int(c)])
            if min(b,c,d)>=0: indices.extend([int(b),int(d),int(c)])
    return {"metadata": {
        "site_latitude_deg": site["latitude_deg"],
        "site_longitude_deg_east": site["longitude_deg_east"],
        "site_elevation_m": site["dem_elevation_m"],
        "observer_height_m": site["observer_height_m"],
        "dem_source": selected_file.name,
        "dem_resolution_m": site["terrain_resolution_m"],
        "mesh_width_m": width_m,
        "valid_vertices": len(vertices)//3,
    }, "positions": vertices, "indices": indices}
