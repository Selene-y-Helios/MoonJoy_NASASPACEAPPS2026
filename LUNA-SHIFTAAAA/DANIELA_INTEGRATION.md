# Handoff to Daniela — preserve SpaceView

- The original source comes from the team's `lunar-spaceview(2).zip`, using the same `SpaceView.tsx`, `Timeline.tsx`, `style.css`, colors and single-scene layout. The scene has only the minimal extra click handler for the south pole.
- The integration is **additive** in `web/src/science` plus a 3D terrain overlay in `web/src/mission/MissionTerrainView.tsx`; there are exactly two visible modes. No independent scientific frontend is served.
- In Professional, map selection is routed to `/api/site/from-map` and triggers per-site `/api/horizon`, `/api/terrain`, `/api/visibility`; selecting B triggers `/api/compare`, using separate horizons. The uploaded Shackleton JSON is only a fixed-site reference, served by `/api/reference/shackleton/summary`.
- UTC range is controlled by `SciencePanel.tsx` and `useLunarScience.ts`, not by the illustrative orbital animation. The 3D surface Sun/Earth directions interpolate the scientific SPICE timeline.
- Educational gets five actual NASA landing histories from `/api/education/missions`; it never applies the south-polar DEM to Apollo locations.
- The `web/public` Moon and Earth images are Daniela's original demo textures; the polar terrain geometry comes from NASA LOLA DEMs.
- Run `python -m pytest -q` in the project root and `npm run build` in `web` after `npm ci` on Windows.
