
import json
from pathlib import Path
import numpy as np

PROFILE_FILE = Path("horizon_profile.json")

with PROFILE_FILE.open("r", encoding="utf-8") as file:
    profile = json.load(file)

samples = [
    sample
    for sample in profile["samples"]
    if sample["horizon_elevation_deg"] is not None
]

angles = np.array([
    sample["horizon_elevation_deg"]
    for sample in samples
])

distances = np.array([
    sample["obstacle_distance_m"]
    for sample in samples
])

missing = np.array([
    sample["missing_sample_fraction"]
    for sample in samples
])

print("\nLUNAR HORIZON VALIDATION")
print("=" * 45)

print(f"Valid directions: {len(samples)}")
print(f"Minimum horizon: {angles.min():.3f} deg")
print(f"Maximum horizon: {angles.max():.3f} deg")
print(f"Mean horizon: {angles.mean():.3f} deg")

print(
    f"Nearest dominant obstacle: "
    f"{distances.min() / 1000:.3f} km"
)

print(
    f"Farthest dominant obstacle: "
    f"{distances.max() / 1000:.3f} km"
)

print(
    f"Maximum missing sample fraction: "
    f"{missing.max():.2%}"
)

print("\nSELECTED AZIMUTHS")
print("=" * 45)

for azimuth in [0, 45, 90, 135, 180, 225, 270, 315]:
    sample = min(
        samples,
        key=lambda s: abs(
            s["azimuth_deg"] - azimuth
        )
    )

    print(
        f"Azimuth: {sample['azimuth_deg']:6.1f} deg | "
        f"Horizon: {sample['horizon_elevation_deg']:7.3f} deg | "
        f"Obstacle: {sample['obstacle_distance_m'] / 1000:8.3f} km | "
        f"Missing: {sample['missing_sample_fraction']:.1%}"
    )
