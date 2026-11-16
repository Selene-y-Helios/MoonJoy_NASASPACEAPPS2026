"""Generate a local first-person NASA LOLA terrain mesh for Three.js.

Usage from the project root:
    python backend/export_terrain.py

The exact original NASA Site04 DEM must first be copied to data/dem/.
"""
import json
import math
from pathlib import Path

import numpy as np
import rasterio
from pyproj import CRS, Transformer
from rasterio.enums import Resampling
from rasterio.windows import Window

ROOT = Path(__file__).resolve().parents[1]
DEM = ROOT / "data" / "dem" / "Site04_final_adj_5mpp_surf.tif"
PROFILE = ROOT / "data" / "shackleton" / "horizon_profile.json"
OUTPUT = ROOT / "data" / "shackleton" / "terrain_mesh.json"
SIZE_M = 3000.0
MAX_RES = 140


def main():
    if not DEM.is_file():
        raise FileNotFoundError(f"NASA Site04 DEM missing: {DEM}")
    meta = json.loads(PROFILE.read_text(encoding="utf-8"))["metadata"]
    x0, y0 = float(meta["site_x_m"]), float(meta["site_y_m"])
    radius = float(meta["moon_reference_radius_m"])
    site_elevation = float(meta["dem_elevation_m"])

    with rasterio.open(DEM) as src:
        if not src.crs:
            raise ValueError("NASA DEM CRS is missing.")
        expected_crs = meta.get("local_crs_wkt")
        if expected_crs and not CRS.from_user_input(expected_crs).equals(CRS.from_wkt(src.crs.to_wkt()), ignore_axis_order=True):
            raise ValueError("Local DEM CRS differs from the profile's original DEM CRS.")
        row, col = src.index(x0, y0)
        if not (0 <= row < src.height and 0 <= col < src.width):
            raise ValueError("Horizon observer is outside the local DEM.")
        test = src.read(1, window=Window(col, row, 1, 1), masked=True)
        if np.ma.is_masked(test[0, 0]) or abs(float(test[0, 0]) - site_elevation) > 0.2:
            raise ValueError("DEM elevation at the observer does not match the horizon profile.")
        half_rows = max(1, int((SIZE_M / 2) / abs(src.transform.e)))
        half_cols = max(1, int((SIZE_M / 2) / abs(src.transform.a)))
        row_min, row_max = max(0, row-half_rows), min(src.height, row+half_rows+1)
        col_min, col_max = max(0, col-half_cols), min(src.width, col+half_cols+1)
        window = Window(col_min, row_min, col_max-col_min, row_max-row_min)
        rows = min(MAX_RES, int(window.height))
        cols = min(MAX_RES, int(window.width))
        masked = src.read(1, window=window, out_shape=(rows, cols), masked=True, resampling=Resampling.nearest)
        heights = np.asarray(masked.filled(np.nan), dtype=np.float64)
        sample_transform = src.window_transform(window) * rasterio.Affine.scale(window.width/cols, window.height/rows)
        pixel_cols, pixel_rows = np.meshgrid(np.arange(cols)+0.5, np.arange(rows)+0.5)
        xs = sample_transform.c + sample_transform.a * pixel_cols
        ys = sample_transform.f + sample_transform.e * pixel_rows
        crs = CRS.from_wkt(src.crs.to_wkt())
        transformer = Transformer.from_crs(crs, crs.geodetic_crs, always_xy=True)
        longs, lats = transformer.transform(xs, ys)

    lat0 = math.radians(float(meta["latitude_deg"]))
    lon0 = math.radians(float(meta["longitude_deg_east"]))
    u = np.array([math.cos(lat0)*math.cos(lon0), math.cos(lat0)*math.sin(lon0), math.sin(lat0)])
    e = np.array([-math.sin(lon0), math.cos(lon0), 0.0])
    n = np.cross(u, e)
    observer = (radius + site_elevation) * u

    latr, lonr = np.deg2rad(lats), np.deg2rad(longs)
    rr = radius + heights
    x = rr * np.cos(latr) * np.cos(lonr)
    y = rr * np.cos(latr) * np.sin(lonr)
    z = rr * np.sin(latr)
    difference = np.stack((x, y, z), axis=-1) - observer
    local_e = difference @ e
    local_u = difference @ u
    local_n = difference @ n

    positions = []
    lookup = np.full((rows, cols), -1, dtype=int)
    for r in range(rows):
        for c in range(cols):
            if np.isfinite(heights[r,c]):
                lookup[r,c] = len(positions)//3
                # Right-handed scene: +X=East, +Y=Up, -Z=North.
                positions.extend([round(float(local_e[r,c]), 3), round(float(local_u[r,c]), 3), round(float(-local_n[r,c]), 3)])
    indices = []
    for r in range(rows-1):
        for c in range(cols-1):
            a,b,d,f = lookup[r,c],lookup[r,c+1],lookup[r+1,c],lookup[r+1,c+1]
            if min(a,b,d,f) >= 0:
                indices.extend((int(a),int(d),int(b),int(b),int(d),int(f)))
    if not indices:
        raise RuntimeError("No valid surface mesh triangles were generated.")
    OUTPUT.write_text(json.dumps({
        "site_id": "shackleton",
        "source": "NASA LOLA Site04 5 m/pixel DEM, resampled for visualization",
        "reference": "Local tangent coordinates; +X East, +Y Up, -Z North; meters",
        "observer_at": [0.0, float(meta["observer_height_m"]), 0.0],
        "rows": rows,
        "columns": cols,
        "positions": positions,
        "indices": indices,
        "limitations": ["Terrain extends only around the landing site.", "Terrain shadows are a rendering aid, not the far-horizon visibility algorithm."]
    }, separators=(",", ":")), encoding="utf-8")
    print(f"NASA terrain mesh generated: {OUTPUT}")
    print(f"Mesh vertices: {len(positions)//3}; faces: {len(indices)//3}")


if __name__ == "__main__":
    main()
