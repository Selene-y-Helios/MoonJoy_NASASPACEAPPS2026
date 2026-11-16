"""Optional NASA/JPL Horizons cross-check for the exact Shackleton observer.

This adapts the engineering-team Horizons method without retaining its old
-89.5 / 0.0 lunar observer. It never overwrites the main SPICE predictions.
"""

import argparse
import csv
import io
import json
from datetime import datetime, timezone
from pathlib import Path

import requests

from .horizon_utils import load_horizon

ROOT = Path(__file__).resolve().parents[1]
HORIZON_PATH = ROOT / "data" / "shackleton" / "horizon_profile.json"
OUTPUT = ROOT / "data" / "shackleton" / "earth_positions_horizons_crosscheck.json"
API_URL = "https://ssd.jpl.nasa.gov/api/horizons.api"


def quote(value):
    return "'" + str(value) + "'"


def fetch(start, end, step="15m"):
    profile = load_horizon(HORIZON_PATH)
    meta = profile["metadata"]
    latitude = float(meta["latitude_deg"])
    longitude = float(meta["longitude_deg_east"])
    elevation_km = (float(meta["dem_elevation_m"]) + float(meta["observer_height_m"])) / 1000.0
    params = {
        "format": "json",
        "COMMAND": quote("399"),
        "CENTER": quote("coord@301"),
        "COORD_TYPE": quote("GEODETIC"),
        "SITE_COORD": quote(f"{longitude:.10f},{latitude:.10f},{elevation_km:.9f}"),
        "MAKE_EPHEM": quote("YES"),
        "EPHEM_TYPE": quote("OBSERVER"),
        "OBJ_DATA": quote("NO"),
        "START_TIME": quote(start),
        "STOP_TIME": quote(end),
        "STEP_SIZE": quote(step),
        "QUANTITIES": quote("4"),
        "CSV_FORMAT": quote("YES"),
        "TIME_DIGITS": quote("MINUTES"),
        "ANG_FORMAT": quote("DEG"),
        "ELEV_CUT": quote("-90"),
        "SKIP_DAYLT": quote("NO"),
    }
    response = requests.get(API_URL, params=params, timeout=90)
    response.raise_for_status()
    payload = response.json()
    if payload.get("error"):
        raise RuntimeError(payload["error"])
    text = payload.get("result", "")
    if "$$SOE" not in text or "$$EOE" not in text:
        raise RuntimeError("Horizons did not return an ephemeris table. " + text[-1000:])
    table = text.split("$$SOE", 1)[1].split("$$EOE", 1)[0]
    positions = []
    for record in csv.reader(io.StringIO(table)):
        fields = [v.strip() for v in record]
        while fields and not fields[-1]:
            fields.pop()
        if not fields:
            continue
        try:
            instant = datetime.strptime(fields[0], "%Y-%b-%d %H:%M").replace(tzinfo=timezone.utc)
            azimuth = float(fields[-2]); elevation = float(fields[-1])
        except (ValueError, IndexError) as exc:
            raise ValueError(f"Unrecognized Horizons row: {record!r}") from exc
        positions.append({
            "time_utc": instant.isoformat().replace("+00:00", "Z"),
            "az_deg": azimuth,
            "el_deg": elevation,
        })
    if not positions:
        raise RuntimeError("No Horizons positions were returned.")
    return {
        "source": "NASA/JPL Horizons API",
        "site_id": "shackleton",
        "observer": {
            "body": "Moon",
            "longitude_e_deg": longitude,
            "latitude_deg": latitude,
            "altitude_km": elevation_km,
            "observer_height_m": float(meta["observer_height_m"]),
        },
        "target": "Earth center",
        "sampling_step": step,
        "reference": "Apparent, airless, topocentric azimuth/elevation",
        "terrain_horizon_applied": False,
        "notes": [
            "Same-site Horizons cross-check, not a replacement for LOLA horizon visibility.",
            "Horizon/DEM and Horizons lunar body-frame and altitude conventions require independent verification.",
            "Horizons apparent directions are not identical to SPICE geometric NONE corrections."
        ],
        "positions": positions,
    }


def main():
    parser = argparse.ArgumentParser(description="Request NASA Horizons Earth angles for Shackleton only.")
    parser.add_argument("--start", default="2026-11-14 00:00")
    parser.add_argument("--end", default="2026-11-15 00:00")
    parser.add_argument("--step", default="15m")
    args = parser.parse_args()
    result = fetch(args.start, args.end, args.step)
    OUTPUT.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(f"Saved {len(result['positions'])} same-site Earth positions: {OUTPUT}")
    print("NOTICE: This file does not establish direct-to-Earth radio link availability.")


if __name__ == "__main__":
    main()
