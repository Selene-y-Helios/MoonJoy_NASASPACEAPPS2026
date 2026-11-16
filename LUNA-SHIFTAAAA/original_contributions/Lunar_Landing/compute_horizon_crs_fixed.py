"""Compute a terrain-aware lunar horizon profile from NASA LOLA GeoTIFFs.

This is a DEM-sampled geometric approximation, not a validated mission product.
All angles are with respect to the spherical local level at the observer.
"""

import argparse
import json
import math
from datetime import datetime, timezone
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import rasterio
from pyproj import CRS, Transformer
from rasterio.windows import Window, from_bounds

MOON_RADIUS_M = 1_737_400.0
DEFAULT_LOCAL = "data/dem/Site04_final_adj_5mpp_surf.tif"
DEFAULT_REGIONAL = "data/dem/LDEM_80S_80MPP_ADJ.TIF"


def unit_basis(latitude_deg, longitude_deg):
    lat = np.deg2rad(latitude_deg)
    lon = np.deg2rad(longitude_deg)
    up = np.array([np.cos(lat) * np.cos(lon),
                   np.cos(lat) * np.sin(lon), np.sin(lat)])
    east = np.array([-np.sin(lon), np.cos(lon), 0.0])
    north = np.array([-np.sin(lat) * np.cos(lon),
                      -np.sin(lat) * np.sin(lon), np.cos(lat)])
    return up, east, north


def read_raster_window(path, bounding_box):
    """Read a clipped raster window; use NaN for missing pixels."""
    with rasterio.open(path) as src:
        window = from_bounds(*bounding_box, transform=src.transform)
        window = window.round_offsets().round_lengths()
        raster_bounds = Window(0, 0, src.width, src.height)
        window = window.intersection(raster_bounds)
        values = src.read(1, window=window, masked=True)
        values = np.asarray(values.astype(np.float64).filled(np.nan), dtype=np.float64)
        return values, src.window_transform(window)


def read_subset(path, px, py, radius_m):
    """Read an approximately square area around a projected site position."""
    with rasterio.open(path) as src:
        bbox = (max(src.bounds.left, px - radius_m),
                max(src.bounds.bottom, py - radius_m),
                min(src.bounds.right, px + radius_m),
                min(src.bounds.top, py + radius_m))
        if bbox[0] >= bbox[2] or bbox[1] >= bbox[3]:
            return None
    return read_raster_window(path, bbox)


def lookup_nearest(data, affine, xs, ys):
    """Vectorized nearest-grid-cell sampling; out-of-bounds pixels remain NaN."""
    output = np.full(xs.shape, np.nan, dtype=np.float64)
    inv = ~affine
    cols_float, rows_float = inv * (xs, ys)
    cols = np.floor(cols_float).astype(np.int64)
    rows = np.floor(rows_float).astype(np.int64)
    ok = (rows >= 0) & (rows < data.shape[0]) & (cols >= 0) & (cols < data.shape[1])
    output[ok] = data[rows[ok], cols[ok]]
    return output


def radial_distances(max_distance_m):
    """Use denser samples near the landing site."""
    segments = [(20.0, min(5_000.0, max_distance_m), 20.0),
                (5_000.0, min(20_000.0, max_distance_m), 80.0),
                (20_000.0, max_distance_m, 250.0)]
    vectors = [np.arange(start, stop + 0.1, step)
               for start, stop, step in segments if stop >= start]
    if not vectors:
        raise ValueError("Maximum distance must be at least 20 meters.")
    return np.unique(np.concatenate(vectors))


