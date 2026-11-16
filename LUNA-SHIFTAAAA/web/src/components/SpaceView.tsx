import { Canvas, useFrame, useThree } from '@react-three/fiber';
import { Html, OrbitControls, Stars, useTexture } from '@react-three/drei';
import { Suspense, useEffect, useMemo, useRef, useState } from 'react';
import * as THREE from 'three';
import type { SpaceSnapshot, ViewMode } from '../types';
import { latLonToPoint, MOON_RENDER_RADIUS, EARTH_RENDER_RADIUS } from '../lib/coordinates';
import { 
  type CelestialState, 
  EARTH_ORBIT_RADIUS, 
  MOON_ORBIT_RADIUS, 
  MOON_ORBIT_INCLINATION 
} from '../lib/astronomy';
import type { OrbitControls as OrbitControlsImpl } from 'three-stdlib';
import type { OrbitPaths } from '../lib/useSpiceOrbit';

export type CameraFocus = 'moon' | 'earth' | 'overview' | 'southPole';

interface SpaceViewProps {
  snapshot: SpaceSnapshot;
  selectedSiteId: string;
  view: ViewMode;
  cameraFocus?: CameraFocus;
  focusRequest?: number;
  onSiteSelect: (id: string) => void;
  showLabels: boolean;
  lighting: 'exploration' | 'directional';
  celestialState: CelestialState;
  orbitPaths?: OrbitPaths;
  onPolarPick?: (latitudeDeg: number, longitudeDeg: number) => void;
  onMoonClick?: () => void;
  onSouthPoleArrival?: () => void;
}

// Optional local NASA texture: if a texture was not downloaded, the existing
// bundled texture remains in use. This never changes any physics or picking.
function useOptionalNASAtexture(url: string, isColor = true): THREE.Texture | null {
  const [texture, setTexture] = useState<THREE.Texture | null>(null);
  useEffect(() => {
    let cancelled = false;
    let loaded: THREE.Texture | null = null;
    new THREE.TextureLoader().load(
      url,
      result => {
        if (cancelled) { result.dispose(); return; }
        result.colorSpace = isColor ? THREE.SRGBColorSpace : THREE.NoColorSpace;
        result.anisotropy = 8;
        // NASA cylindrical maps have their 0° meridian in the center.
        // Standard cylindrical NASA maps use 0° at the center.
        // The default sphere UV mapping already matches the Moon_ME axes.
        // Do not mirror U: flipping it reverses east/west geography.
        result.wrapS = THREE.RepeatWrapping;
        result.repeat.set(1, 1);
        result.offset.set(0, 0);
        result.needsUpdate = true;
        loaded = result;
        setTexture(result);
      },
      undefined,
      () => { if (!cancelled) setTexture(null); }
    );
    return () => { cancelled = true; loaded?.dispose(); };
  }, [url, isColor]);
  return texture;
}

function MoonBody({ rotationY = 0, onPolarPick, onMoonClick }: { rotationY?: number; onPolarPick?: (latitudeDeg: number, longitudeDeg: number) => void; onMoonClick?: () => void }) {
  const backupTexture = useTexture('/moon-demo.jpg');
  const nasaColorMap = useOptionalNASAtexture('/NASA_Moon_LROC_2K.jpg');
  const nasaBumpMap = useOptionalNASAtexture('/NASA_Moon_LOLA_Height_1K.jpg', false);
  backupTexture.colorSpace = THREE.SRGBColorSpace;
  return (
    <mesh rotation={[0, rotationY, 0]} onClick={event => {
      if (!onPolarPick && !onMoonClick) return;
      const local = event.object.worldToLocal(event.point.clone()).normalize();
      const latitude = THREE.MathUtils.radToDeg(Math.asin(THREE.MathUtils.clamp(local.y, -1, 1)));
      if (latitude < -90 || latitude > -80) {
        // Non-polar click: open a south-pole overview, without pretending the clicked
        // non-polar coordinate belongs to our regional NASA DEM.
        event.stopPropagation();
        onMoonClick?.();
        return;
      }
      const longitude = (THREE.MathUtils.radToDeg(Math.atan2(-local.z, local.x)) + 360) % 360;
      event.stopPropagation();
      if (onPolarPick) onPolarPick(latitude, longitude);
      else onMoonClick?.();
    }}>
      <sphereGeometry args={[MOON_RENDER_RADIUS, 96, 64]} />
      <meshStandardMaterial map={nasaColorMap ?? backupTexture} bumpMap={nasaBumpMap ?? undefined} bumpScale={0.028} roughness={1} metalness={0} />
    </mesh>
  );
}

