"""Tests only verify file consistency and interface behavior, not scientific validity."""
import json
from pathlib import Path

from backend.horizon_utils import load_horizon, horizon_at, verify_recorded_snapshot, check_observer_match

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "shackleton"


def test_recorded_snapshot_same_site():
    horizon = load_horizon(DATA / "horizon_profile.json")
    celestial = json.loads((DATA / "celestial_positions.json").read_text())
    snapshot = json.loads((DATA / "snapshot_visibility_shackleton.json").read_text())
    assert verify_recorded_snapshot(horizon, celestial, snapshot)
    assert snapshot["bodies"]["sun"]["center_above_terrain_horizon"] is False
    assert snapshot["bodies"]["earth"]["center_above_terrain_horizon"] is False


def test_horizon_wraparound():
    horizon = load_horizon(DATA / "horizon_profile.json")
    assert abs(horizon_at(horizon, 360) - horizon_at(horizon, 0)) < 1e-9
    assert abs(horizon_at(horizon, -1) - horizon_at(horizon, 359)) < 1e-9


def test_engineering_reference_different_site():
    horizon = load_horizon(DATA / "horizon_profile.json")
    try:
        check_observer_match(horizon["metadata"], {
            "latitude_deg": -89.5, "longitude_deg_east": 0,
            "dem_elevation_m": 0, "observer_height_m": 0,
        })
    except ValueError as err:
        assert "mismatch" in str(err).lower()
    else:
        raise AssertionError("The integration must reject the other lunar site.")


def test_api_requires_selected_coordinates():
    from fastapi.testclient import TestClient
    from backend.api import app
    client = TestClient(app)
    response = client.get('/api/snapshot', params={'at': '2026-11-14T12:00:00Z'})
    assert response.status_code == 422
    reference = client.get('/api/reference/test-south-pole')
    assert reference.status_code == 200
    assert reference.json()['can_merge_with_shackleton'] is False
    assert client.get('/api/health').status_code == 200
