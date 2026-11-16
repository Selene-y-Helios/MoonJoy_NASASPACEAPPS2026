"""Check caching avoids redundant SPICE calls and expires after horizon changes."""
import os
from datetime import datetime, timedelta, timezone

from backend import api


def test_run_spice_uses_site_time_cache_and_horizon_signature(tmp_path, monkeypatch):
    kernels = tmp_path / "kernels"
    kernels.mkdir()
    for name in ("first.bsp", "second.tls"):
        (kernels / name).write_text("mock")
    horizon = tmp_path / "horizon.json"
    horizon.write_text('{"metadata":{}}')

    calls = []

    def fake_calculate(start, end, *, step_minutes, horizon_path, kernel_dir):
        calls.append((start, end, step_minutes, horizon_path, kernel_dir))
        return {"timeline": [], "count": len(calls)}

    monkeypatch.setattr(api, "KERNELS", kernels)
    monkeypatch.setattr(api, "KERNEL_NAMES", ["first.bsp", "second.tls"])
    monkeypatch.setattr(api.importlib.util, "find_spec", lambda name: object())
    monkeypatch.setattr(api, "calculate_visibility", fake_calculate)
    api.SPICE_CACHE.clear()

    start = datetime(2026, 11, 14, tzinfo=timezone.utc)
    end = start + timedelta(days=1)
    try:
        a = api.run_spice(start, end, 15, horizon)
        b = api.run_spice(start, end, 15, horizon)
        assert a is b
        assert len(calls) == 1

        api.run_spice(start, end, 5, horizon)
        assert len(calls) == 2

        stat = horizon.stat()
        os.utime(horizon, ns=(stat.st_atime_ns, stat.st_mtime_ns + 5_000_000_000))
        api.run_spice(start, end, 15, horizon)
        assert len(calls) == 3
    finally:
        api.SPICE_CACHE.clear()
