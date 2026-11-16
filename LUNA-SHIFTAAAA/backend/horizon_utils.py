"""Validation and circular interpolation for NASA LOLA lunar horizon profiles."""

import json
import math
from pathlib import Path


def load_horizon(path):
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data.get("samples"), list):
        raise ValueError("Horizon file has no sample list.")
    meta = data.get("metadata", {})
    required = ("latitude_deg", "longitude_deg_east", "dem_elevation_m", "observer_height_m")
    if any(name not in meta for name in required):
        raise ValueError("Horizon metadata is missing observer coordinates or elevation.")
    samples = sorted(data["samples"], key=lambda r: float(r["azimuth_deg"]))
    if len(samples) < 4:
        raise ValueError("At least four horizon samples are required.")
    azimuths = [float(s["azimuth_deg"]) for s in samples]
    if any(not math.isfinite(a) or a < 0 or a >= 360 for a in azimuths):
        raise ValueError("Azimuths must be finite and within [0, 360).")
    if any(b <= a for a, b in zip(azimuths, azimuths[1:])):
        raise ValueError("Horizon azimuths must be unique and increasing.")
    return data


def horizon_at(data, azimuth_deg):
    """Return interpolated terrain-horizon elevation, or None for unknown terrain."""
    samples = sorted(data["samples"], key=lambda s: float(s["azimuth_deg"]))
    query = float(azimuth_deg) % 360.0
    for i, left in enumerate(samples):
        right = samples[(i + 1) % len(samples)]
        a = float(left["azimuth_deg"])
        b = float(right["azimuth_deg"]) + (360.0 if i == len(samples) - 1 else 0.0)
        adjusted = query + (360.0 if query < a else 0.0)
        if a <= adjusted <= b:
            h0, h1 = left.get("horizon_elevation_deg"), right.get("horizon_elevation_deg")
            if h0 is None or h1 is None:
                return None
            h0, h1 = float(h0), float(h1)
            if not (math.isfinite(h0) and math.isfinite(h1)):
                return None
            return h0 + (h1 - h0) * ((adjusted - a) / (b - a))
    raise ValueError("Failed to interpolate the horizon in a circular azimuth range.")


def check_observer_match(horizon_metadata, observer):
    """Reject data from different sites; label matching is not sufficient."""
    delta_lat = abs(float(horizon_metadata["latitude_deg"]) - float(observer["latitude_deg"]))
    delta_lon = abs(((float(horizon_metadata["longitude_deg_east"]) -
                     float(observer["longitude_deg_east"]) + 180) % 360) - 180)
    delta_elev = abs(float(horizon_metadata["dem_elevation_m"]) - float(observer["dem_elevation_m"]))
    delta_height = abs(float(horizon_metadata["observer_height_m"]) - float(observer["observer_height_m"]))
    if delta_lat > 1e-5 or delta_lon > 1e-5 or delta_elev > 0.1 or delta_height > 0.01:
        raise ValueError("Observer mismatch: horizon and celestial coordinates do not describe the same site.")


def verify_recorded_snapshot(horizon, celestial, snapshot, tolerance_deg=0.015):
    check_observer_match(horizon["metadata"], celestial["site"])
    check_observer_match(horizon["metadata"], snapshot["site"])
    if celestial["date_utc"] != snapshot["date_utc"]:
        raise ValueError("Recorded observation timestamps do not agree.")
    for body in ("sun", "earth"):
        raw = celestial[body]
        observed = snapshot["bodies"][body]
        expected = horizon_at(horizon, raw["azimuth_deg"])
        if expected is None:
            raise ValueError(f"Terrain horizon is unknown at the {body} azimuth.")
        if abs(expected - float(observed["terrain_horizon_elevation_deg"])) > tolerance_deg:
            raise ValueError(f"Recorded {body} horizon does not match the LOLA profile.")
        if abs(float(raw["elevation_deg"]) - float(observed["body_center_elevation_deg"])) > tolerance_deg:
            raise ValueError(f"Recorded {body} elevation differs from the input positions.")
    return True