function EarthBody({ rotationY = 0 }: { rotationY?: number }) {
  const backupTexture = useTexture('/earth-map.jpg');
  const nasaColorMap = useOptionalNASAtexture('/NASA_Earth_BlueMarble_2K.png');
  const nasaCloudMap = useOptionalNASAtexture('/NASA_Earth_Clouds_2K.jpg', false);
  backupTexture.colorSpace = THREE.SRGBColorSpace;
  return (
    <group rotation={[0, 0, THREE.MathUtils.degToRad(23.44)]}>
      <mesh rotation={[0, rotationY, 0]}>
        <sphereGeometry args={[EARTH_RENDER_RADIUS, 80, 64]} />
        <meshStandardMaterial map={nasaColorMap ?? backupTexture} roughness={0.95} metalness={0} />
      </mesh>
      {/* Static NASA cloud mosaic: appearance only, NOT real-time weather. */}
      {nasaCloudMap && (
        <mesh rotation={[0, rotationY, 0]} raycast={() => {}}>
          <sphereGeometry args={[EARTH_RENDER_RADIUS * 1.006, 80, 64]} />
          <meshStandardMaterial color="#f9fbff" alphaMap={nasaCloudMap} transparent opacity={0.48} depthWrite={false} roughness={1} />
        </mesh>
      )}
      {/* Very thin decorative atmosphere, excluded from click picking. */}
      <mesh raycast={() => {}}>
        <sphereGeometry args={[EARTH_RENDER_RADIUS * 1.017, 64, 48]} />
        <meshBasicMaterial color="#77b3dd" transparent opacity={0.055} depthWrite={false} side={THREE.FrontSide} blending={THREE.AdditiveBlending} />
      </mesh>
    </group>
  );
}

// Landing-site markers: constant size
function SitePins({
  snapshot,
  selectedSiteId,
  onSiteSelect,
  showLabels
}: Pick<SpaceViewProps, 'snapshot' | 'selectedSiteId' | 'onSiteSelect' | 'showLabels'>) {
  return (
    <>
      {snapshot.sites.map(site => {
        const p = latLonToPoint(site.latitudeDeg, site.longitudeDeg, MOON_RENDER_RADIUS + 0.075);
        const active = selectedSiteId === site.id;
        return (
          <group key={site.id} position={p}>
            <mesh 
              onClick={event => {
                event.stopPropagation();
                onSiteSelect(site.id);
              }}
              scale={1}
            >
              <sphereGeometry args={[0.07, 16, 16]} />
              <meshBasicMaterial color={active ? '#f3c86a' : '#48d6e3'} depthTest={false} />
            </mesh>
            {showLabels && (
              <Html center distanceFactor={12} style={{ pointerEvents: 'none' }}>
                <div className={`pin-label ${active ? 'active' : ''}`}>{site.name}</div>
              </Html>
            )}
          </group>
        );
      })}
    </>
  );
}

// Illustrative orbit ring
function OrbitRing({ 
  radius, 
  position = [0, 0, 0], 
  rotation = [0, 0, 0], 
  color = '#2d4b68' 
}: { 
  radius: number; 
  position?: [number, number, number]; 
  rotation?: [number, number, number]; 
  color?: string; 
}) {
  const lineGeometry = useMemo(() => {
    const pts: THREE.Vector3[] = [];
    const segments = 128;
    for (let i = 0; i <= segments; i++) {
      const theta = (i / segments) * 2 * Math.PI;
      pts.push(new THREE.Vector3(radius * Math.cos(theta), 0, radius * Math.sin(theta)));
    }
    return new THREE.BufferGeometry().setFromPoints(pts);
  }, [radius]);

  return (
    <group position={position} rotation={rotation}>
      <lineLoop geometry={lineGeometry}>
        <lineBasicMaterial color={color} transparent opacity={0.32} />
      </lineLoop>
    </group>
  );
}

// Physically sampled JPL DE440 path, with scene scaling provided by useSpiceOrbit.
// This affects neither textures nor camera orientation or surface-coordinate picks.
function EphemerisOrbitLine({points,color}: {points:OrbitPaths['earth']; color:string}) {
  const geometry=useMemo(()=>new THREE.BufferGeometry().setFromPoints(
    points.map(p=>new THREE.Vector3(p[0],p[1],p[2]))
  ),[points]);
  useEffect(()=>()=>geometry.dispose(),[geometry]);
  return <lineLoop geometry={geometry}><lineBasicMaterial color={color} transparent opacity={0.32}/></lineLoop>;
}

