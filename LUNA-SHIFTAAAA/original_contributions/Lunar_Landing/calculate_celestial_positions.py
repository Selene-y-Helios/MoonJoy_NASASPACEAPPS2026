
import json
import math
from pathlib import Path

import numpy as np
import rasterio
import spiceypy as spice

from pyproj import CRS, Transformer
from rasterio.transform import rowcol
from rasterio.windows import Window


# ==========================================
# 1. CONFIGURATION
# ==========================================

BASE_DIR = Path(__file__).resolve().parent

DEM_FILE = (
    BASE_DIR / "data/dem/Site04_final_adj_5mpp_surf.tif"
)

SITE_FILE = BASE_DIR / "lunar_site.json"
KERNEL_DIR = BASE_DIR / "data/kernels"

OUTPUT_FILE = BASE_DIR / "celestial_positions.json"

UTC_DATE = "2026-11-14 12:00:00 UTC"

OBSERVER_HEIGHT_M = 1.5

# Reference radius used by the LOLA DEM
MOON_REFERENCE_RADIUS_M = 1737400.0

KERNEL_FILES = [
    "naif0012.tls",
    "de440s.bsp",
    "moon_pa_de440_200625.bpc",
    "moon_de440_250416.tf",
    "pck00011.tpc",
]


# ==========================================
# 2. LOAD SITE AND DEM INFORMATION
# ==========================================

with SITE_FILE.open("r", encoding="utf-8") as file:
    site = json.load(file)

site_x = float(site["x_m"])
site_y = float(site["y_m"])

with rasterio.open(DEM_FILE) as src:

    if src.crs is None:
        raise ValueError(
            "The DEM has no coordinate reference system."
        )

    dem_crs = CRS.from_user_input(src.crs.to_wkt())

    if site.get("crs"):
        site_crs = CRS.from_user_input(site["crs"])

        if not site_crs.equals(dem_crs):
            raise ValueError(
                "Site and DEM coordinate systems differ."
            )

    row, col = rowcol(src.transform, site_x, site_y)

    if not (
        0 <= row < src.height
        and 0 <= col < src.width
    ):
        raise ValueError(
            "The selected site is outside the DEM."
        )

    elevation_data = src.read(
        1,
        window=Window(col, row, 1, 1),
        masked=True
    )

    if np.ma.is_masked(elevation_data[0, 0]):
        raise ValueError(
            "The selected site has no valid elevation."
        )

    elevation_m = float(elevation_data[0, 0])

    # Convert lunar projected coordinates to
    # geographic coordinates of the same lunar CRS.
    geographic_crs = dem_crs.geodetic_crs

    if geographic_crs is None:
        raise ValueError(
            "The DEM has no lunar geographic CRS."
        )

    transformer = Transformer.from_crs(
        dem_crs,
        geographic_crs,
        always_xy=True
    )

    longitude_deg, latitude_deg = transformer.transform(
        site_x,
        site_y
    )

if not (
    math.isfinite(latitude_deg)
    and math.isfinite(longitude_deg)
    and math.isfinite(elevation_m)
):
    raise ValueError(
        "Invalid lunar coordinates or elevation."
    )

# Normalize east-positive longitude
longitude_deg = longitude_deg % 360.0

print("Lunar observer loaded successfully.")
print(f"Latitude: {latitude_deg:.6f} deg")
print(f"Longitude: {longitude_deg:.6f} deg East")
print(f"DEM elevation: {elevation_m:.2f} m")


# ==========================================
# 3. BUILD LOCAL OBSERVER FRAME
# ==========================================

lat = math.radians(latitude_deg)
lon = math.radians(longitude_deg)

up = np.array([
    math.cos(lat) * math.cos(lon),
    math.cos(lat) * math.sin(lon),
    math.sin(lat)
])

east = np.array([
    -math.sin(lon),
    math.cos(lon),
    0.0
])

north = np.array([
    -math.sin(lat) * math.cos(lon),
    -math.sin(lat) * math.sin(lon),
    math.cos(lat)
])

radius_km = (
    MOON_REFERENCE_RADIUS_M
    + elevation_m
    + OBSERVER_HEIGHT_M
) / 1000.0

observer_position = radius_km * up


# ==========================================
# 4. LOAD NASA SPICE KERNELS
# ==========================================

try:
    for filename in KERNEL_FILES:
        kernel_path = KERNEL_DIR / filename

        if not kernel_path.exists():
            raise FileNotFoundError(
                f"Kernel not found: {kernel_path}"
            )

        spice.furnsh(str(kernel_path))

    et = spice.str2et(UTC_DATE)

    # JPL lunar reference frame
    rotation = spice.pxform(
        "J2000",
        "MOON_ME",
        et
    )

    # ======================================
    # 5. CALCULATE BODY DIRECTIONS
    # ======================================

    def calculate_body(body_name):

        # Apparent body-center vector relative
        # to the Moon center.
        body_vector, light_time = spice.spkpos(
            body_name,
            et,
            "J2000",
            "LT+S",
            "MOON"
        )

        body_moon_frame = (
            rotation @ np.asarray(body_vector)
        )

        # Approximate topocentric vector
        local_vector = (
            body_moon_frame - observer_position
        )

        distance_km = float(
            np.linalg.norm(local_vector)
        )

        direction = local_vector / distance_km

        east_component = float(
            np.dot(direction, east)
        )

        north_component = float(
            np.dot(direction, north)
        )

        up_component = float(
            np.dot(direction, up)
        )

        azimuth = math.degrees(
            math.atan2(
                east_component,
                north_component
            )
        ) % 360.0

        elevation = math.degrees(
            math.asin(
                np.clip(up_component, -1.0, 1.0)
            )
        )

        return {
            "azimuth_deg": round(azimuth, 6),
            "elevation_deg": round(elevation, 6),
            "distance_km": round(distance_km, 3),
            "above_geometric_horizon": elevation > 0
        }

    sun = calculate_body("SUN")
    earth = calculate_body("EARTH")

    # ======================================
    # 6. EXPORT RESULTS
    # ======================================

    result = {
        "date_utc": UTC_DATE,
        "site": {
            "name": site.get(
                "site_name",
                "Shackleton Rim"
            ),
            "latitude_deg": latitude_deg,
            "longitude_deg_east": longitude_deg,
            "dem_elevation_m": elevation_m,
            "observer_height_m": OBSERVER_HEIGHT_M
        },
        "sun": sun,
        "earth": earth,
        "calculation_notes": {
            "reference_frame": "MOON_ME",
            "aberration_correction": "LT+S",
            "visibility_model": "geometric_horizontal_plane",
            "terrain_occlusion_included": False,
            "body_disc_included": False,
            "observer_light_time_approximation": True
        }
    }

    OUTPUT_FILE.write_text(
        json.dumps(result, indent=4),
        encoding="utf-8"
    )

    print("\nSUN POSITION")
    print(f"Azimuth: {sun['azimuth_deg']:.3f} deg")
    print(f"Elevation: {sun['elevation_deg']:.3f} deg")

    print("\nEARTH POSITION")
    print(f"Azimuth: {earth['azimuth_deg']:.3f} deg")
    print(f"Elevation: {earth['elevation_deg']:.3f} deg")

    print("\nCalculation completed successfully.")
    print(f"Output file: {OUTPUT_FILE}")

finally:
    spice.kclear()
