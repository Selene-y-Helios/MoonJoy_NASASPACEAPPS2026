import {useEffect, useMemo, useState} from 'react';
import type {CelestialState} from './astronomy';
import {calculateCelestialState, EARTH_ORBIT_RADIUS, MOON_ORBIT_RADIUS} from './astronomy';

type Vector3 = [number, number, number];
type OrbitSample = {time_utc:string; earth_sun_km:Vector3; moon_earth_km:Vector3};
type OrbitPayload = {
  date:string;
  reference_frame:'J2000';
  ephemeris:'de440s.bsp';
  aberration_correction:'NONE';
  samples:OrbitSample[];
  earth_curve_km:Vector3[];
  moon_curve_km:Vector3[];
};
export type OrbitPaths = {earth:Vector3[]; moon:Vector3[]};

const ONE_AU_KM = 149597870.7;
const MEAN_MOON_DISTANCE_KM = 384400;
const finiteVector = (v:unknown):v is Vector3 =>
  Array.isArray(v) && v.length===3 && v.every(x=>typeof x==='number'&&Number.isFinite(x));

// ICRF/J2000 x/y/z (Z north) => right-handed scene x/y/z (Y up).
// This is a rigid axis conversion: no mirroring of the NASA textures.
function sceneDirection(v:Vector3):Vector3{return [v[0],v[2],-v[1]];}
function kmToScene(v:Vector3,visualRadius:number,referenceKm:number):Vector3{
  const [x,y,z]=sceneDirection(v);
  const factor=visualRadius/referenceKm;
  return [x*factor,y*factor,z*factor];
}
const add=(a:Vector3,b:Vector3):Vector3=>[a[0]+b[0],a[1]+b[1],a[2]+b[2]];
const lerp=(a:Vector3,b:Vector3,t:number):Vector3=>
  [a[0]+(b[0]-a[0])*t,a[1]+(b[1]-a[1])*t,a[2]+(b[2]-a[2])*t];
const len=(v:Vector3)=>Math.hypot(...v);

function validPayload(input:unknown,date:string):input is OrbitPayload{
  if(!input||typeof input!=='object')return false;
  const p=input as Partial<OrbitPayload>;
  return p.date===date&&p.reference_frame==='J2000'&&p.ephemeris==='de440s.bsp'&&
    p.aberration_correction==='NONE'&&Array.isArray(p.samples)&&p.samples.length>2&&
    p.samples.every(s=>typeof s.time_utc==='string'&&Number.isFinite(Date.parse(s.time_utc))&&finiteVector(s.earth_sun_km)&&finiteVector(s.moon_earth_km))&&
    Array.isArray(p.earth_curve_km)&&p.earth_curve_km.length>12&&p.earth_curve_km.every(finiteVector)&&
    Array.isArray(p.moon_curve_km)&&p.moon_curve_km.length>12&&p.moon_curve_km.every(finiteVector);
}

function sampleAt(payload:OrbitPayload,ms:number):OrbitSample|null{
  const points=payload.samples;
  if(ms<Date.parse(points[0].time_utc)||ms>Date.parse(points[points.length-1].time_utc))return null;
  let lo=0,hi=points.length-1;
  while(lo<hi){
    const mid=(lo+hi)>>1;
    if(Date.parse(points[mid].time_utc)<ms)lo=mid+1; else hi=mid;
  }
  if(lo===0)return points[0];
  const a=points[lo-1],b=points[lo];
  const aMs=Date.parse(a.time_utc),bMs=Date.parse(b.time_utc);
  const fraction=bMs===aMs?0:Math.max(0,Math.min(1,(ms-aMs)/(bMs-aMs)));
  return {time_utc:new Date(ms).toISOString(),earth_sun_km:lerp(a.earth_sun_km,b.earth_sun_km,fraction),moon_earth_km:lerp(a.moon_earth_km,b.moon_earth_km,fraction)};
}

export function useSpiceOrbit(date:string){
  const [loaded,setLoaded]=useState<OrbitPayload|null>(null);
  useEffect(()=>{
    const controller=new AbortController();
    void fetch(`/api/orbits?date=${encodeURIComponent(date)}`,{signal:controller.signal})
      .then(async response=>{
        if(!response.ok)throw Error(`Orbit ephemeris request failed (HTTP ${response.status})`);
        const parsed:unknown=await response.json();
        if(!validPayload(parsed,date))throw Error('Malformed DE440 orbit response');
        if(!controller.signal.aborted)setLoaded(parsed);
      })
      .catch(error=>{
        if(!controller.signal.aborted){
          console.warn('NASA orbital ephemerides unavailable; illustrative fallback remains enabled.',error);
          setLoaded(null);
        }
      });
    return ()=>controller.abort();
  },[date]);

  const payload=loaded?.date===date?loaded:null;
  const orbitPaths=useMemo<OrbitPaths|undefined>(()=>payload?{
    earth:payload.earth_curve_km.map(v=>kmToScene(v,EARTH_ORBIT_RADIUS,ONE_AU_KM)),
    moon:payload.moon_curve_km.map(v=>kmToScene(v,MOON_ORBIT_RADIUS,MEAN_MOON_DISTANCE_KM)),
  }:undefined,[payload]);

  const atMinutes=(minutes:number):CelestialState|null=>{
    if(!payload)return null;
    const fallback=calculateCelestialState(date,minutes);
    const sample=sampleAt(payload,fallback.currentMs);
    if(!sample)return null;
    const earth=kmToScene(sample.earth_sun_km,EARTH_ORBIT_RADIUS,ONE_AU_KM);
    const relativeMoon=kmToScene(sample.moon_earth_km,MOON_ORBIT_RADIUS,MEAN_MOON_DISTANCE_KM);
    return {
      ...fallback,
      sunPosition:[0,0,0],
      earthPosition:earth,
      moonPosition:add(earth,relativeMoon),
      earthOrbitAngle:Math.atan2(earth[2],earth[0]),
      moonOrbitAngle:Math.atan2(relativeMoon[2],relativeMoon[0]),
      earthSunDistKm:len(sample.earth_sun_km),
      earthMoonDistKm:len(sample.moon_earth_km),
      // Axial spins remain exactly as before, to preserve texture orientation and pin picking.
    };
  };
  return {orbitPaths,atMinutes,hasRealOrbits:!!payload};
}