function SolarSystemBodies({
  snapshot,
  showLabels,
  lighting,
  celestialState,
  selectedSiteId,
  onSiteSelect,
  onPolarPick,
  onMoonClick,
  orbitPaths
}: SpaceViewProps) {
  const { sunPosition, earthPosition, moonPosition, earthSpinRotation, moonSpinRotation } = celestialState;

  return (
    <>
      {/* 1. SUN (system center) */}
      <mesh position={sunPosition}>
        <sphereGeometry args={[5, 48, 48]} />
        <meshBasicMaterial color="#ffd78b" />
      </mesh>
      <pointLight position={sunPosition} intensity={lighting === 'exploration' ? 3.8 : 4.2} distance={300} decay={0.3} />
      {lighting === 'exploration' && <directionalLight position={[0, 40, 60]} intensity={0.58} />}

      {/* Earth orbit around Sun */}
      {orbitPaths ? <EphemerisOrbitLine points={orbitPaths.earth} color="#355b80" /> : <OrbitRing radius={EARTH_ORBIT_RADIUS} color="#355b80" />}

      {/* 2. EARTH (orbits Sun) */}
      <group position={earthPosition}>
        <Suspense fallback={
          <mesh>
            <sphereGeometry args={[EARTH_RENDER_RADIUS, 48, 32]} />
            <meshBasicMaterial color="#287eae" />
          </mesh>
        }>
          <EarthBody rotationY={earthSpinRotation} />
        </Suspense>

        {/* Moon orbit around Earth */}
        {orbitPaths ? <EphemerisOrbitLine points={orbitPaths.moon} color="#465c73" /> : <OrbitRing radius={MOON_ORBIT_RADIUS} rotation={[MOON_ORBIT_INCLINATION, 0, 0]} color="#465c73" />}
      </group>

      {/* 3. MOON (orbits Earth) */}
      <group position={moonPosition}>
        <Suspense fallback={
          <mesh>
            <sphereGeometry args={[MOON_RENDER_RADIUS, 48, 32]} />
            <meshStandardMaterial color="#7e8085" />
          </mesh>
        }>
          <MoonBody rotationY={moonSpinRotation} onPolarPick={onPolarPick} onMoonClick={onMoonClick} />
        </Suspense>

        {/* Landing-site markers */}
        <group rotation={[0,moonSpinRotation,0]}>
          <SitePins
            snapshot={snapshot}
            selectedSiteId={selectedSiteId}
            onSiteSelect={onSiteSelect}
            showLabels={showLabels}
          />
        </group>
      </group>

      {/* Body labels */}
      {showLabels && (
        <>
          <Html position={sunPosition} center distanceFactor={28}>
            <span className="body-label">SUN</span>
          </Html>
          <Html position={earthPosition} center distanceFactor={22}>
            <span className="body-label">EARTH</span>
          </Html>
          <Html position={moonPosition} center distanceFactor={14}>
            <span className="body-label">MOON</span>
          </Html>
        </>
      )}
    </>
  );
}

