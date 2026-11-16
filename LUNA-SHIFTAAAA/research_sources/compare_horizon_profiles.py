
import json
import numpy as np
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

def load_profile(filename):
    with (BASE_DIR / filename).open(
        "r", encoding="utf-8"
    ) as file:
        return json.load(file)

profile_80 = load_profile("horizon_80km.json")
profile_120 = load_profile("horizon_120km.json")

def samples_by_azimuth(profile):
    return {
        round(float(s["azimuth_deg"]), 5): s
        for s in profile["samples"]
        if s["horizon_elevation_deg"] is not None
    }

samples_80 = samples_by_azimuth(profile_80)
samples_120 = samples_by_azimuth(profile_120)

common_azimuths = sorted(
    set(samples_80) & set(samples_120)
)

if not common_azimuths:
    raise ValueError("No common azimuth directions found.")

differences = np.array([
    abs(
        samples_80[az]["horizon_elevation_deg"]
        - samples_120[az]["horizon_elevation_deg"]
    )
    for az in common_azimuths
])

print("\nHORIZON PROFILE COMPARISON")
print("=" * 45)
print(f"Common directions: {len(common_azimuths)}")
print(f"Maximum angular difference: {differences.max():.6f} deg")
print(f"Mean angular difference: {differences.mean():.6f} deg")
print(f"Directions with difference > 0.01 deg: {np.sum(differences > 0.01)}")

if np.all(differences < 0.01):
    print("\nRESULT: Profiles agree within 0.01 deg.")
else:
    print("\nRESULT: Differences require investigation.")
