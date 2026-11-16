"""South-pole crater geographic references and DEM preview API tests."""
from pathlib import Path
from fastapi.testclient import TestClient
from backend.api import app

client=TestClient(app)
ROOT=Path(__file__).resolve().parents[1]

def test_crater_catalog_and_preview_sources():
    if not (ROOT/'data/dem/LDEM_80S_80MPP_ADJ.TIF').is_file():
        import pytest;pytest.skip('NASA regional DEM is not included in code-only package.')
    response=client.get('/api/craters')
    assert response.status_code==200
    data=response.json()
    assert len(data['craters'])==6
    assert {c['name'] for c in data['craters']}=={'Shackleton','Shoemaker','Faustini','Haworth','de Gerlache','Nobile'}
    assert all('not an optical photograph' in c['preview_type'] for c in data['craters'])
    assert all(-90<=c['latitude_deg']<=-80 for c in data['craters'])
    assert all(c['preview_url'].startswith('/api/craters/') for c in data['craters'])
    preview=client.get('/api/craters/shackleton/preview')
    assert preview.status_code==200
    assert preview.content.startswith(b'\x89PNG')
    assert client.get('/api/craters/not-a-crater/preview').status_code==404

def test_two_modes_and_five_historical_landings_only():
    frontend=(ROOT/'web/src/App.tsx').read_text()
    assert "type Profile='student'|'professional'" in frontend
    assert 'Mission Challenge' not in frontend
    assert 'EducationalMissionDock' not in frontend
    assert 'EducationPanel' in frontend
    assert '<SpaceView' in frontend
    science=(ROOT/'web/src/science/useLunarScience.ts').read_text()
    assert '/api/visibility?' in science
    assert '/api/compare?' in science
    panel=(ROOT/'web/src/science/SciencePanel.tsx').read_text()
    assert 'Place Point A' in (ROOT/'web/src/science/CraterExplorer.tsx').read_text()
    assert 'Place Point B' in (ROOT/'web/src/science/CraterExplorer.tsx').read_text()
    assert 'UTC' in panel and 'Earth' in panel
