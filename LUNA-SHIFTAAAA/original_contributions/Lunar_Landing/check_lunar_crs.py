import rasterio
from pathlib import Path

# ==========================================
# 1. CONFIGURATION
# ==========================================

BASE_DIR = Path(__file__).resolve().parent

DEM_FILES = {
    "Local DEM": (
        BASE_DIR
        / "data/dem/Site04_final_adj_5mpp_surf.tif"
    ),
    "Regional DEM": (
        BASE_DIR
        / "data/dem/LDEM_80S_80MPP_ADJ.TIF"
    )
}

# ==========================================
# 2. INSPECT DEM METADATA
# ==========================================

for name, file_path in DEM_FILES.items():

    print("\n" + "=" * 60)
    print(name)
    print("=" * 60)

    if not file_path.exists():
        print(f"File not found: {file_path}")
        continue

    with rasterio.open(file_path) as src:

        print("\nFile:", file_path.name)

        print("\nCoordinate Reference System:")
        print(src.crs)

        print("\nCRS WKT:")
        print(src.crs.to_wkt() if src.crs else "None")

        print("\nRaster bounds:")
        print(src.bounds)

        print("\nPixel resolution:")
        print(src.res)

        print("\nRaster dimensions:")
        print(f"Width: {src.width}")
        print(f"Height: {src.height}")

        print("\nAffine transform:")
        print(src.transform)

        print("\nNoData value:")
        print(src.nodata)

print("\nCRS inspection completed.")
