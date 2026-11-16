"""Tests for two-site intervals and API wiring, without NASA datasets or SPICE kernels."""
from datetime import datetime, timezone
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend import api
from backend.site_comparison import intersect_opportunities, summarize_opportunity


def window(start: str, end: str) -> dict:
    return {"start_utc": f"2026-11-14T{start}Z", "end_utc": f"2026-11-14T{end}Z"}


def test_opportunity_summary():
    item = summarize_opportunity([
        window("01:00:00", "03:00:00"),
        window("04:00:00", "04:30:00"),
    ])
    assert item["total_hours"] == 2.5
    assert item["longest_window_hours"] == 2.0
    assert item["window_count"] == 2
    assert item["windows"][1]["duration_hours"] == 0.5


def test_intersection_multiple_windows_and_no_overlap():
    a = [window("01:00:00", "04:00:00"), window("05:00:00", "06:00:00")]
    b = [window("02:00:00", "03:00:00"), window("04:00:00", "05:30:00")]
    common = intersect_opportunities(a, b)
    assert common["window_count"] == 2
    assert common["total_hours"] == 1.5
    assert common["longest_window_hours"] == 1.0
    assert common["windows"][1]["start_utc"] == "2026-11-14T05:00:00Z"
    assert common["windows"][1]["end_utc"] == "2026-11-14T05:30:00Z"
    assert intersect_opportunities([window("00:00:00", "01:00:00")],
                                   [window("01:00:00", "02:00:00")])["window_count"] == 0


def test_intersection_merges_adjacent_pieces():
    a = [window("01:00:00", "04:00:00")]
    b = [window("01:00:00", "02:00:00"), window("02:00:00", "04:00:00")]
    shared = intersect_opportunities(a, b)
    assert shared["window_count"] == 1
    assert shared["longest_window_hours"] == 3.0


def test_invalid_window_rejected():
    with pytest.raises(ValueError, match="positive"):
        summarize_opportunity([window("03:00:00", "01:00:00")])
    with pytest.raises(ValueError, match="out of order"):
        intersect_opportunities([
            window("03:00:00", "04:00:00"),
            window("02:00:00", "03:00:00"),
        ], [])


def test_compare_api_uses_separate_observers(monkeypatch):
    requested = []

    def fake_resolve(lat, lon, height):
        return {
            "latitude_deg": float(lat),
            "longitude_deg_east": float(lon) % 360,
            "observer_height_m": float(height),
            "dem_elevation_m": -1234.0,
        }

    def fake_horizon(site):
        label = "A" if site["latitude_deg"] == -89.8 else "B"
        return ({"metadata": {
            "latitude_deg": site["latitude_deg"],
            "longitude_deg_east": site["longitude_deg_east"],
            "observer_height_m": site["observer_height_m"],
            "dem_elevation_m": site["dem_elevation_m"],
        }}, Path(f"{label}.json"))

    def fake_spice(begin, finish, step, horizon_path):
        label = horizon_path.stem
        requested.append((label, begin, finish, step))
        windows = ([window("01:00:00", "04:00:00"), window("05:00:00", "06:00:00")]
                   if label == "A" else
                   [window("02:00:00", "03:00:00"), window("04:00:00", "05:30:00")])
        visible = 4 if label == "A" else 2.5
        return {
            "metadata": {
                "start_utc": "2026-11-14T00:00:00Z",
                "end_utc": "2026-11-14T06:00:00Z",
                "warnings": ["Synthetic API test only"],
            },
            "summary": {
                "sun": {"visible_hours": 5, "visible_percent_of_interval": 83.333, "unknown_hours": 0},
                "earth": {"visible_hours": 4, "visible_percent_of_interval": 66.667, "unknown_hours": 0},
                "both": {"visible_hours": visible, "visible_percent_of_interval": visible/6*100, "unknown_hours": 0},
            },
            "windows": {"both": windows},
        }

    monkeypatch.setattr(api, "site_from_query", fake_resolve)
    monkeypatch.setattr(api, "profile_for", fake_horizon)
    monkeypatch.setattr(api, "run_spice", fake_spice)

    client = TestClient(api.app)
    params = {
        "a_latitude_deg": -89.8, "a_longitude_deg_east": 155.95,
        "b_latitude_deg": -89.5, "b_longitude_deg_east": 20.0,
        "start": "2026-11-14T00:00:00Z",
        "end": "2026-11-14T06:00:00Z", "step_minutes": 15,
    }
    response = client.get("/api/compare", params=params)
    assert response.status_code == 200, response.text
    result = response.json()
    assert [x[0] for x in requested] == ["A", "B"]
    assert requested[0][1:] == requested[1][1:]
    assert result["points"]["A"]["opportunity"]["total_hours"] == 4.0
    assert result["points"]["B"]["opportunity"]["longest_window_hours"] == 1.5
    assert result["shared_opportunity"]["total_hours"] == 1.5
    assert result["shared_opportunity"]["window_count"] == 2
    assert result["points"]["A"]["site"]["longitude_deg_east"] == 155.95
    assert result["points"]["B"]["site"]["longitude_deg_east"] == 20
    assert "timeline" not in result

    same = dict(params, b_latitude_deg=-89.8, b_longitude_deg_east=155.95)
    assert client.get("/api/compare", params=same).status_code == 422
    reverse = dict(params, start=params["end"], end=params["start"])
    assert client.get("/api/compare", params=reverse).status_code == 422
    invalid_coord = dict(params, b_latitude_deg=-75)
    assert client.get("/api/compare", params=invalid_coord).status_code == 422


def test_frontend_comparison_controls():
    root = Path(__file__).resolve().parents[1] / 'web/src'
    map_src = (root / 'science/CraterExplorer.tsx').read_text()
    science = (root / 'science/useLunarScience.ts').read_text()
    panel = (root / 'science/SciencePanel.tsx').read_text()
    for control in ('Place Point A','Place Point B','science-map-pin','selectMapPoint'):
        assert control in map_src
    for route in ('/api/compare?', '/api/visibility?'):
        assert route in science
    assert 'POINT A / B COMPARISON' in panel
    assert 'DIRECT EARTH VIEW WINDOWS' in panel
