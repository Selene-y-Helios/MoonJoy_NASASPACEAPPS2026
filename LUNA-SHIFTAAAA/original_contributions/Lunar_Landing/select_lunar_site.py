import rasterio
import numpy as np
import matplotlib.pyplot as plt
import json
from pathlib import Path

# ==========================================
# 1. LOAD NASA ELEVATION MODEL
# ==========================================

file_path = "Site04_final_adj_5mpp_surf.tif"

with rasterio.open(file_path) as src:
    elevation = src.read(1, masked=True)
    elevation = elevation.filled(np.nan)
    transform = src.transform
    bounds = src.bounds
    crs = src.crs

print("Lunar elevation model loaded successfully.")
print("Dimensions:", elevation.shape)
print("Coordinate reference system:", crs)

# ==========================================
# 2. CREATE INTERACTIVE WINDOW
# ==========================================

fig, ax = plt.subplots(figsize=(12, 8))

# Leave extra space at the bottom for results text
fig.subplots_adjust(bottom=0.23)

image = ax.imshow(
    elevation,
    cmap="terrain",
    origin="upper",
    extent=[
        bounds.left,
        bounds.right,
        bounds.bottom,
        bounds.top
    ]
)

plt.colorbar(
    image,
    ax=ax,
    label="Lunar elevation (m)"
)

ax.set_title(
    "NASA LOLA - Shackleton Rim\n"
    "Click to select a lunar site"
)

ax.set_xlabel("Projected X coordinate (m)")
ax.set_ylabel("Projected Y coordinate (m)")

# Red marker shown after clicking
marker, = ax.plot(
    [],
    [],
    "ro",
    markersize=9,
    markeredgecolor="white",
    markeredgewidth=2
)

# Text box for selected point information
info_text = fig.text(
    0.12,
    0.06,
    "Select a point on the lunar terrain.",
    fontsize=11,
    family="monospace",
    verticalalignment="bottom"
)

# ==========================================
# 3. INTERACTIVE SELECTION FUNCTION
# ==========================================

def select_point(event):

    if event.inaxes != ax:
        return

    if event.xdata is None or event.ydata is None:
        return

    x = float(event.xdata)
    y = float(event.ydata)

    row, col = rasterio.transform.rowcol(
        transform, x, y
    )

    if not (
        0 <= row < elevation.shape[0]
        and 0 <= col < elevation.shape[1]
    ):
        return

    height = elevation[row, col]

    if not np.isfinite(height):
        info_text.set_text(
            "Selected point has no valid elevation data."
        )
        fig.canvas.draw_idle()
        return

    # ======================================
    # 4. UPDATE MARKER
    # ======================================

    marker.set_data([x], [y])

    message = (
        "SELECTED LUNAR SITE\n"
        f"X: {x:.2f} m    "
        f"Y: {y:.2f} m\n"
        f"Elevation: {height:.2f} m    "
        f"Pixel: ({row}, {col})"
    )

    info_text.set_text(message)

    print("\n" + message, flush=True)

    # ======================================
    # 5. SAVE DATA
    # ======================================

    result = {
        "site_name": "Shackleton Rim",
        "x_m": x,
        "y_m": y,
        "elevation_m": float(height),
        "row": int(row),
        "column": int(col),
        "crs": crs.to_wkt() if crs else None,
        "dem_file": file_path
    }

    Path("lunar_site.json").write_text(
        json.dumps(result, indent=4),
        encoding="utf-8"
    )

    print("File 'lunar_site.json' updated successfully.")

    fig.canvas.draw_idle()

# Connect mouse click to function
fig.canvas.mpl_connect(
    "button_press_event",
    select_point
)

plt.show() 