
import spiceypy as spice
from pathlib import Path

# ==========================================
# 1. CONFIGURE SPICE KERNELS
# ==========================================

kernel_dir = Path("data/kernels")

kernel_files = [
    "naif0012.tls",
    "de440s.bsp",
    "moon_pa_de440_200625.bpc",
    "moon_de440_250416.tf",
    "pck00011.tpc",
]

# ==========================================
# 2. LOAD KERNELS
# ==========================================

try:
    for filename in kernel_files:
        kernel_path = kernel_dir / filename

        if not kernel_path.exists():
            raise FileNotFoundError(
                f"Kernel not found: {kernel_path}"
            )

        spice.furnsh(str(kernel_path))

    print("SPICE kernels loaded successfully.")

    # ======================================
    # 3. CONVERT UTC TO EPHEMERIS TIME
    # ======================================

    utc_date = "2026-11-14 12:00:00 UTC"

    et = spice.str2et(utc_date)

    print(f"Selected date: {utc_date}")
    print(f"Ephemeris time: {et}")

    # ======================================
    # 4. CALCULATE MOON POSITION
    # ======================================

    moon_position, light_time = spice.spkpos(
        "MOON",
        et,
        "J2000",
        "NONE",
        "EARTH"
    )

    print("\nMoon position relative to Earth (km):")

    print(f"X: {moon_position[0]:,.2f} km")
    print(f"Y: {moon_position[1]:,.2f} km")
    print(f"Z: {moon_position[2]:,.2f} km")

    distance = spice.vnorm(moon_position)

    print(f"\nEarth-Moon distance: {distance:,.2f} km")

    print("\nSPICE calculation completed successfully.")

finally:
    spice.kclear()
