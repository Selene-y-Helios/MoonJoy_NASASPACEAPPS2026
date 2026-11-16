from fastapi.testclient import TestClient
from backend import api


def test_mission_endpoint_uses_existing_scientific_visibility(monkeypatch, tmp_path):
    monkeypatch.setattr(api, 'site_from_query', lambda lat, lon, h: {
        'latitude_deg': lat, 'longitude_deg_east': lon, 'observer_height_m': h,
        'dem_elevation_m': -1343.6, 'elevation_dem': 'test.tif',
    })
    monkeypatch.setattr(api, 'profile_for', lambda site: ({'metadata': {}}, tmp_path / 'profile.json'))
    def fake_spice(start, end, step, horizon_file):
        return {'summary': {'sun': {'visible_hours': 8}, 'earth': {'visible_hours': 9}, 'both': {'visible_hours': 4}},
                'windows': {'both': [{'start_utc': '2026-11-14T13:00:00Z',
                                      'end_utc': '2026-11-14T17:00:00Z', 'duration_hours': 4}]},
                'metadata': {'warnings': ['synthetic test data']}}
    monkeypatch.setattr(api, 'run_spice', fake_spice)
    client = TestClient(api.app)
    body = {'latitude_deg': -89.8026, 'longitude_deg_east': 155.95,
            'analysis_start': '2026-11-14T00:00:00Z',
            'analysis_end': '2026-11-15T00:00:00Z',
            'operation_start': '2026-11-14T14:00:00Z',
            'duration_hours': 2, 'delay_hours': 12, 'step_minutes': 15}
    result = client.post('/api/mission/evaluate', json=body)
    assert result.status_code == 200
    assert result.json()['passed'] is True
    assert result.json()['site']['latitude_deg'] == -89.8026
    body['operation_start'] = '2026-11-14T16:00:00Z'
    fail = client.post('/api/mission/evaluate', json=body)
    assert fail.status_code == 200
    assert fail.json()['passed'] is False
    assert fail.json()['checks']['continuous_sun_earth_visibility'] is False


def test_mission_endpoint_rejects_outside_coverage_and_bad_period():
    client = TestClient(api.app)
    body = {'latitude_deg': -45, 'longitude_deg_east': 120,
            'analysis_start': '2026-11-14T00:00:00Z',
            'analysis_end': '2026-11-15T00:00:00Z',
            'operation_start': '2026-11-14T14:00:00Z'}
    assert client.post('/api/mission/evaluate', json=body).status_code == 422
    body['latitude_deg'] = -89.8
    body['analysis_end'] = body['analysis_start']
    assert client.post('/api/mission/evaluate', json=body).status_code == 422
