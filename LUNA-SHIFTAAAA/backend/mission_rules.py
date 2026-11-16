"""Educational mission checks derived exclusively from terrain-aware SPICE windows.

A pass means the sampled Sun and Earth *centers* are above the site's DEM
horizon for the requested continuous interval. It does not certify landing
safety, power availability, radio link quality, or human safety.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone


def parse_utc_timestamp(value: str) -> datetime:
    if not (value.endswith('Z') or value.endswith('+00:00')):
        raise ValueError('Mission timestamps must use an explicit UTC timezone.')
    date = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if date.utcoffset() != timedelta(0):
        raise ValueError('Mission timestamps must use UTC.')
    return date.astimezone(timezone.utc)


def utc_string(value: datetime) -> str:
    return value.isoformat(timespec='seconds').replace('+00:00', 'Z')


def evaluate_mission_windows(*, analysis_start: str, analysis_end: str,
                             operation_start: str, duration_hours: float,
                             delay_hours: float, windows: list[dict]) -> dict:
    start = parse_utc_timestamp(analysis_start)
    end = parse_utc_timestamp(analysis_end)
    operation = parse_utc_timestamp(operation_start)
    if end <= start:
        raise ValueError('Analysis end must be later than analysis start.')
    if not 0.25 <= duration_hours <= 24:
        raise ValueError('Mission duration must be between 0.25 and 24 hours.')
    if not 0 <= delay_hours <= 72:
        raise ValueError('Mission delay must be between 0 and 72 hours.')
    earliest = start + timedelta(hours=delay_hours)
    operation_end = operation + timedelta(hours=duration_hours)
    in_range = operation >= earliest and operation_end <= end
    suitable = []
    candidates = []
    for item in windows:
        w_start = parse_utc_timestamp(item['start_utc'])
        w_end = parse_utc_timestamp(item['end_utc'])
        if w_end <= w_start:
            raise ValueError('Invalid scientific visibility window.')
        if w_end - max(w_start, earliest) >= timedelta(hours=duration_hours):
            candidates.append({
                'start_utc': utc_string(max(w_start, earliest)),
                'end_utc': utc_string(w_end),
                'duration_hours': round((w_end - max(w_start, earliest)).total_seconds() / 3600, 5),
            })
        if w_start <= operation and operation_end <= w_end:
            suitable.append(item)
    visible = bool(suitable)
    passed = in_range and visible
    return {
        'passed': passed,
        'status': 'MISSION_REQUIREMENTS_MET' if passed else 'MISSION_REQUIREMENTS_NOT_MET',
        'checks': {
            'delay_respected': operation >= earliest,
            'within_analysis_range': operation >= start and operation_end <= end,
            'continuous_sun_earth_visibility': visible,
        },
        'analysis_start_utc': utc_string(start),
        'analysis_end_utc': utc_string(end),
        'earliest_allowed_start_utc': utc_string(earliest),
        'operation_start_utc': utc_string(operation),
        'operation_end_utc': utc_string(operation_end),
        'duration_hours': duration_hours,
        'delay_hours': delay_hours,
        'candidate_windows': candidates,
        'recommended_start_utc': candidates[0]['start_utc'] if candidates else None,
        'message': ('The selected site and time satisfy the educational visibility requirements.'
                    if passed else
                    'The selected plan does not satisfy the full continuous visibility and timing requirements.'),
        'scientific_scope': 'Sampled geometric Sun/Earth center visibility above local NASA LOLA horizon; preliminary.',
    }
