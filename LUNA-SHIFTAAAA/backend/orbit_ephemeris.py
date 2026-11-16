"""Geometric Sun/Earth/Moon orbital geometry from JPL DE440 via NAIF SPICE.

All returned vectors are in ICRF/J2000 coordinates and kilometers. No
approximate circular-orbit formulas or invented astronomical coordinates are used.
The browser scales heliocentric and geocentric distances separately for display.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from pathlib import Path
import re

try:
    import spiceypy as spice
except ImportError:
    spice = None

UTC = timezone.utc
KERNELS = ("naif0012.tls", "de440s.bsp")
EARTH_ORBIT_DAYS = 365.25636  # Only selects the path's sample duration.
MOON_ORBIT_DAYS = 27.321661   # Only selects the path's sample duration.


def _spice_time(instant: datetime) -> float:
    # NAIF STR2ET handles this explicit UTC representation reliably.
    return float(spice.str2et(instant.strftime("%Y-%m-%d %H:%M:%S UTC")))


def _vector(target: str, observer: str, et: float) -> list[float]:
    # Geometric J2000 ephemeris coordinates, consistent with our visibility model.
    xyz, _ = spice.spkpos(target, et, "J2000", "NONE", observer)
    return [float(component) for component in xyz]


def _instant_label(instant: datetime) -> str:
    return instant.astimezone(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


def calculate_orbit_ephemeris(day: str, kernels_dir: Path) -> dict:
    """Call with the API's shared SPICE_LOCK already held.

    The sample window spans the selected UTC date and its neighboring dates,
    supporting responsive playback by interpolation without SPICE per frame.
    """
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", day):
        raise ValueError("Expected UTC date YYYY-MM-DD.")
    try:
        requested_day = date.fromisoformat(day)
    except ValueError as error:
        raise ValueError("Invalid UTC calendar date.") from error

    if spice is None:
        raise RuntimeError("SpiceyPy must be installed before orbit calculations.")
    missing = [name for name in KERNELS if not (kernels_dir / name).is_file()]
    if missing:
        raise FileNotFoundError("Missing orbit kernels: " + ", ".join(missing))

    midnight = datetime(requested_day.year, requested_day.month, requested_day.day, tzinfo=UTC)
    samples = []
    earth_curve = []
    moon_curve = []
    try:
        for kernel in KERNELS:
            spice.furnsh(str(kernels_dir / kernel))

        # 30-minute samples spanning previous 24 h through next 72 h.
        for sample_index in range(-48, 145):
            instant = midnight + timedelta(minutes=30 * sample_index)
            et = _spice_time(instant)
            samples.append({
                "time_utc": _instant_label(instant),
                "earth_sun_km": _vector("EARTH", "SUN", et),
                "moon_earth_km": _vector("MOON", "EARTH", et),
            })

        # Each plotted path is sampled from the kernel, NOT a fixed orbit ring.
        for sample_index in range(366):
            instant = midnight + timedelta(days=(sample_index - 182))
            earth_curve.append(_vector("EARTH", "SUN", _spice_time(instant)))

        moon_samples = 224
        for sample_index in range(moon_samples):
            offset = (sample_index / moon_samples - 0.5) * MOON_ORBIT_DAYS
            instant = midnight + timedelta(days=offset)
            moon_curve.append(_vector("MOON", "EARTH", _spice_time(instant)))
    finally:
        # The API uses SPICE_LOCK across all SPICE endpoints: pool changes are safe.
        spice.kclear()

    return {
        "date": day,
        "reference_frame": "J2000",
        "ephemeris": "de440s.bsp",
        "aberration_correction": "NONE",
        "samples": samples,
        "earth_curve_km": earth_curve,
        "moon_curve_km": moon_curve,
        "notes": [
            "SPICE geometric body-center positions; no light-time correction.",
            "Earth orbit and Moon orbit are displayed using different distance scales.",
            "Earth/Moon texture orientation and axial spin remain illustrative in this update.",
        ],
    }
