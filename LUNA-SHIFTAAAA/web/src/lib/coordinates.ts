import * as THREE from 'three';
import type { Vector3Km } from '../types';
// Mean radii (NASA/JPL): Moon ~1737.4 km, Earth ~6371 km.
// Visual units: Moon radius = 2.35; relative Earth/Moon diameter is physical.
// Inter-body distances are not to scale.
export const MOON_RENDER_RADIUS=2.35;
export const EARTH_RENDER_RADIUS=MOON_RENDER_RADIUS*(6371/1737.4);
export function unitFromKm(v:Vector3Km):THREE.Vector3 {
  const a=new THREE.Vector3(...v);
  if (!a.lengthSq() || !Number.isFinite(a.lengthSq())) throw new Error('Invalid astronomical vector');
  return a.normalize();
}
// Moon ME: east-positive longitude. Graphics convention: +Y north, +X 0° E, -Z 90° E.
export function latLonToPoint(latDeg:number,lonDeg:number,r=MOON_RENDER_RADIUS):THREE.Vector3 {
  const a=THREE.MathUtils.degToRad(latDeg),b=THREE.MathUtils.degToRad(lonDeg);
  return new THREE.Vector3(r*Math.cos(a)*Math.cos(b),r*Math.sin(a),-r*Math.cos(a)*Math.sin(b));
}
export function mappedDirection(v:Vector3Km):THREE.Vector3 {
  // Convert input Moon_ME axes to the rendered coordinate frame.
  return unitFromKm(v).multiply(new THREE.Vector3(1,1,-1));
}
export function normKm(v:Vector3Km):number{return Math.hypot(...v)}
