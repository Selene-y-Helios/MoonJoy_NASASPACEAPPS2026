"""Compute sampled Sun/Earth horizon visibility for a lunar site.

Input: horizon_profile.json from compute_horizon_crs_fixed.py and NASA/JPL SPICE kernels.
Output: visibility_results.json and visibility_timeline.png.

The method uses geometric body-center directions, a sampled DEM horizon, and
linear interpolation between time samples. It is NOT mission-certified.
"""

import argparse
import json
import math
from datetime import datetime, timedelta, timezone
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
try:
    import spiceypy as spice
except ImportError:
    spice = None

BASE_DIR = Path(__file__).resolve().parent
KERNEL_NAMES = [
    "naif0012.tls",
    "de440s.bsp",
    "moon_pa_de440_200625.bpc",
    "moon_de440_250416.tf",
    "pck00011.tpc",
]


def parse_utc(value):
    """Accept YYYY-MM-DD, ISO UTC, or YYYY-MM-DD HH:MM:SS UTC."""
    value = value.strip()
    if value.upper().endswith(" UTC"):
        value = value[:-4].strip()
    if value.endswith("Z"):
        value = value[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(
            f"Invalid UTC date: {value!r}. Use 2026-11-14T12:00:00Z."
        ) from exc
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    if parsed.utcoffset() != timedelta(0):
        parsed = parsed.astimezone(timezone.utc)
    return parsed


def utc_string(value):
    return value.astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def load_horizon(path):
    data = json.loads(path.read_text(encoding="utf-8"))
    metadata = data.get("metadata", {})
    raw = data.get("samples", [])
    if len(raw) < 4:
        raise ValueError("Horizon JSON must have at least four azimuth samples.")
    required = ["latitude_deg", "longitude_deg_east", "dem_elevation_m", "observer_height_m"]
    absent = [name for name in required if name not in metadata]
    if absent:
        raise ValueError(f"Missing horizon metadata: {', '.join(absent)}")
    samples = sorted(raw, key=lambda item: float(item["azimuth_deg"]))
    az = np.asarray([float(s["azimuth_deg"]) for s in samples], dtype=float)
    heights = np.asarray([
        float(s["horizon_elevation_deg"]) if s.get("horizon_elevation_deg") is not None else float("nan")
        for s in samples
    ], dtype=float)
    if np.any(~np.isfinite(az)) or np.any(np.diff(az) <= 0) or az[0] < 0 or az[-1] >= 360:
        raise ValueError("Horizon azimuth samples must be unique and within [0, 360).")
    if np.any(np.diff(np.concatenate((az, [az[0] + 360.0]))) > 20):
        raise ValueError("Horizon profile has azimuth gaps larger than 20 degrees.")
    if not np.isfinite(heights).any():
        raise ValueError("No valid horizon elevations available.")
    return metadata, az, heights


def horizon_at(azimuth, az_samples, elevation_samples):
    """Circular interpolation; missing neighbors yield unknown, not clear sky."""
    azimuth = azimuth % 360.0
    right = int(np.searchsorted(az_samples, azimuth, side="right")) % len(az_samples)
    left = (right - 1) % len(az_samples)
    a = float(az_samples[left])
    b = float(az_samples[right])
    q = azimuth
    if right == 0:
        b += 360.0
    if q < a:
        q += 360.0
    h0, h1 = elevation_samples[left], elevation_samples[right]
    if not (math.isfinite(h0) and math.isfinite(h1)):
        return None
    fraction = 0.0 if math.isclose(a, b) else (q - a) / (b - a)
    return float(h0 + (h1 - h0) * fraction)


def local_basis(latitude_deg, longitude_deg):
    lat, lon = np.deg2rad([latitude_deg, longitude_deg])
    up = np.array([np.cos(lat) * np.cos(lon), np.cos(lat) * np.sin(lon), np.sin(lat)])
    east = np.array([-np.sin(lon), np.cos(lon), 0.0])
    north = np.array([-np.sin(lat) * np.cos(lon), -np.sin(lat) * np.sin(lon), np.cos(lat)])
    return up, east, north


def sky_position(body, et, observer, up, east, north, azimuths, horizon_heights):
    # Same-time geometric vector; no aberration correction (NONE).
    body_center_km, _ = spice.spkpos(body, et, "MOON_ME", "NONE", "MOON")
    relative = np.asarray(body_center_km, dtype=float) - observer
    distance = float(np.linalg.norm(relative))
    direction = relative / distance
    east_value = float(np.dot(direction, east))
    north_value = float(np.dot(direction, north))
    up_value = float(np.dot(direction, up))
    azimuth = (math.degrees(math.atan2(east_value, north_value)) + 360.0) % 360.0
    elevation = math.degrees(math.asin(np.clip(up_value, -1.0, 1.0)))
    terrain_horizon = horizon_at(azimuth, azimuths, horizon_heights)
    clearance = elevation - terrain_horizon if terrain_horizon is not None else None
    return {
        "azimuth_deg": round(azimuth, 6),
        "elevation_deg": round(elevation, 6),
        "horizon_elevation_deg": round(terrain_horizon, 6) if terrain_horizon is not None else None,
        "clearance_deg": round(clearance, 6) if clearance is not None else None,
        "visible_center": bool(clearance > 0) if clearance is not None else None,
        "distance_km": round(distance, 3),
        "direction_local_east_north_up": [round(east_value, 9), round(north_value, 9), round(up_value, 9)],
    }


def sample_times(start, end, step_minutes):
    duration = (end - start).total_seconds()
    count = math.ceil(duration / (step_minutes * 60))
    if count > 20000:
        raise ValueError("Too many samples. Shorten the interval or increase --step-minutes.")
    return [min(start + timedelta(minutes=step_minutes * index), end) for index in range(count + 1)]


def segment_intervals(times, timeline):
    """Split time intervals at linearly interpolated center-visibility crossings."""
    pieces = []
    for index in range(len(times) - 1):
        t0, t1 = times[index:index + 2]
        dt = (t1 - t0).total_seconds()
        if dt <= 0:
            continue
        start_record, end_record = timeline[index:index + 2]
        m0 = {b: start_record[b]["clearance_deg"] for b in ("sun", "earth")}
        m1 = {b: end_record[b]["clearance_deg"] for b in ("sun", "earth")}
        roots = [0.0, 1.0]
        for body in ("sun", "earth"):
            v0, v1 = m0[body], m1[body]
            if v0 is not None and v1 is not None and ((v0 < 0 < v1) or (v1 < 0 < v0)):
                roots.append(-v0 / (v1 - v0))
        roots = sorted(set(roots))
        for a, b in zip(roots[:-1], roots[1:]):
            if b <= a:
                continue
            middle = (a + b) / 2
            flags = {}
            for body in ("sun", "earth"):
                v0, v1 = m0[body], m1[body]
                if v0 is None or v1 is None:
                    flags[body] = None
                else:
                    flags[body] = (v0 + middle * (v1 - v0)) > 0
            flags["both"] = (
                flags["sun"] and flags["earth"]
                if flags["sun"] is not None and flags["earth"] is not None else None
            )
            pieces.append({
                "start": t0 + timedelta(seconds=a * dt),
                "end": t0 + timedelta(seconds=b * dt),
                "flags": flags,
            })
    return pieces


def build_summary(pieces, total_seconds):
    summary = {}
    all_windows = {}
    for body in ("sun", "earth", "both"):
        visible_seconds = 0.0
        unknown_seconds = 0.0
        active = []
        for piece in pieces:
            flag = piece["flags"][body]
            seconds = (piece["end"] - piece["start"]).total_seconds()
            if flag is True:
                visible_seconds += seconds
                if active and (piece["start"] - active[-1]["end"]).total_seconds() < 0.01:
                    active[-1]["end"] = piece["end"]
                else:
                    active.append({"start": piece["start"], "end": piece["end"]})
            elif flag is None:
                unknown_seconds += seconds
        all_windows[body] = [
            {
                "start_utc": utc_string(window["start"]),
                "end_utc": utc_string(window["end"]),
                "duration_hours": round((window["end"] - window["start"]).total_seconds() / 3600, 5),
            }
            for window in active
        ]
        summary[body] = {
            "visible_hours": round(visible_seconds / 3600, 5),
            "visible_percent_of_interval": round(100 * visible_seconds / total_seconds, 3),
            "unknown_hours": round(unknown_seconds / 3600, 5),
            "window_count": len(active),
        }
    return summary, all_windows


def plot_timeline(timeline, output_path):
    times = [datetime.fromisoformat(p["time_utc"].replace("Z", "+00:00")) for p in timeline]
    fig, axes = plt.subplots(2, 1, figsize=(12, 7), sharex=True, constrained_layout=True)
    for axis, body, label, color in zip(
        axes, ("sun", "earth"), ("Sun", "Earth"), ("#e6a544", "#4596d2")
    ):
        altitude = [item[body]["elevation_deg"] for item in timeline]
        horizon = [item[body]["horizon_elevation_deg"] for item in timeline]
        axis.plot(times, altitude, color=color, label=f"{label} elevation")
        axis.plot(times, horizon, color="black", linestyle="--", label="Terrain horizon")
        axis.set_ylabel("Elevation (degrees)")
        axis.grid(alpha=0.25)
        axis.legend(loc="best")
    axes[0].set_title("Shackleton Rim | Geometric Sun and Earth Visibility")
    axes[-1].set_xlabel("UTC date and time")
    fig.autofmt_xdate()
    fig.savefig(output_path, dpi=160)
    plt.close(fig)


def calculate_visibility(start_utc, end_utc, step_minutes=10.0, horizon_path=None, kernel_dir=None):
    """Reusable function for a future FastAPI backend; accepts ISO UTC strings."""
    if spice is None:
        raise RuntimeError("SpiceyPy is not installed; install requirements.txt for dynamic simulations.")
    start, end = parse_utc(start_utc), parse_utc(end_utc)
    if end <= start:
        raise ValueError("End time must be later than start time.")
    if not (0 < step_minutes <= 1440):
        raise ValueError("Step minutes must be greater than 0 and at most 1440.")
    horizon_path = Path(horizon_path) if horizon_path else BASE_DIR / "horizon_profile.json"
    kernel_dir = Path(kernel_dir) if kernel_dir else BASE_DIR / "data" / "kernels"
    if not horizon_path.is_file():
        raise FileNotFoundError(f"Horizon JSON not found: {horizon_path}")
    metadata, azimuths, horizon_heights = load_horizon(horizon_path)
    lat = float(metadata["latitude_deg"])
    lon = float(metadata["longitude_deg_east"])
    radius = float(metadata.get("moon_reference_radius_m", 1737400.0))
    observer_radius_km = (radius + float(metadata["dem_elevation_m"]) + float(metadata["observer_height_m"])) / 1000.0
    up, east, north = local_basis(lat, lon)
    observer = observer_radius_km * up
    times = sample_times(start, end, step_minutes)
    for name in KERNEL_NAMES:
        if not (kernel_dir / name).is_file():
            raise FileNotFoundError(f"Missing SPICE kernel: {kernel_dir / name}")

    timeline = []
    try:
        for name in KERNEL_NAMES:
            spice.furnsh(str(kernel_dir / name))
        # Check the lunar frame is available at the requested dates.
        spice.pxform("J2000", "MOON_ME", spice.str2et(start.strftime("%Y-%m-%d %H:%M:%S UTC")))
        for current in times:
            et = spice.str2et(current.strftime("%Y-%m-%d %H:%M:%S UTC"))
            timeline.append({
                "time_utc": utc_string(current),
                "sun": sky_position("SUN", et, observer, up, east, north, azimuths, horizon_heights),
                "earth": sky_position("EARTH", et, observer, up, east, north, azimuths, horizon_heights),
            })
    finally:
        spice.kclear()

    total_seconds = (end - start).total_seconds()
    pieces = segment_intervals(times, timeline)
    summary, windows = build_summary(pieces, total_seconds)
    warnings = [
        "Preliminary visualization model; not mission-qualified.",
        "Body-center visibility only: apparent disks, receiver height, and antenna masks are not included.",
        "SPICE uses geometric positions (NONE) without light-time or stellar-aberration corrections.",
        "Window boundary times are linearly interpolated and depend on time-step resolution.",
        "LOLA DEM height datum and lunar-frame compatibility must be independently validated.",
        "Complete shadowing and communications link budgets are not modeled.",
    ]
    return {
        "metadata": {
            "product": "Lunar Sun and Earth visibility assessment",
            "site_name": metadata.get("site_name", "Shackleton Rim"),
            "site_latitude_deg": lat,
            "site_longitude_deg_east": lon,
            "site_elevation_m": float(metadata["dem_elevation_m"]),
            "observer_height_m": float(metadata["observer_height_m"]),
            "start_utc": utc_string(start),
            "end_utc": utc_string(end),
            "step_minutes": step_minutes,
            "time_samples": len(times),
            "horizon_source": str(horizon_path),
            "lunar_frame": "MOON_ME (DE440 orientation with ME421 alignment)",
            "ephemeris": "de440s.bsp",
            "aberration_correction": "NONE",
            "visibility_definition": "Body center strictly above DEM terrain horizon",
            "warnings": warnings,
        },
        "summary": summary,
        "windows": windows,
        "timeline": timeline,
    }


def main():
    parser = argparse.ArgumentParser(description="NASA/JPL lunar site Sun and Earth visibility")
    parser.add_argument("--start", required=True, help="UTC start, e.g. 2026-11-14T00:00:00Z")
    parser.add_argument("--end", required=True, help="UTC end, e.g. 2026-11-21T00:00:00Z")
    parser.add_argument("--step-minutes", type=float, default=10.0)
    parser.add_argument("--horizon", default="horizon_profile.json")
    parser.add_argument("--kernels", default="data/kernels")
    parser.add_argument("--output", default="visibility_results.json")
    args = parser.parse_args()
    result = calculate_visibility(
        args.start, args.end, args.step_minutes,
        horizon_path=BASE_DIR / args.horizon,
        kernel_dir=BASE_DIR / args.kernels,
    )
    output = BASE_DIR / args.output
    output.write_text(json.dumps(result, indent=2, allow_nan=False), encoding="utf-8")
    png_path = output.with_suffix(".png")
    plot_timeline(result["timeline"], png_path)
    print("Visibility calculation completed successfully.")
    print("Site:", result["metadata"]["site_name"])
    print("UTC interval:", result["metadata"]["start_utc"], "to", result["metadata"]["end_utc"])
    print("Sample count:", result["metadata"]["time_samples"])
    for body, label in (("sun", "Sun"), ("earth", "Earth"), ("both", "Sun and Earth")):
        block = result["summary"][body]
        print(f"{label} visible: {block['visible_hours']:.2f} h ({block['visible_percent_of_interval']:.2f}%)")
        print(f"{label} unknown: {block['unknown_hours']:.2f} h")
    print("JSON output:", output)
    print("Timeline plot:", png_path)
    print("WARNING: Results are preliminary and not mission-qualified.")


if __name__ == "__main__":
    main()
