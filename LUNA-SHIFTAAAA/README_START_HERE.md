# LUNA SHIFT — Daniela SpaceView + NASA science (two modes)

## What is included
This project keeps **Daniela's original React + Three.js SpaceView layout** as the shared viewer. Two modes only:
- **Educational:** interactive NASA-textured lunar globe with five historical NASA missions and the **Learn** information panel. Earth–Sun and Moon–Earth orbital positions and curves use JPL DE440 when SPICE is available; illustrative fallback is explicitly labeled when unavailable.
- **Professional:** the same globe with a **South Pole** zoom into a LOLA DEM-based first-person view and an integrated NASA Science Data panel with a polar elevation map, named crater context, A/B selection, a custom UTC date-range calendar, JPL SPICE Sun/Earth positions, 360-degree horizon, visibility graphs, communications opportunities and comparisons.

## Install on Windows (step by step)
1. **Extract this complete ZIP into a new folder**, without overwriting the original Daniela project or your prior working installation.
2. When cloning from GitHub, run `git lfs pull` after checkout. The `data/dem` and `data/kernels` source assets are tracked through Git LFS. If running this package before uploading, these assets are already present; never move/delete the originals.
3. Confirm the following exist:
   - `data/dem/LDEM_80S_80MPP_ADJ.TIF` (regional LOLA model)
   - `data/dem/Site04_final_adj_5mpp_surf.tif` (optional higher resolution local Shackleton model)
   - `data/kernels/naif0012.tls`, `de440s.bsp`, `moon_pa_de440_200625.bpc`, `moon_de440_250416.tf`, `pck00011.tpc`
4. Install **Python 3.12/3.13** and **Node.js 22** if needed. The launchers create a Python environment and install dependencies at first run.
5. Double-click `START_ALL.bat`, keep the API and WEBSITE windows open. The first installation can require an internet connection.
6. Open the **Local** address printed by Vite, e.g. `http://localhost:5173/` or `http://localhost:5174/` if the first port is occupied. The backend health check is `http://127.0.0.1:8000/api/health`.

## Professional use
1. Select **Professional** (top navigation). Open **Science Data** if closed.
2. Choose **Place Point A** and click a **valid pixel** on the south-pole elevation map; this is a geographic, topographically precise pick.
3. Choose **Place Point B** and click another valid pixel. Both markers remain on the map. Crater labels identify geographic landmarks only; crater centers are not certified landing sites.
4. Enter **Start UTC** and **End UTC** in the calendar and click **Calculate selected period**. Set sampling resolution to 15/30/60/120 min; ranges up to 31 days and 3000 samples are supported.
5. Inspect separate Earth and Sun elevation/horizon time-series and the numeric tables, Earth visibility windows, the A/B comparison and which option has the longer uninterrupted combined Sun + Earth window. Download comparison CSV if needed.
6. Click **Explore selected site in 3D** to zoom from the original Moon to the LOLA first-person landscape. The shared Play and UTC timeline controls move the Sun/Earth markers according to sampled SPICE output (not invented orbital geometry).

## Educational use
Select **Educational** and choose from exactly **five historical NASA landing sites**. Press a labeled marker on the same Moon or select its name from the left menu. **Learn** shows its landing date, geographic location, historical achievement, one short learning question and NASA sources. The orbital positions and curves come from geometric JPL DE440 ephemerides whenever the SPICE API is available; inter-body distances are visually rescaled and body texture rotations remain illustrative. If the API is missing, a clearly labeled illustrative fallback is used.

## Research inputs retained separately
- `data/reference/shackleton/horizon_80km.json`: fixed 80 km horizon for a specific Shackleton observer.
- `data/reference/shackleton/horizon_120km.json`: 120 km higher-angular-resolution fixed horizon.
- `data/reference/shackleton/visibility_results.json`: supplied 2026-11-14 to 2026-11-21 reference timeline with **zero Sun and Earth visible hours** at that specific site, reproduced in the clearly labeled fixed-reference table.
- `data/reference/shackleton/lunar_site_other_observer.json`: another input point (distinct coordinates), never mixed with the same-observer reference horizon.

**Critical:** A and B are not computed by copying a single-site reference JSON. `/api/visibility` and `/api/compare` recompute independent horizons and SPICE windows from each selected site and the chosen UTC period using the real DEM/kernels.

**Science limits:** This is preliminary geometric body-center visibility against a sampled terrain horizon. No RF link budget, antenna patterns, actual generated solar power, thermal modeling, landing hazard classification or mission qualification is provided. DEM lunar frame compatibility requires further cross-validation. A site with zero confirmed visibility is never labeled favorable.

## GitHub distribution

For repository upload, Git LFS, cloning instructions and the 7-file NASA data integrity checks, read **README_GITHUB_ES.md** and run `python tools/verify_github_package.py`.
