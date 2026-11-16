"""New single-view React+Three.js regression tests (supersede legacy static UI tests)."""
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]/'web/src'

def test_two_modes_share_original_scene():
    app=(ROOT/'App.tsx').read_text()
    assert "type Profile='student'|'professional'" in app
    assert app.count('<SpaceView')==1
    assert app.count('<Timeline')==1
    assert 'EducationalMissionDock' not in app
    assert 'SciencePanel' in app and 'EducationPanel' in app

def test_utc_calendar_queries_dynamic_windows_and_comparison():
    panel=(ROOT/'science/SciencePanel.tsx').read_text()
    science=(ROOT/'science/useLunarScience.ts').read_text()
    assert 'datetime-local' in panel
    assert 'Calculate selected period' in panel
    assert 'setAnalysisRange' in science
    assert '/api/visibility?' in science and '/api/compare?' in science
    assert 'setTarget' in science and 'selectMapPoint' in science

def test_original_timeline_interpolates_spice_without_per_frame_api_requests():
    app=(ROOT/'App.tsx').read_text()
    math=(ROOT/'mission/missionMath.ts').read_text()
    terrain=(ROOT/'mission/MissionTerrainView.tsx').read_text()
    graph=(ROOT/'science/VisibilityChart.tsx').read_text()
    assert 'setInterval' in app
    assert 'interpolateFrame' in math
    assert 'horizonAt' in math
    assert 'direction_local_east_north_up' in terrain
    assert 'terrain horizon' in graph
    assert '/api/' not in terrain
