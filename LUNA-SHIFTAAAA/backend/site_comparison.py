"""Compare body-center visibility windows for two independently evaluated lunar sites.

An opportunity exists when the Sun and the Earth are both above the sampled
terrain horizon at the same location.  A shared opportunity is the intersection
of the two sites' opportunity intervals. All dates are UTC.
"""
from __future__ import annotations

from datetime import datetime, timezone


def parse_timestamp(value: str) -> datetime:
    instant = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if instant.tzinfo is None:
        raise ValueError("Opportunity window timestamps must include a UTC offset.")
    return instant.astimezone(timezone.utc)


def format_timestamp(value: datetime) -> str:
    return value.isoformat(timespec="seconds").replace("+00:00", "Z")


def _intervals(windows: list[dict]) -> list[tuple[datetime, datetime]]:
    result = []
    for item in windows:
        start = parse_timestamp(item["start_utc"])
        end = parse_timestamp(item["end_utc"])
        if end <= start:
            raise ValueError("Opportunity window must have a positive duration.")
        if result and start < result[-1][1]:
            raise ValueError("Opportunity windows must not overlap or be out of order.")
        result.append((start, end))
    return result


def summarize_intervals(intervals: list[tuple[datetime, datetime]]) -> dict:
    windows = []
    total_seconds = 0.0
    longest_seconds = 0.0
    for start, end in intervals:
        seconds = (end - start).total_seconds()
        total_seconds += seconds
        longest_seconds = max(longest_seconds, seconds)
        windows.append({
            "start_utc": format_timestamp(start),
            "end_utc": format_timestamp(end),
            "duration_hours": round(seconds / 3600, 5),
        })
    return {
        "total_hours": round(total_seconds / 3600, 5),
        "longest_window_hours": round(longest_seconds / 3600, 5),
        "window_count": len(windows),
        "windows": windows,
    }


def summarize_opportunity(windows: list[dict]) -> dict:
    return summarize_intervals(_intervals(windows))


def intersect_opportunities(windows_a: list[dict], windows_b: list[dict]) -> dict:
    """Find intervals when Sun AND Earth are simultaneously visible at BOTH sites."""
    a = _intervals(windows_a)
    b = _intervals(windows_b)
    common: list[tuple[datetime, datetime]] = []
    i = j = 0
    while i < len(a) and j < len(b):
        start = max(a[i][0], b[j][0])
        end = min(a[i][1], b[j][1])
        if end > start:
            # Adjacent intersections represent one uninterrupted opportunity.
            if common and abs((start - common[-1][1]).total_seconds()) < 0.0001:
                common[-1] = (common[-1][0], end)
            else:
                common.append((start, end))
        if a[i][1] <= b[j][1]:
            i += 1
        else:
            j += 1
    return summarize_intervals(common)


def site_comparison_metrics(site: dict, result: dict) -> dict:
    summary = result["summary"]
    opportunities = summarize_opportunity(result["windows"]["both"])
    return {
        "site": site,
        "sun_visible_hours": summary["sun"]["visible_hours"],
        "sun_visible_percent": summary["sun"]["visible_percent_of_interval"],
        "earth_visible_hours": summary["earth"]["visible_hours"],
        "earth_visible_percent": summary["earth"]["visible_percent_of_interval"],
        "sun_earth_overlap_hours": summary["both"]["visible_hours"],
        "sun_earth_overlap_percent": summary["both"]["visible_percent_of_interval"],
        "unknown_sun_hours": summary["sun"]["unknown_hours"],
        "unknown_earth_hours": summary["earth"]["unknown_hours"],
        "earth_windows": result["windows"].get("earth", []),
        "sun_windows": result["windows"].get("sun", []),
        "opportunity": opportunities,
    }
