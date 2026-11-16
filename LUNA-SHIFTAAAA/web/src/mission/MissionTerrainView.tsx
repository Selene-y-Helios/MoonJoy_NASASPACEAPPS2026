import {Canvas,useFrame,useThree} from '@react-three/fiber';
import {OrbitControls,Stars} from '@react-three/drei';
import {useEffect,useMemo,useRef,useState} from 'react';
import * as THREE from 'three';
import type {MissionHorizon,MissionSample,MissionTerrain} from './missionTypes';

interface Props {terrain:MissionTerrain|null;horizon:MissionHorizon|null;sample:MissionSample|null;observerHeight:number;onHeading:(heading:number)=>void}
// Deterministic visual regolith grain. It is NOT a NASA terrain measurement:
// the DEM positions, normals, horizon and visibility remain untouched.
function useRegolithBump(): THREE.CanvasTexture {
  const texture=useMemo(()=>{
    const canvas=document.createElement('canvas'); canvas.width=256; canvas.height=256;
    const ctx=canvas.getContext('2d');
    if(ctx){
      const pixels=ctx.createImageData(256,256); let seed=1949;
      for(let i=0;i<pixels.data.length;i+=4){
        seed=(Math.imul(seed,1664525)+1013904223)>>>0;
        const grain=110+(seed%65);
        pixels.data[i]=grain;pixels.data[i+1]=grain;pixels.data[i+2]=grain;pixels.data[i+3]=255;
      }
      ctx.putImageData(pixels,0,0);
    }
    const t=new THREE.CanvasTexture(canvas);
    t.wrapS=t.wrapT=THREE.RepeatWrapping;
    t.colorSpace=THREE.NoColorSpace;
    t.repeat.set(18,18);
    t.needsUpdate=true;
    return t;
  },[]);
  useEffect(()=>()=>texture.dispose(),[texture]);
  return texture;
}

// LUNA_SHIFT_LUNAR_SURFACE_PATCH_V2: visual texture handling only.
// These images alter *appearance*, never the science DEM or SPICE positions.
function useOptionalVisualMap(url: string | null, colorMap: boolean, repeat: boolean): THREE.Texture | null {
  const [texture, setTexture] = useState<THREE.Texture | null>(null);
  useEffect(() => {
    if (!url) return;
    let cancelled = false;
    let loaded: THREE.Texture | null = null;
    new THREE.TextureLoader().load(url, result => {
      if (cancelled) { result.dispose(); return; }
      result.colorSpace = colorMap ? THREE.SRGBColorSpace : THREE.NoColorSpace;
      result.anisotropy = 8;
      if (repeat) {
        result.wrapS = THREE.RepeatWrapping;
        result.wrapT = THREE.RepeatWrapping;
      }
      // World-projected surface UVs are tiled in the geometry; no global mirroring.
      result.repeat.set(1, 1);
      result.offset.set(0, 0);
      result.needsUpdate = true;
      loaded = result;
      setTexture(result);
    }, undefined, () => {
      // Missing artwork must never prevent terrain/science from rendering.
      if (!cancelled) setTexture(null);
    });
    return () => { cancelled = true; loaded?.dispose(); };
  }, [url, colorMap, repeat]);
  return texture;
}

