"""Verify required NASA/JPL assets and source files from the GitHub checkout.

Uses only the Python standard library. Rejects missing, truncated, or Git LFS
pointer files before the FastAPI application is started.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CHECKS = ROOT / 'NASA_DATA_SHA256.json'
PROJECT_FILES = (
    'backend/api.py',
    'backend/orbit_ephemeris.py',
    'web/src/App.tsx',
    'web/src/components/SpaceView.tsx',
    'web/src/mission/MissionTerrainView.tsx',
    'web/src/lib/useSpiceOrbit.ts',
    'web/public/NASA_Moon_LROC_2K.jpg',
    'web/public/NASA_Moon_LOLA_Height_1K.jpg',
    'web/public/NASA_Earth_BlueMarble_2K.png',
    'web/public/lunar_regolith_visual.jpg',
    'web/public/lunar_regolith_bump.jpg',
    'data/education/lunar_missions.sqlite',
)


def verify():
    missing = [name for name in PROJECT_FILES if not (ROOT / name).is_file()]
    if missing:
        raise RuntimeError('Missing project files: ' + ', '.join(missing))
    manifest = json.loads(CHECKS.read_text(encoding='utf-8'))
    for rel, expected in manifest['files'].items():
        path = ROOT / rel
        if not path.is_file():
            raise RuntimeError(f'Missing NASA/JPL asset: {rel}. Try git lfs pull.')
        size = path.stat().st_size
        if size != expected['bytes']:
            raise RuntimeError(f'Incorrect asset size for {rel}: {size} bytes, expected {expected["bytes"]}. Try git lfs pull.')
        digest = hashlib.sha256()
        with path.open('rb') as reader:
            for chunk in iter(lambda: reader.read(1024 * 1024), b''):
                digest.update(chunk)
        if digest.hexdigest() != expected['sha256']:
            raise RuntimeError(f'Integrity check failed for {rel}. Use the exact source data.')
        print(f'OK: {rel} ({size:,} bytes)')
    print('PASS: All 7 NASA/JPL files and required web sources are present.')


if __name__ == '__main__':
    try:
        verify()
    except (OSError, ValueError, KeyError, RuntimeError) as error:
        print('FAIL:', error)
        raise SystemExit(1) from error
