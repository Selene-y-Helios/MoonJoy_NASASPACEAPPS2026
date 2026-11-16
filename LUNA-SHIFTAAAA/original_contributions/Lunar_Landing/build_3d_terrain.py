
import json
from pathlib import Path

import numpy as np
import plotly.graph_objects as go
import rasterio

from rasterio.windows import Window
from rasterio.enums import Resampling
from rasterio.transform import rowcol


# ==========================================
# 1. CONFIGURATION
# ==========================================

DEM_FILE = Path("Site04_final_adj_5mpp_surf.tif")
SITE_FILES = [
    Path("lunar_site.json"),
    Path("sitio_lunar.json")
]

OUTPUT_FILE = Path("lunar_terrain_3d.html")

# Approximate local terrain size in meters
TERRAIN_SIZE_M = 4000

# Maximum grid size for visualization
GRID_SIZE = 220

# Observer height above the selected terrain
OBSERVER_HEIGHT_M = 1.5

# Keep vertical scale physically consistent
VERTICAL_EXAGGERATION = 1.0


# ==========================================
# 2. LOAD SELECTED LUNAR SITE
# ==========================================

if not DEM_FILE.exists():
    raise FileNotFoundError(
        f"DEM file not found: {DEM_FILE}"
    )

site_file = next(
    (path for path in SITE_FILES if path.exists()),
    None
)

if site_file is None:
    raise FileNotFoundError(
        "No lunar site JSON file found. "
        "Run the site selection script first."
    )

with site_file.open("r", encoding="utf-8") as file:
    site = json.load(file)

site_x = float(site["x_m"])
site_y = float(site["y_m"])

print("Selected lunar site loaded.")
print(f"Projected X: {site_x:.2f} m")
print(f"Projected Y: {site_y:.2f} m")


# ==========================================
# 3. EXTRACT A LOCAL DEM WINDOW
# ==========================================

with rasterio.open(DEM_FILE) as src:

    if not (
        src.bounds.left <= site_x <= src.bounds.right
        and src.bounds.bottom <= site_y <= src.bounds.top
    ):
        raise ValueError(
            "Selected site is outside the DEM bounds."
        )

    if not np.isclose(src.transform.b, 0) or not np.isclose(
        src.transform.d, 0
    ):
        raise ValueError(
            "This script requires a north-up raster."
        )

    if site.get("crs") and src.crs:
        try:
            if rasterio.crs.CRS.from_user_input(
                site["crs"]
            ) != src.crs:
                raise ValueError(
                    "Site and DEM coordinate systems differ."
                )
        except rasterio.errors.CRSError as error:
            raise ValueError(
                "Could not validate site CRS."
            ) from error

    pixel_size_x = abs(src.transform.a)
    pixel_size_y = abs(src.transform.e)

    center_row, center_col = rowcol(
        src.transform,
        site_x,
        site_y
    )

    half_cols = max(
        1, int(TERRAIN_SIZE_M / (2 * pixel_size_x))
    )
    half_rows = max(
        1, int(TERRAIN_SIZE_M / (2 * pixel_size_y))
    )

    col_start = max(0, center_col - half_cols)
    col_end = min(src.width, center_col + half_cols + 1)

    row_start = max(0, center_row - half_rows)
    row_end = min(src.height, center_row + half_rows + 1)

    window = Window(
        col_off=col_start,
        row_off=row_start,
        width=col_end - col_start,
        height=row_end - row_start
    )

    if window.width < 2 or window.height < 2:
        raise ValueError("Selected terrain window is too small.")

    output_rows = min(GRID_SIZE, int(window.height))
    output_cols = min(GRID_SIZE, int(window.width))

    elevation = src.read(
        1,
        window=window,
        out_shape=(output_rows, output_cols),
        masked=True,
        resampling=Resampling.nearest
    )

    # Read the selected site's original elevation
    site_value = src.read(
        1,
        window=Window(center_col, center_row, 1, 1),
        masked=True
    )

    if np.ma.is_masked(site_value[0, 0]):
        raise ValueError(
            "Selected site has no valid elevation data."
        )

    site_elevation = float(site_value[0, 0])

    # Transform pixel positions into projected meters
    window_transform = src.window_transform(window)

    scale_x = window.width / output_cols
    scale_y = window.height / output_rows

    sample_transform = window_transform * (
        rasterio.Affine.scale(scale_x, scale_y)
    )

    columns = np.arange(output_cols) + 0.5
    rows = np.arange(output_rows) + 0.5

    col_grid, row_grid = np.meshgrid(columns, rows)

    x_coords = (
        sample_transform.c
        + sample_transform.a * col_grid
    )

    y_coords = (
        sample_transform.f
        + sample_transform.e * row_grid
    )


