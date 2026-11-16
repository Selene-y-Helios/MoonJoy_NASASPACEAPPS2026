"""Standalone mocked-SPICE tests for the DE440 orbit response contract."""
from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
import importlib.util
from unittest import TestCase, mock

SCRIPT = Path(__file__).resolve().parents[1] / "backend" / "orbit_ephemeris.py"
spec = importlib.util.spec_from_file_location("orbit_ephemeris_under_test", SCRIPT)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class MockSpice:
    def __init__(self):
        self.kernels = []
        self.calls = []
        self.cleared = 0

    def furnsh(self, name):
        self.kernels.append(name)

    def str2et(self, utc):
        # Returns a synthetic epoch, used only to exercise the API contract.
        instant = datetime.strptime(utc, "%Y-%m-%d %H:%M:%S UTC").replace(tzinfo=timezone.utc)
        return instant.timestamp()

    def spkpos(self, target, et, frame, correction, observer):
        self.calls.append((target, observer, frame, correction))
        assert frame == 'J2000' and correction == 'NONE'
        if target == 'EARTH' and observer == 'SUN':
            return [149_597_870.7, et % 10000, 10], 500
        if target == 'MOON' and observer == 'EARTH':
            return [384_400.0, 0, et % 1000], 1
        raise AssertionError('Unexpected ephemeris request')

    def kclear(self):
        self.cleared += 1


class OrbitEphemerisTest(TestCase):
    def test_real_vectors_preserved_and_metadata(self):
        spice = MockSpice()
        with TemporaryDirectory() as tmp, mock.patch.object(module, "spice", spice):
            for f in module.KERNELS:
                (Path(tmp)/f).touch()
            result = module.calculate_orbit_ephemeris('2026-11-14', Path(tmp))
        self.assertEqual(result['date'], '2026-11-14')
        self.assertEqual(result['reference_frame'], 'J2000')
        self.assertEqual(result['ephemeris'], 'de440s.bsp')
        self.assertEqual(result['aberration_correction'], 'NONE')
        self.assertEqual(len(result['samples']), 193)
        self.assertEqual(len(result['earth_curve_km']), 366)
        self.assertEqual(len(result['moon_curve_km']), 224)
        self.assertEqual(result['samples'][48]['time_utc'], '2026-11-14T00:00:00Z')
        self.assertEqual(result['samples'][48]['earth_sun_km'][0], 149_597_870.7)
        self.assertEqual(result['samples'][48]['moon_earth_km'][0], 384_400.)
        self.assertEqual(spice.cleared, 1)
        self.assertEqual(len(spice.kernels), 2)
        self.assertTrue(all(q[2:] == ('J2000','NONE') for q in spice.calls))

    def test_rejects_invalid_dates_without_spice(self):
        with self.assertRaises(ValueError):
            module.calculate_orbit_ephemeris('2026-11-14T00:00:00Z', Path('/tmp'))
        with self.assertRaises(ValueError):
            module.calculate_orbit_ephemeris('2026-02-30', Path('/tmp'))

    def test_refuses_missing_kernels(self):
        with TemporaryDirectory() as tmp, mock.patch.object(module, 'spice', MockSpice()):
            with self.assertRaises(FileNotFoundError):
                module.calculate_orbit_ephemeris('2026-11-14', Path(tmp))

    def test_clears_kernel_pool_on_spice_failure(self):
        class BrokenSpice(MockSpice):
            def spkpos(self,*args):
                raise ValueError('Expected test exception')
        broken=BrokenSpice()
        with TemporaryDirectory() as tmp, mock.patch.object(module, 'spice', broken):
            for f in module.KERNELS:
                (Path(tmp)/f).touch()
            with self.assertRaises(ValueError):
                module.calculate_orbit_ephemeris('2026-11-14', Path(tmp))
        self.assertEqual(broken.cleared,1)