def main():
    parser = argparse.ArgumentParser(description="NASA LOLA 360-degree lunar horizon")
    parser.add_argument("--site", default="lunar_site.json")
    parser.add_argument("--local", default=DEFAULT_LOCAL)
    parser.add_argument("--regional", default=DEFAULT_REGIONAL)
    parser.add_argument("--output", default="horizon_profile.json")
    parser.add_argument("--max-distance-km", type=float, default=120.0)
    parser.add_argument("--azimuth-step-deg", type=float, default=1.0)
    parser.add_argument("--observer-height-m", type=float, default=1.5)
    args = parser.parse_args()

    site_path = Path(args.site)
    if not site_path.exists() and args.site == "lunar_site.json":
        site_path = Path("sitio_lunar.json")
    local_path = Path(args.local)
    regional_path = Path(args.regional)
    for item in [site_path, local_path, regional_path]:
        if not item.is_file():
            raise FileNotFoundError(f"Required input file not found: {item}")
    if not 0 < args.azimuth_step_deg <= 10:
        raise ValueError("Azimuth step must be greater than 0 and at most 10 degrees.")
    if not 0 < args.max_distance_km <= 180:
        raise ValueError("Maximum distance must be between 0 and 180 km.")
    if args.observer_height_m < 0:
        raise ValueError("Observer height must not be negative.")

    site = json.loads(site_path.read_text(encoding="utf-8"))
    site_x, site_y = float(site["x_m"]), float(site["y_m"])

    with rasterio.open(local_path) as local, rasterio.open(regional_path) as regional:
        if not local.crs or not regional.crs:
            raise ValueError("Both NASA DEM files must include coordinate reference systems.")
        local_crs = CRS.from_wkt(local.crs.to_wkt())
        regional_crs = CRS.from_wkt(regional.crs.to_wkt())
        # Different projected CRS definitions can represent the same lunar body.
        # Never sample the regional DEM using projected local-DEM coordinates.
        local_geodetic = local_crs.geodetic_crs
        regional_geodetic = regional_crs.geodetic_crs
        if local_geodetic is None or regional_geodetic is None:
            raise ValueError("A DEM is missing its lunar geographic coordinate system.")
        local_ellipsoid = local_geodetic.ellipsoid
        regional_ellipsoid = regional_geodetic.ellipsoid
        if (abs(local_ellipsoid.semi_major_metre - regional_ellipsoid.semi_major_metre) > 0.01
                or abs(local_ellipsoid.semi_minor_metre - regional_ellipsoid.semi_minor_metre) > 0.01):
            raise ValueError(
                "DEM lunar reference spheroids differ. Verify the source metadata before combining them."
            )
        print("Local DEM CRS:", local.crs)
        print("Regional DEM CRS:", regional.crs)
        if not local_crs.equals(regional_crs, ignore_axis_order=True):
            print("NOTICE: Projected CRSs differ; each DEM will be sampled in its own projection.")
        print("CHECK: Confirm both DEMs use the same lunar body-fixed reference frame and vertical datum.")
        if site.get("crs"):
            site_crs = CRS.from_user_input(site["crs"])
            if not site_crs.equals(local_crs, ignore_axis_order=True):
                raise ValueError("Site JSON CRS does not match the DEM CRS.")
        if not (local.bounds.left <= site_x < local.bounds.right and
                local.bounds.bottom < site_y <= local.bounds.top):
            raise ValueError("Selected observer is outside the local Shackleton DEM.")
        row, col = local.index(site_x, site_y)
        value = local.read(1, window=Window(col, row, 1, 1), masked=True)
        if np.ma.is_masked(value[0, 0]):
            raise ValueError("Observer position has no valid NASA elevation measurement.")
        elevation_m = float(value[0, 0])
        geodetic = local_crs.geodetic_crs
        if geodetic is None:
            raise ValueError("Could not determine the DEM's lunar geodetic CRS.")
        radius = geodetic.ellipsoid.semi_major_metre
        if abs(radius - MOON_RADIUS_M) > 1000:
            raise ValueError(f"Unexpected DEM projection radius: {radius:.2f} m")

    lonlat = Transformer.from_crs(local_crs, geodetic, always_xy=True)
    to_local_xy = Transformer.from_crs(geodetic, local_crs, always_xy=True)
    to_regional_xy = Transformer.from_crs(geodetic, regional_crs, always_xy=True)
    lon0, lat0 = lonlat.transform(site_x, site_y)
    regional_site_x, regional_site_y = to_regional_xy.transform(lon0, lat0)
    if not np.all(np.isfinite([lon0, lat0, elevation_m])):
        raise ValueError("Invalid lunar observer coordinates.")

    # A projected radius slightly exceeds a true geodesic radius at these latitudes.
    # Buffer is in projected metres, not guaranteed geodesic metres;
    # this padding is practical for near-polar south-pole projections.
    regional = read_subset(regional_path, regional_site_x, regional_site_y,
                           args.max_distance_km * 1000 * 1.10 + 1000)
    local = read_subset(local_path, site_x, site_y,
                        min(7_000, args.max_distance_km * 1000 + 1000))
    if regional is None or local is None:
        raise ValueError("Insufficient DEM coverage around the observer.")

    up, east, north = unit_basis(lat0, lon0)
    observer = (MOON_RADIUS_M + elevation_m + args.observer_height_m) * up
    azimuths = np.arange(0, 360, args.azimuth_step_deg, dtype=np.float64)
    distances = radial_distances(args.max_distance_km * 1000)
    delta = distances / MOON_RADIUS_M

    angles = []
    maximum_obstacles = []
    missing_fraction = []
    missing_azimuths = []
    print(f"Site: {lat0:.6f} deg latitude, {lon0 % 360:.6f} deg east longitude")
    print(f"Observer DEM elevation: {elevation_m:.2f} m")
    print(f"Computing {len(azimuths)} azimuth directions...")

    for azimuth_deg in azimuths:
        az = math.radians(float(azimuth_deg))
        horizontal = math.cos(az) * north + math.sin(az) * east
        unit_points = (np.cos(delta)[:, None] * up[None, :]
                       + np.sin(delta)[:, None] * horizontal[None, :])
        target_lat = np.degrees(np.arcsin(np.clip(unit_points[:, 2], -1, 1)))
        target_lon = np.degrees(np.arctan2(unit_points[:, 1], unit_points[:, 0]))
        regional_x, regional_y = to_regional_xy.transform(target_lon, target_lat)
        local_x, local_y = to_local_xy.transform(target_lon, target_lat)

        height = lookup_nearest(*regional, regional_x, regional_y)
        local_height = lookup_nearest(*local, local_x, local_y)
        use_local = np.isfinite(local_height)
        height[use_local] = local_height[use_local]
        valid = np.isfinite(height)
        missing_fraction.append(float(1.0 - np.mean(valid)))
        if not np.any(valid):
            angles.append(None)
            maximum_obstacles.append(None)
            missing_azimuths.append(float(azimuth_deg))
            continue

        targets = unit_points[valid] * (MOON_RADIUS_M + height[valid])[:, None]
        line_of_sight = targets - observer[None, :]
        vertical = line_of_sight @ up
        lateral = np.linalg.norm(line_of_sight - vertical[:, None] * up[None, :], axis=1)
        apparent_angle = np.degrees(np.arctan2(vertical, lateral))
        maximum_index = int(np.argmax(apparent_angle))
        angles.append(float(apparent_angle[maximum_index]))
        maximum_obstacles.append(float(distances[valid][maximum_index]))

    output = {
        "metadata": {
            "product": "Lunar terrain horizon profile",
            "generated_utc": datetime.now(timezone.utc).isoformat(),
            "site_name": site.get("site_name", "Shackleton Rim"),
            "latitude_deg": float(lat0),
            "longitude_deg_east": float(lon0 % 360),
            "site_x_m": site_x,
            "site_y_m": site_y,
            "dem_elevation_m": elevation_m,
            "observer_height_m": args.observer_height_m,
            "moon_reference_radius_m": MOON_RADIUS_M,
            "dem_lunar_reference_frame": "MOON_ME (DE421)",
            "horizon_reference": "Local spherical tangent plane",
            "azimuth_convention": "0=north, 90=east, clockwise",
            "maximum_search_distance_km": args.max_distance_km,
            "azimuth_step_deg": args.azimuth_step_deg,
            "local_dem": str(local_path),
            "regional_dem": str(regional_path),
            "local_crs_wkt": local_crs.to_wkt(),
            "regional_crs_wkt": regional_crs.to_wkt(),
            "method": "Radial DEM samples, nearest-neighbor elevations, spherical curvature",
            "limitations": [
                "Unsampled terrain features may obstruct the true horizon.",
                "Horizon beyond maximum search distance is not assessed.",
                "No-data pixels are unknown, not unobstructed terrain.",
                "DEM error and sub-pixel roughness are not propagated.",
                "Both DEMs are assumed to share lunar body-fixed axes and vertical datum; verify product documentation.",
                "Reference-frame consistency with any later SPICE calculation must be validated."
            ]
        },
        "samples": [
            {
                "azimuth_deg": float(azimuths[i]),
                "horizon_elevation_deg": angles[i],
                "obstacle_distance_m": maximum_obstacles[i],
                "missing_sample_fraction": missing_fraction[i]
            }
            for i in range(len(azimuths))
        ]
    }

    result_path = Path(args.output)
    result_path.write_text(json.dumps(output, indent=2), encoding="utf-8")
    valid_angles = [a for a in angles if a is not None]
    if not valid_angles:
        raise RuntimeError("No valid horizon directions were found.")

    fig, ax = plt.subplots(figsize=(12, 5))
    ax.plot(azimuths, np.array([np.nan if a is None else a for a in angles]),
            color="#3d6c91", linewidth=1.3, label="NASA LOLA terrain horizon")
    ax.axhline(0, color="black", linestyle="--", linewidth=0.8,
               label="Local geometric horizontal plane")
    ax.set(title="Shackleton Rim — Lunar Terrain Horizon Profile",
           xlabel="Azimuth (degrees clockwise from north)",
           ylabel="Terrain horizon elevation (degrees)", xlim=(0, 360))
    ax.grid(alpha=0.25)
    ax.legend()
    fig.tight_layout()
    png_path = result_path.with_suffix(".png")
    fig.savefig(png_path, dpi=160)
    plt.close(fig)

    print(f"Horizon JSON: {result_path.resolve()}")
    print(f"Horizon plot: {png_path.resolve()}")
    print(f"Horizon elevation range: {min(valid_angles):.3f} to {max(valid_angles):.3f} degrees")
    print(f"Directions with no data: {len(missing_azimuths)} of {len(azimuths)}")
    if any(f > 0 for f in missing_fraction):
        print("WARNING: One or more directions contain missing DEM samples.")
    print("Horizon calculation completed.")


if __name__ == "__main__":
    main()
