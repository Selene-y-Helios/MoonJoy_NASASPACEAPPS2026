"""Audit the engineering / terrain files before using them together."""
from pathlib import Path
import json

from .horizon_utils import load_horizon, verify_recorded_snapshot, horizon_at

ROOT = Path(__file__).resolve().parents[1]
SHACKLETON = ROOT / 'data' / 'shackleton'
REFERENCE = ROOT / 'data' / 'test_south_pole'
REPORT_PATH = ROOT / 'merge_report.json'


def main():
    horizon = load_horizon(SHACKLETON / 'horizon_profile.json')
    celestial = json.loads((SHACKLETON / 'celestial_positions.json').read_text(encoding='utf-8'))
    snapshot = json.loads((SHACKLETON / 'snapshot_visibility_shackleton.json').read_text(encoding='utf-8'))
    engineering = json.loads((REFERENCE / 'earth_positions.json').read_text(encoding='utf-8'))
    ref_windows = json.loads((REFERENCE / 'visibility_windows.json').read_text(encoding='utf-8'))
    verify_recorded_snapshot(horizon, celestial, snapshot)
    site = horizon['metadata']
    other = engineering['observer']
    matching = (abs(site['latitude_deg'] - other['latitude_deg']) < 1e-5 and
                abs(((site['longitude_deg_east'] - other['longitude_e_deg'] + 180) % 360) - 180) < 1e-5)
    if matching:
        raise RuntimeError('Unexpected site match; reference file classification needs review.')
    report = {
        'selected_site_id': 'shackleton',
        'selected_site': {
            'latitude_deg': site['latitude_deg'],
            'longitude_deg_east': site['longitude_deg_east'],
            'dem_elevation_m': site['dem_elevation_m'],
            'observer_height_m': site['observer_height_m'],
        },
        'same_site_recorded_snapshot_validated_internally': True,
        'snapshot_timestamp_utc': celestial['date_utc'],
        'snapshot_body_center_visibility': {name: val['center_above_terrain_horizon'] for name, val in snapshot['bodies'].items()},
        'engineering_horizons_site_id': engineering['site_id'],
        'engineering_horizons_observer': other,
        'engineering_horizons_samples': len(engineering['positions']),
        'engineering_reference_window_count': ref_windows['visible_window_count'],
        'engineering_horizons_usable_at_shackleton': False,
        'reason': 'Engineering Horizons positions are from a different lunar location and compare Earth center to 0 degrees, not Shackleton terrain.',
        'scientific_status': 'preliminary; coordinate frames and DEM datum require independent validation',
    }
    REPORT_PATH.write_text(json.dumps(report, indent=2), encoding='utf-8')
    print('Merge audit completed successfully.')
    print('Same-site Shackleton recorded snapshot: consistent with the attached horizon.')
    print(f'Engineering Horizons sample count: {len(engineering["positions"])}')
    print('Engineering Horizons observer matches Shackleton: NO')
    print('Do not use geometric zero-degree Earth windows as Shackleton visibility windows.')
    print(f'Report: {REPORT_PATH}')


if __name__ == '__main__':
    main()