function Terrain({terrain}:{terrain:MissionTerrain|null}){
  // Visual-only repeating gray lunar dust; NOT a georeferenced NASA photograph.
  const fallbackBump = useRegolithBump();
  const regolithColor = useOptionalVisualMap('/lunar_regolith_visual.jpg', true, true);
  const regolithBump = useOptionalVisualMap('/lunar_regolith_bump.jpg', false, true);
  const geometry=useMemo(()=>{
    if(!terrain)return null;
    const g=new THREE.BufferGeometry();
    // Scientific DEM positions and triangle indices are copied verbatim.
    g.setAttribute('position',new THREE.Float32BufferAttribute(terrain.positions,3));
    g.setIndex(terrain.indices);
    // UV coordinates are COSMETIC world-space projection, ~14 m per tile.
    // They cannot alter the 5 m/80 m LOLA elevation or any horizon occlusion.
    const uv:number[]=[];
    for(let i=0;i<terrain.positions.length;i+=3){
      uv.push(terrain.positions[i]/14,terrain.positions[i+2]/14);
    }
    g.setAttribute('uv',new THREE.Float32BufferAttribute(uv,2));
    g.computeVertexNormals();return g;
  },[terrain]);
  useEffect(()=>()=>{geometry?.dispose()},[geometry]);
  if(!geometry)return null;
  return <mesh geometry={geometry} receiveShadow castShadow>
    <meshStandardMaterial
      map={regolithColor??undefined}
      color="#d4d0cb" bumpMap={regolithBump??fallbackBump}
      bumpScale={0.045} roughness={1} metalness={0}
      side={THREE.DoubleSide}
    />
  </mesh>;
}
function Horizon({horizon}:{horizon:MissionHorizon|null}){
  const geometry=useMemo(()=>{
    if(!horizon)return null;
    const vertices:number[]=[],indices:number[]=[];
    const samples=horizon.samples;
    for(let i=0;i<samples.length;i++){
      const p=samples[i],a=p.azimuth_deg*Math.PI/180,e=(p.horizon_elevation_deg??0)*Math.PI/180;
      const r=3500*Math.cos(e),x=r*Math.sin(a),y=3500*Math.sin(e),z=-r*Math.cos(a);
      vertices.push(x,-900,z,x,y,z);
    }
    for(let i=0;i<samples.length;i++){
      const next=(i+1)%samples.length;
      if(samples[i].horizon_elevation_deg===null||samples[next].horizon_elevation_deg===null)continue;
      const a=2*i,b=2*next;
      indices.push(a,a+1,b,a+1,b+1,b);
    }
    const g=new THREE.BufferGeometry();g.setAttribute('position',new THREE.Float32BufferAttribute(vertices,3));g.setIndex(indices);g.computeVertexNormals();return g;
  },[horizon]);
  useEffect(()=>()=>{geometry?.dispose()},[geometry]);
  if(!geometry)return null;
  return <mesh geometry={geometry}><meshBasicMaterial color="#344354" side={THREE.DoubleSide}/></mesh>;
}
function Body({sample,kind}:{sample:MissionSample|null;kind:'sun'|'earth'}){
  // Keep exactly the original SPICE ENU body-center positions, radii and
  // visibility-dependent opacities. Earth imagery is a decorative texture.
  const earthMap = useOptionalVisualMap(kind==='earth'?'/NASA_Earth_BlueMarble_2K.png':null,true,false);
  if(!sample)return null;
  const body=sample[kind];const [east,north,up]=body.direction_local_east_north_up;
  const position:[number,number,number]=[east*3100,up*3100,-north*3100];
  return <mesh position={position} renderOrder={2}>
    <sphereGeometry args={[kind==='sun'?47:34,24,16]}/>
    <meshBasicMaterial
      map={kind==='earth'?(earthMap??undefined):undefined}
      color={kind==='sun'?'#ffd37d':earthMap?'#ffffff':'#74c9ff'}
      depthTest={false} transparent
      opacity={body.visible_center===true?1:0.3}
    />
  </mesh>;
}
function SunLight({sample}:{sample:MissionSample|null}){
  if(!sample)return null;
  const [east,north,up]=sample.sun.direction_local_east_north_up;
  return <directionalLight position={[east*2500,up*2500,-north*2500]} intensity={sample.sun.visible_center===true?2.2:0.1} castShadow shadow-mapSize={[1024,1024]} shadow-camera-left={-950} shadow-camera-right={950} shadow-camera-top={950} shadow-camera-bottom={-950} shadow-camera-near={0.5} shadow-camera-far={7000}/>;
}
function CameraHeading({onHeading,observerHeight}:{onHeading:(heading:number)=>void;observerHeight:number}){
  const {camera}=useThree();const last=useRef(-1);const forward=useMemo(()=>new THREE.Vector3(),[]);
  useEffect(()=>{camera.position.set(0,observerHeight,0.025);camera.up.set(0,1,0);camera.lookAt(0,observerHeight,-1)},[camera,observerHeight]);
  useFrame(({clock})=>{const t=clock.elapsedTime;if(t-last.current<.18)return;last.current=t;camera.getWorldDirection(forward);onHeading((Math.atan2(forward.x,-forward.z)*180/Math.PI+360)%360);});
  return <OrbitControls target={[0,observerHeight,0]} enablePan={false} enableZoom={false} rotateSpeed={-0.7} minPolarAngle={0.1} maxPolarAngle={Math.PI-0.1}/>;
}
export default function MissionTerrainView({terrain,horizon,sample,observerHeight,onHeading}:Props){
  return <div className="mc-canvas">
    <Canvas camera={{position:[0,observerHeight,.025],fov:70,near:.05,far:10000}} dpr={[1,1.6]} shadows gl={{antialias:true}}>
      <color attach="background" args={['#010309']}/>
      <Stars radius={180} depth={70} count={2900} factor={2.9} saturation={0} fade speed={0}/>
      <ambientLight intensity={0.43}/>
      <SunLight sample={sample}/>
      <Terrain terrain={terrain}/><Horizon horizon={horizon}/>
      <Body sample={sample} kind="sun"/><Body sample={sample} kind="earth"/>
      <CameraHeading observerHeight={observerHeight} onHeading={onHeading}/>
    </Canvas>
    {!terrain&&<div className="mc-canvas-loading">NASA terrain will appear after the selected site is processed.</div>}
    <div className="mc-viewport-label">LOLA DEM · FIRST-PERSON VIEW · DRAG TO LOOK AROUND</div>
  </div>;
}
