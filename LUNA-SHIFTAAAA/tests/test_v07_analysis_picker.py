"""UI contract regression: independently chosen UTC period and distinct polar points."""
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def test_analysis_period_is_configurable_and_not_tied_to_scrubber():
    hook=(ROOT/'web/src/science/useLunarScience.ts').read_text()
    panel=(ROOT/'web/src/science/SciencePanel.tsx').read_text()
    assert 'setAnalysisRange' in hook and "setAnalysis({start:nextStart,end:nextEnd,step:nextStep})" in hook
    assert "const start=missionBaseline?" in hook
    for name in ['Analysis start UTC','Analysis end UTC','Sampling interval','Calculate selected period']:
        assert name in panel
    assert 'science.visibility.windows.earth.map' in panel
    assert 'science.visibility.windows.both.map' in panel

def test_point_b_can_be_created_from_map_and_coordinates():
    app=(ROOT/'web/src/App.tsx').read_text()
    panel=(ROOT/'web/src/science/SciencePanel.tsx').read_text()
    mapview=(ROOT/'web/src/science/CraterExplorer.tsx').read_text()
    assert "science.selectCoordinates(lat,lon,science.target)" in app
    assert "science.selectCoordinates(Number(lat),Number(lon),science.target)" in panel
    assert "science.selectMapPoint(x,y,science.target)" in mapview
    assert 'Currently placing' in mapview and 'POINT {science.target}' in mapview
    assert 'earth_visible_hours' in panel
