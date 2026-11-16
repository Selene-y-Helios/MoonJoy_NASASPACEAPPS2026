# LUNA SHIFT — Daniela's SpaceView + NASA Science

**Two modes in ONE interface:** Educational (five historical NASA lunar landings + Learn) and Professional (polar map, A/B sites, LOLA horizon/terrain, JPL SPICE Sun and Earth visibility, UTC calendar, 3D animation, communication opportunity windows and A/B tradeoffs).

For installation and scientific caveats, read **README_START_HERE.md**.

The current site is a research demonstrator; geometric Earth visibility is not a radio link budget or a landing safety guarantee.

## DE440 orbital update and GitHub release

JPL SPICE DE440 provides the geometric Earth/Sun and Moon/Earth orbital vectors and sampled paths (`/api/orbits`). The 3D scene rescales distances for visibility and leaves the existing NASA texture mappings unchanged. Original LOLA terrain and A/B scientific analysis remain separate. **To reproduce the complete project from GitHub, install Git LFS and use `git lfs pull`**. See `README_GITHUB_ES.md` and `NASA_DATA_SHA256.json` for release instructions and integrity checks.
