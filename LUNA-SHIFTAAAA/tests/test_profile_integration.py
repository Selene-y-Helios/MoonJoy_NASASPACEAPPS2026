"""Regression checks for the single-scene Daniela/LOLA/SPICE integration."""
from pathlib import Path

from fastapi.testclient import TestClient
from backend.api import app

ROOT = Path(__file__).resolve().parents[1]
client = TestClient(app)


def test_nasa_student_catalog_is_separate_from_polar_dem():
    response = client.get('/api/education/missions')
    assert response.status_code == 200
    catalog = response.json()
    assert catalog['count'] == 5
    assert {item['id'] for item in catalog['missions']} == {
        'surveyor-1', 'apollo-11', 'apollo-12', 'apollo-15', 'apollo-17'
    }
    assert all(item['latitude_deg'] > -80 for item in catalog['missions'])
    assert all(item['sources'] for item in catalog['missions'])


def test_all_profiles_render_the_same_original_spaceview_and_timeline():
    frontend = (ROOT / 'web/src/App.tsx').read_text(encoding='utf-8')
    for profile in ['student', 'professional']:
        assert f"profile==='{profile}'" in frontend
    assert "profile==='game'" not in frontend
    assert 'EducationalMissionDock' not in frontend
    assert 'Mission Challenge' not in frontend
    assert frontend.count('<SpaceView') == 1
    assert frontend.count('<Timeline') == 1
    assert 'EducationPanel' in frontend
    assert 'SciencePanel' in frontend
    assert 'MissionTerrainView' in frontend
    assert 'onSouthPoleArrival' in frontend
    assert 'onPolarPick' in frontend
    assert 'MissionControl' not in frontend  # No alternate full-screen interface.
    assert (ROOT / 'web/src/components/SpaceView.tsx').exists()
    assert (ROOT / 'web/src/components/Timeline.tsx').exists()


def test_professional_uses_existing_scientific_api_without_mock_values():
    science = (ROOT / 'web/src/science/useLunarScience.ts').read_text(encoding='utf-8')
    panel = (ROOT / 'web/src/science/SciencePanel.tsx').read_text(encoding='utf-8')
    for route in ['/api/site?', '/api/horizon?', '/api/terrain?', '/api/visibility?', '/api/compare?', '/api/site/from-map?']:
        assert route in science
    assert 'CraterExplorer' in panel
    assert 'VisibilityChart' in panel
    assert 'POINT A / B COMPARISON' in panel
    for label in ['SITE CONDITIONS', '360° TERRAIN HORIZON', 'OPERATIONAL WINDOWS', 'POINT A / B COMPARISON']:
        assert label in panel
    assert 'interpolateFrame' in science
    assert 'setInterval' not in science
    assert 'No simultaneous Sun/Earth visibility window' in panel


def test_polar_zoom_targets_actual_selected_site_and_keeps_original_moon():
    scene = (ROOT / 'web/src/components/SpaceView.tsx').read_text(encoding='utf-8')
    assert "cameraFocus === 'southPole'" in scene
    assert 'onSouthPoleArrival' in scene
    assert 'onPolarPick' in scene
    assert 'MoonBody' in scene


def test_real_dem_endpoint_if_user_assets_are_installed():
    if not (ROOT / 'data/dem/LDEM_80S_80MPP_ADJ.TIF').exists():
        import pytest
        pytest.skip('NASA DEM is optional in the code-only package.')
    response = client.get('/api/site', params={
        'latitude_deg': -89.8026005358603,
        'longitude_deg_east': 155.95074562959945,
    })
    assert response.status_code == 200
    assert response.json()['elevation_dem'].lower().endswith('.tif')