# ==========================================
# 4. PREPARE 3D TERRAIN
# ==========================================

elevation = np.ma.filled(
    elevation.astype(float),
    np.nan
)

if not np.isfinite(elevation).any():
    raise ValueError(
        "The selected terrain window has no valid data."
    )

# Local X/Y coordinates relative to selected site
X = x_coords - site_x
Y = y_coords - site_y

# Relative height for the 3D display
Z = (
    elevation - site_elevation
) * VERTICAL_EXAGGERATION

observer_z = (
    OBSERVER_HEIGHT_M * VERTICAL_EXAGGERATION
)

print("Terrain data processed successfully.")
print(f"Grid: {output_rows} x {output_cols}")
print(f"Site elevation: {site_elevation:.2f} m")


# ==========================================
# 5. CREATE INTERACTIVE 3D VIEW
# ==========================================

fig = go.Figure()

fig.add_trace(
    go.Surface(
        x=X,
        y=Y,
        z=Z,
        surfacecolor=elevation,
        colorscale="Earth",
        colorbar=dict(
            title="Elevation (m)"
        ),
        customdata=elevation,
        hovertemplate=(
            "Local X: %{x:.1f} m<br>"
            "Local Y: %{y:.1f} m<br>"
            "Relative height: %{z:.1f} m<br>"
            "DEM elevation: %{customdata:.1f} m"
            "<extra></extra>"
        ),
        name="Lunar Terrain",
        showscale=True
    )
)

# Add the selected observer position
fig.add_trace(
    go.Scatter3d(
        x=[0],
        y=[0],
        z=[observer_z],
        mode="markers+text",
        marker=dict(
            size=8,
            color="red",
            symbol="circle"
        ),
        text=["Selected Landing Site"],
        textposition="top center",
        name="Selected Site",
        hovertemplate=(
            "Selected Landing Site<br>"
            f"Elevation: {site_elevation:.2f} m<br>"
            f"Observer height: {OBSERVER_HEIGHT_M:.1f} m"
            "<extra></extra>"
        )
    )
)

fig.update_layout(
    title=dict(
        text="NASA LOLA - Shackleton Rim | 3D Lunar Terrain",
        x=0.5
    ),

    scene=dict(
        xaxis_title="Local X (m)",
        yaxis_title="Local Y (m)",
        zaxis_title="Relative Height (m)",

        aspectmode="data",

        camera=dict(
            eye=dict(x=1.5, y=-1.5, z=1.0)
        )
    ),

    margin=dict(l=0, r=0, b=0, t=65),

    paper_bgcolor="#0b1020",
    font=dict(color="white"),

    legend=dict(
        x=0.01,
        y=0.99
    )
)


# ==========================================
# 6. SAVE AND OPEN HTML
# ==========================================

fig.write_html(
    str(OUTPUT_FILE),
    include_plotlyjs=True,
    full_html=True,
    auto_open=True
)

print("3D terrain generated successfully.")
print(f"Output file: {OUTPUT_FILE.resolve()}")
print("Open the HTML file in your browser.")
