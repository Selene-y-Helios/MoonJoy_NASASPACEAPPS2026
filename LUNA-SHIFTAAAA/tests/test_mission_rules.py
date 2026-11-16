"""Mission success must be based on complete windows, never summed fragments."""
from backend.mission_rules import evaluate_mission_windows

START='2026-11-14T00:00:00Z'
END='2026-11-16T00:00:00Z'
WINDOWS=[
 {'start_utc':'2026-11-14T13:00:00Z','end_utc':'2026-11-14T15:30:00Z'},
 {'start_utc':'2026-11-14T17:00:00Z','end_utc':'2026-11-14T19:00:00Z'},
]

def check(at, duration=2, delay=12, windows=WINDOWS):
 return evaluate_mission_windows(analysis_start=START,analysis_end=END,operation_start=at,
                                duration_hours=duration,delay_hours=delay,windows=windows)

def test_success():
 r=check('2026-11-14T13:00:00Z')
 assert r['passed'] is True
 assert r['recommended_start_utc']=='2026-11-14T13:00:00Z'
 assert all(r['checks'].values())

def test_failure_for_delayed_launch():
 r=check('2026-11-14T11:00:00Z')
 assert r['passed'] is False
 assert r['checks']['delay_respected'] is False

def test_failure_for_short_or_disjoint_windows():
 r=check('2026-11-14T14:00:00Z')
 assert r['passed'] is False
 assert r['checks']['continuous_sun_earth_visibility'] is False
 assert check('2026-11-14T16:00:00Z',windows=[])['passed'] is False

def test_exact_window_boundary():
 assert check('2026-11-14T13:30:00Z')['passed'] is True
 assert check('2026-11-14T13:31:00Z')['passed'] is False

def test_recommendation_respects_delay():
 r=check('2026-11-14T13:00:00Z',delay=14)
 assert r['recommended_start_utc']=='2026-11-14T17:00:00Z'

def test_end_limit():
 assert check('2026-11-15T23:00:00Z')['checks']['within_analysis_range'] is False
