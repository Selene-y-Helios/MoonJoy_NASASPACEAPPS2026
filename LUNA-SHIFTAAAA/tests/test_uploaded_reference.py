"""Uploaded Shackleton research files are fixed-site references, not dynamic A/B results."""
import json
from pathlib import Path
from fastapi.testclient import TestClient
from backend.api import app
from backend.site_comparison import site_comparison_metrics

ROOT=Path(__file__).resolve().parents[1]

def test_uploaded_reference_values_and_provenance():
    response=TestClient(app).get('/api/reference/shackleton/summary')
    assert response.status_code==200
    doc=response.json()
    assert doc['kind']=='static_research_reference'
    assert doc['start_utc']=='2026-11-14T00:00:00Z'
    assert doc['end_utc']=='2026-11-21T00:00:00Z'
    assert doc['summary']['sun']['visible_hours']==0
    assert doc['summary']['earth']['visible_hours']==0
    assert doc['summary']['both']['visible_hours']==0
    assert 'ONLY' in doc['note']

def test_research_sources_not_mixed_across_observers():
    folder=ROOT/'data/reference/shackleton'
    fixed=json.loads((folder/'horizon_120km.json').read_text())['metadata']
    other=json.loads((folder/'lunar_site_other_observer.json').read_text())
    assert (fixed['site_x_m'],fixed['site_y_m']) != (other['x_m'],other['y_m'])

def test_a_b_metrics_retain_earth_windows():
    site={'latitude_deg':-89.8,'longitude_deg_east':155.9}
    w={'start_utc':'2026-11-14T00:00:00Z','end_utc':'2026-11-14T02:00:00Z','duration_hours':2}
    result={'summary':{'sun':{'visible_hours':2,'visible_percent_of_interval':50,'unknown_hours':0},'earth':{'visible_hours':2,'visible_percent_of_interval':50,'unknown_hours':0},'both':{'visible_hours':2,'visible_percent_of_interval':50}},'windows':{'sun':[w],'earth':[w],'both':[w]}}
    metrics=site_comparison_metrics(site,result)
    assert metrics['earth_windows']==[w]
    assert metrics['sun_windows']==[w]
    assert metrics['opportunity']['longest_window_hours']==2