function CameraDriver({
  view,
  selectedSiteId,
  cameraFocus = 'moon',
  focusRequest = 0,
  celestialState,
  snapshot,
  onSouthPoleArrival,
}: {
  view: ViewMode;
  selectedSiteId: string;
  cameraFocus?: CameraFocus;
  focusRequest?: number;
  celestialState: CelestialState;
  snapshot: SpaceSnapshot;
  onSouthPoleArrival?: () => void;
}) {
  const { camera } = useThree();
  const controls = useRef<OrbitControlsImpl>(null);
  const desired = useRef({
    position: new THREE.Vector3(8, 5, 14),
    target: new THREE.Vector3(),
    up: new THREE.Vector3(0, 1, 0)
  });
  const pending = useRef(true);
  const arrivalCallback = useRef(onSouthPoleArrival);
  arrivalCallback.current = onSouthPoleArrival;

  const moonPos = useMemo(() => new THREE.Vector3(...celestialState.moonPosition), [celestialState.moonPosition]);
  const earthPos = useMemo(() => new THREE.Vector3(...celestialState.earthPosition), [celestialState.earthPosition]);

  useEffect(() => {
    const site = snapshot.sites.find(s => s.id === selectedSiteId);
    const sitePos = site ? latLonToPoint(site.latitudeDeg, site.longitudeDeg) : new THREE.Vector3(0, -MOON_RENDER_RADIUS, 0);

    const pos = new THREE.Vector3();
    const target = new THREE.Vector3();
    const up = new THREE.Vector3(0, 1, 0);

    if (view === 'orbital') {
      if (cameraFocus === 'southPole') {
        const polarPoint = sitePos.clone().applyAxisAngle(new THREE.Vector3(0, 1, 0), celestialState.moonSpinRotation);
        const outward = polarPoint.clone().normalize();
        target.copy(moonPos).add(polarPoint);
        pos.copy(target).addScaledVector(outward, 3.1).add(new THREE.Vector3(0.5, 0, 0.6));
        up.set(0, 0, -1);
      } else if (cameraFocus === 'earth') {
        target.copy(earthPos);
        pos.copy(earthPos).add(new THREE.Vector3(0, EARTH_RENDER_RADIUS * 0.35, EARTH_RENDER_RADIUS * 2.8));
      } else if (cameraFocus === 'overview') {
        target.set(earthPos.x * 0.5, 0, earthPos.z * 0.5);
        pos.set(0, 75, 115);
      } else {
        target.copy(moonPos);
        pos.copy(moonPos).add(new THREE.Vector3(8, 5, 14));
      }
    } else if (view === 'earth') {
      const dirToMoon = new THREE.Vector3().subVectors(moonPos, earthPos).normalize();
      target.copy(moonPos);
      pos.copy(earthPos).addScaledVector(dirToMoon, EARTH_RENDER_RADIUS + 3.2);
    } else {
      sitePos.applyAxisAngle(new THREE.Vector3(0,1,0),celestialState.moonSpinRotation);
      const worldSitePos = moonPos.clone().add(sitePos);
      const outward = sitePos.clone().normalize();
      const dirToEarth = new THREE.Vector3().subVectors(earthPos, moonPos).normalize();
      const tangent = dirToEarth.clone().addScaledVector(outward, -dirToEarth.dot(outward));
      if (tangent.lengthSq() < 0.0001) tangent.set(1, 0, 0).addScaledVector(outward, -outward.x);
      tangent.normalize();

      pos.copy(worldSitePos).addScaledVector(outward, 0.22);
      target.copy(pos).addScaledVector(tangent, 5).addScaledVector(outward, 0.15);
      up.copy(outward);
    }

    desired.current = { position: pos, target, up };
    pending.current = true;
  }, [view, selectedSiteId, cameraFocus, focusRequest]);

  useFrame((_, delta) => {
    if (pending.current) {
      const k = 1 - Math.exp(-Math.min(delta, 0.06) * 3.4);
      camera.position.lerp(desired.current.position, k);
      camera.up.lerp(desired.current.up, k).normalize();
      if (controls.current) {
        controls.current.target.lerp(desired.current.target, k);
        controls.current.update();
      } else {
        camera.lookAt(desired.current.target);
      }

      if (
        camera.position.distanceTo(desired.current.position) < 0.025 && 
        (!controls.current || controls.current.target.distanceTo(desired.current.target) < 0.025)
      ) {
        camera.position.copy(desired.current.position);
        camera.up.copy(desired.current.up);
        controls.current?.target.copy(desired.current.target);
        controls.current?.update();
        pending.current = false;
        if (view === 'orbital' && cameraFocus === 'southPole') arrivalCallback.current?.();
      }
    } else {
      // Keep the camera target tracking orbital movement during playback
      if (controls.current) {
        if ((cameraFocus === 'moon' || cameraFocus === 'southPole') && view === 'orbital') {
          const offset = camera.position.clone().sub(controls.current.target);
          controls.current.target.copy(moonPos);
          camera.position.copy(moonPos).add(offset);
          controls.current.update();
        } else if (cameraFocus === 'earth' && view === 'orbital') {
          const offset = camera.position.clone().sub(controls.current.target);
          controls.current.target.copy(earthPos);
          camera.position.copy(earthPos).add(offset);
          controls.current.update();
        }
      }
    }
  });

  return (
    <OrbitControls
      ref={controls}
      enableDamping
      dampingFactor={0.07}
      enablePan={view !== 'surface'}
      minDistance={view === 'surface' ? 0.03 : 2.8}
      maxDistance={350}
      onStart={() => { pending.current = false; }}
    />
  );
}

function Scene(props: SpaceViewProps) {
  return (
    <>
      <color attach="background" args={['#010309']} />
      <ambientLight intensity={props.lighting === 'exploration' ? 0.38 : 0.06} />
      <Stars radius={220} depth={85} count={4400} factor={3.4} saturation={0} fade speed={0} />
      <Stars radius={320} depth={110} count={1100} factor={1.5} saturation={0} fade speed={0} />
      
      <SolarSystemBodies {...props} />

      <CameraDriver
        view={props.view}
        selectedSiteId={props.selectedSiteId}
        cameraFocus={props.cameraFocus}
        focusRequest={props.focusRequest}
        celestialState={props.celestialState}
        snapshot={props.snapshot}
        onSouthPoleArrival={props.onSouthPoleArrival}
      />
    </>
  );
}

export default function SpaceView(props: SpaceViewProps) {
  return (
    <Canvas
      camera={{ position: [8, 5, 14], fov: 45, near: 0.01, far: 600 }}
      dpr={[1, 2]}
      gl={{ antialias: true }}
    >
      <Scene {...props} />
    </Canvas>
  );
}
