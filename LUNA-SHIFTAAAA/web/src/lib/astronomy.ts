// Illustrative orbital motion model (not JPL ephemerides):
// - Earth orbits the Sun (365.25-day period).
// - Moon orbits Earth (27.32-day period).
// - Earth rotates about its axis (24 hours; 23.44° tilt).
// - Moon rotates synchronously (tidal locking).

export const J2000_MS = Date.UTC(2000, 0, 1, 12, 0, 0);

export const EARTH_ORBIT_PERIOD_DAYS = 365.25636;
export const MOON_ORBIT_PERIOD_DAYS = 27.321661;
export const EARTH_DAY_HOURS = 24.0;

// Illustrative orbit radii for clear visualization
export const SUN_POSITION: [number, number, number] = [0, 0, 0];
export const EARTH_ORBIT_RADIUS = 65;
export const MOON_ORBIT_RADIUS = 18;
export const MOON_ORBIT_INCLINATION = 0.0897; // ~5.14 degrees of inclination relative to the ecliptic

export function parseDateToUtcMs(dateStr: string): number {
  const parts = dateStr.split('-').map(Number);
  const year = parts[0] || 2026;
  const month = parts[1] || 11;
  const day = parts[2] || 14;
  return Date.UTC(year, month - 1, day, 0, 0, 0);
}

export function minutesToTimeString(minutes: number): string {
  const clamped = Math.max(0, Math.min(1499, Math.round(minutes)));
  const h = Math.floor(clamped / 60);
  const m = clamped % 60;
  return `${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}`;
}

export function timeStringToMinutes(timeStr: string): number {
  if (!timeStr) return 0;
  const parts = timeStr.split(':').map(Number);
  const h = parts[0] || 0;
  const m = parts[1] || 0;
  return Math.max(0, Math.min(1499, h * 60 + m));
}

export function addDaysToDateString(dateStr: string, days: number): string {
  const ms = parseDateToUtcMs(dateStr);
  const nextDate = new Date(ms + days * 86400000);
  const y = nextDate.getUTCFullYear();
  const m = String(nextDate.getUTCMonth() + 1).padStart(2, '0');
  const d = String(nextDate.getUTCDate()).padStart(2, '0');
  return `${y}-${m}-${d}`;
}

export interface CelestialState {
  sunPosition: [number, number, number];
  earthPosition: [number, number, number];
  moonPosition: [number, number, number];
  earthSpinRotation: number;
  moonSpinRotation: number;
  earthOrbitAngle: number;
  moonOrbitAngle: number;
  earthDegrees: number;
  moonDegrees: number;
  earthMoonDistKm: number;
  earthSunDistKm: number;
  currentMs: number;
  isoTimestamp: string;
}

export function calculateCelestialState(dateStr: string, minutesFromMidnight: number): CelestialState {
  const baseDayMs = parseDateToUtcMs(dateStr);
  const currentMs = baseDayMs + minutesFromMidnight * 60 * 1000;

  const daysSinceJ2000 = (currentMs - J2000_MS) / (1000 * 60 * 60 * 24);
  const hoursSinceJ2000 = daysSinceJ2000 * 24.0;

  // 1. Earth orbit around the Sun (ecliptic XZ plane)
  const earthOrbitAngle = (daysSinceJ2000 / EARTH_ORBIT_PERIOD_DAYS) * (2 * Math.PI);
  const earthX = EARTH_ORBIT_RADIUS * Math.cos(earthOrbitAngle);
  const earthY = 0;
  const earthZ = EARTH_ORBIT_RADIUS * Math.sin(earthOrbitAngle);

  // 2. Moon orbit around Earth (~5.14° inclined)
  const moonOrbitAngle = (daysSinceJ2000 / MOON_ORBIT_PERIOD_DAYS) * (2 * Math.PI);
  const moonRelX = MOON_ORBIT_RADIUS * Math.cos(moonOrbitAngle);
  const moonRelY = MOON_ORBIT_RADIUS * Math.sin(MOON_ORBIT_INCLINATION) * Math.sin(moonOrbitAngle);
  const moonRelZ = MOON_ORBIT_RADIUS * Math.cos(MOON_ORBIT_INCLINATION) * Math.sin(moonOrbitAngle);

  const moonX = earthX + moonRelX;
  const moonY = earthY + moonRelY;
  const moonZ = earthZ + moonRelZ;

  // 3. Earth axial rotation (one turn every 24 hours in this approximation)
  const earthSpinRotation = (hoursSinceJ2000 / EARTH_DAY_HOURS) * (2 * Math.PI);

  // 4. Synchronous lunar rotation
  const moonSpinRotation = moonOrbitAngle;

  const earthDegrees = (((earthSpinRotation * 180 / Math.PI) % 360) + 360) % 360;
  const moonDegrees = (((moonSpinRotation * 180 / Math.PI) % 360) + 360) % 360;

  // Approximate distances for educational metrics
  const earthMoonDistKm = 384400 * (1 - 0.0549 * Math.cos(moonOrbitAngle));
  const earthSunDistKm = 149597870 * (1 - 0.0167 * Math.cos(earthOrbitAngle));

  return {
    sunPosition: SUN_POSITION,
    earthPosition: [earthX, earthY, earthZ],
    moonPosition: [moonX, moonY, moonZ],
    earthSpinRotation,
    moonSpinRotation,
    earthOrbitAngle,
    moonOrbitAngle,
    earthDegrees,
    moonDegrees,
    earthMoonDistKm,
    earthSunDistKm,
    currentMs,
    isoTimestamp: new Date(currentMs).toISOString(),
  };
}
