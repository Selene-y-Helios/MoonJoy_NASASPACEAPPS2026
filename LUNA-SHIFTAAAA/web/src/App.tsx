import {useEffect,useMemo,useRef,useState} from 'react';
import {CalendarDays,ChevronDown,Menu,X,Maximize2,Minimize2,PanelRight,Compass,Crosshair,Earth,Info,Layers3,MapPin,Moon,RotateCcw,Search,Sun,Telescope,GraduationCap,BriefcaseBusiness,BookOpen,Target} from 'lucide-react';
import SpaceView from './components/SpaceView';
import type {CameraFocus} from './components/SpaceView';
import Timeline from './components/Timeline';
import EducationPanel from './components/EducationPanel';
import type {HistoricalMission} from './components/EducationPanel';
import MissionTerrainView from './mission/MissionTerrainView';
import HorizonChart from './mission/HorizonChart';
import SciencePanel from './science/SciencePanel';
import {useLunarScience} from './science/useLunarScience';
import {demoSnapshot} from './data/demo';
import type {SpaceSnapshot,ViewMode} from './types';
import {calculateCelestialState,minutesToTimeString,timeStringToMinutes,addDaysToDateString} from './lib/astronomy';
import {useSpiceOrbit} from './lib/useSpiceOrbit';
import './style.css';
import './science/unified.css';

type Profile='student'|'professional';
export default function App(){
  const [profile,setProfile]=useState<Profile>('student');
  const [educationMissions,setEducationMissions]=useState<HistoricalMission[]>([]);
  const [educationLoading,setEducationLoading]=useState(true);
  const [educationError,setEducationError]=useState('');
  const [siteId,setSiteId]=useState(demoSnapshot.sites[0].id);
  const [date,setDate]=useState('2026-11-14');
  const [minutes,setMinutes]=useState(1080);
  const [isPlaying,setIsPlaying]=useState(false);
  const [playbackSpeed,setPlaybackSpeed]=useState(10);
  const [view,setView]=useState<ViewMode>('orbital');
  const [labels,setLabels]=useState(true);
  const [cameraFocus,setCameraFocus]=useState<CameraFocus>('moon');
  const [focusRequest,setFocusRequest]=useState(0);
  const [surfaceReady,setSurfaceReady]=useState(false);
  const [heading,setHeading]=useState(0);
  const [lighting,setLighting]=useState<'exploration'|'directional'>('exploration');
  const [loadedSnapshot,setLoadedSnapshot]=useState<SpaceSnapshot|null>(null);
  const fileInput=useRef<HTMLInputElement>(null);
  const [search,setSearch]=useState('');
  const [menuOpen,setMenuOpen]=useState(false);
  const [immersive,setImmersive]=useState(true);
  const [detailsOpen,setDetailsOpen]=useState(true);
  const scientific=profile==='professional';
  const science=useLunarScience(scientific,date,minutes);

  useEffect(()=>{
    const controller=new AbortController();
    void fetch('/api/education/missions',{signal:controller.signal}).then(async response=>{
      if(!response.ok)throw Error(`NASA education API unavailable (HTTP ${response.status}).`);
      const data=await response.json();
      if(!Array.isArray(data.missions)||data.missions.length!==5)throw Error('NASA education catalog requires five landing sites.');
      setEducationMissions(data.missions as HistoricalMission[]);
    }).catch(error=>{if(error.name!=='AbortError')setEducationError(error.message||'NASA education data unavailable.');})
      .finally(()=>{if(!controller.signal.aborted)setEducationLoading(false);});
    return()=>controller.abort();
  },[]);

  const studentSnapshot:SpaceSnapshot=useMemo(()=>({...demoSnapshot,sites:educationMissions.map(m=>({
    id:m.id,name:m.name,latitudeDeg:m.latitude_deg,longitudeDeg:m.longitude_deg_east,
    description:m.description,tag:m.mission_type==='crewed_landing'?'CREWED':'ROBOTIC',
  }))}),[educationMissions]);
  const base=loadedSnapshot??(educationMissions.length?studentSnapshot:demoSnapshot);
  useEffect(()=>{if(educationMissions.length&&!loadedSnapshot)setSiteId(prev=>educationMissions.some(m=>m.id===prev)?prev:'apollo-11');},[educationMissions,loadedSnapshot]);
  const activeMission=educationMissions.find(m=>m.id===siteId)??null;
  const sites=base.sites.filter(s=>s.name.toLowerCase().includes(search.toLowerCase()));
  const orbital=useSpiceOrbit(date);
  const celestial=useMemo(()=>orbital.atMinutes(minutes)??calculateCelestialState(date,minutes),[date,minutes,orbital.hasRealOrbits]);
  const snapshot=useMemo(()=>loadedSnapshot??{...base,timestampUTC:celestial.isoTimestamp},[base,loadedSnapshot,celestial.isoTimestamp]);
  const scienceSnapshot:SpaceSnapshot=useMemo(()=>({...demoSnapshot,sites:[
    {id:'science-A',name:'Point A · South Pole',latitudeDeg:science.pointA.latitude_deg,longitudeDeg:science.pointA.longitude_deg_east,description:'LOLA observer A',tag:'LOLA'},
    ...(science.pointB?[{id:'science-B',name:'Point B · South Pole',latitudeDeg:science.pointB.latitude_deg,longitudeDeg:science.pointB.longitude_deg_east,description:'LOLA observer B',tag:'LOLA'}]:[]),
  ]}),[science.pointA,science.pointB]);
  const time=useMemo(()=>minutesToTimeString(minutes),[minutes]);

  // Daniela's timeline is shared. In scientific profiles the same UTC scrubber
  // interpolates actual SPICE direction samples; it never runs SPICE per frame.
  useEffect(()=>{
    if(!isPlaying)return;
    const timer=setInterval(()=>setMinutes(previous=>{
      const next=previous+playbackSpeed*0.5;
      const limit=scientific?1440:1499;
      if(next>=limit){setDate(d=>addDaysToDateString(d,1));return 0;}
      return next;
    }),50);
    return()=>clearInterval(timer);
  },[isPlaying,playbackSpeed,scientific]);

  const selectProfile=(next:Profile)=>{
    setProfile(next);setMenuOpen(false);setIsPlaying(false);setSurfaceReady(false);
    setView('orbital');setCameraFocus('moon');setFocusRequest(n=>n+1);
    setDetailsOpen(true);
    if(next!=='student'&&minutes>1439)setMinutes(720);
  };
  const jumpToTime=(iso:string)=>{const dt=new Date(iso);if(!Number.isFinite(dt.getTime()))return;setDate(dt.toISOString().slice(0,10));setMinutes(dt.getUTCHours()*60+dt.getUTCMinutes());setIsPlaying(false);};
  const focus=(next:CameraFocus)=>{
    setSurfaceReady(false);setView('orbital');setCameraFocus(next);setFocusRequest(n=>n+1);
  };
  const zoomSouthPole=()=>{setSurfaceReady(false);setView('orbital');setCameraFocus('southPole');setFocusRequest(n=>n+1);};
  const selectPolarCoordinates=async(lat:number,lon:number)=>{
    if(await science.selectCoordinates(lat,lon,science.target)){setDetailsOpen(true);zoomSouthPole();}
  };
  const loadSnapshot=async(file:File)=>{
    try{
      const data=JSON.parse(await file.text());
      if(!data||data.frame!=='MOON_ME'||!Array.isArray(data.sites)||!data.sites.length||!['earthFromMoonKm','sunFromMoonKm'].every(k=>Array.isArray(data[k])&&data[k].length===3&&data[k].every((v:unknown)=>typeof v==='number'&&Number.isFinite(v)))||!data.timestampUTC||!Number.isFinite(Date.parse(data.timestampUTC)))throw Error('Invalid snapshot: expected MOON_ME, UTC timestamp, 3D vectors, and landing sites.');
      data.status='demo';data.source='EXTERNAL JSON (NOT SCIENTIFICALLY VALIDATED)';
      setLoadedSnapshot(data);setSiteId(data.sites[0].id);focus('moon');setMenuOpen(false);
      const dt=new Date(data.timestampUTC);setDate(dt.toISOString().slice(0,10));setMinutes(dt.getUTCHours()*60+dt.getUTCMinutes());
    }catch(e){alert(e instanceof Error?e.message:'Unable to open the JSON file');}
  };
  // Safety fallback: a camera-control interruption must not prevent the
  // transition from the animated polar zoom to the actual LOLA terrain view.
  useEffect(()=>{
    if(!scientific||cameraFocus!=='southPole'||surfaceReady)return;
    const timeout=window.setTimeout(()=>setSurfaceReady(true),2600);
    return()=>window.clearTimeout(timeout);
  },[scientific,cameraFocus,focusRequest,surfaceReady]);
  const currentSite=science.active==='A'?science.pointA:science.pointB??science.pointA;

  return <div className={`app ${immersive?'immersive':''}`}>
    {menuOpen&&<button type="button" className="drawer-backdrop" aria-label="Close menu" onClick={()=>setMenuOpen(false)}/>}
    <aside className={`sidebar ${menuOpen?'sidebar-open':''}`}>
      <div className="brand"><div className="brand-icon"><Moon size={22}/></div><div><strong>LUNAR<span className="brand-dot">.</span></strong><small>SITE NAVIGATOR</small></div><button type="button" className="drawer-close" aria-label="Close menu" onClick={()=>setMenuOpen(false)}><X size={19}/></button></div>
      <div className="side-scroll">
        <div className="section-label"><span>00</span> USER PROFILE</div>
        <div className="view-stack profile-side-stack">
          <button className={`view-item ${profile==='student'?'selected':''}`} onClick={()=>selectProfile('student')}><GraduationCap size={18}/><span><b>Educational</b><small>Five historical NASA lunar landings</small></span></button>
          <button className={`view-item ${profile==='professional'?'selected':''}`} onClick={()=>selectProfile('professional')}><BriefcaseBusiness size={18}/><span><b>Professional</b><small>Same explorer + NASA calculations</small></span></button>
        </div>
        <div className="section-label"><span>01</span> {scientific?'SCIENCE TIMELINE':'ORBITAL CONTROLS'}</div>
        <div className="section-block"><label className="field-label" htmlFor="date"><CalendarDays size={14}/> {scientific?'SPICE DATE (UTC)':'EXPLORATION DATE (UTC)'}</label><div className="date-row"><input id="date" type="date" value={date} onChange={e=>{setDate(e.target.value);setIsPlaying(false);}}/><input aria-label="UTC time" type="time" value={timeStringToMinutes(time)>=1440?'23:59':time} onChange={e=>setMinutes(timeStringToMinutes(e.target.value))}/></div>
          <p className="micro">{scientific?'The timeline controls NASA Sun/Earth visibility at the selected south polar site.':'UTC · Explore the illustrative Earth–Moon orbital model.'}</p>
          {!scientific&&<><button className="import-snapshot" onClick={()=>fileInput.current?.click()}>Import JSON snapshot</button><input ref={fileInput} type="file" accept=".json,application/json" hidden onChange={e=>{const file=e.target.files?.[0];if(file)void loadSnapshot(file);e.target.value='';}}/>{loadedSnapshot&&<button className="import-snapshot" onClick={()=>{setLoadedSnapshot(null);setSiteId(demoSnapshot.sites[0].id);}}>Return to NASA catalog</button>}</>}
        </div>
        <div className="section-label"><span>02</span> VIEWPOINT</div>
        <div className="view-stack">
          <button className={`view-item ${view==='orbital'&&cameraFocus==='moon'&&!surfaceReady?'selected':''}`} onClick={()=>focus('moon')}><Compass size={18}/><span><b>Orbital view</b><small>Explore the 3D system</small></span><ChevronDown size={14}/></button>
          <button className={`view-item ${view==='earth'?'selected':''}`} onClick={()=>{setSurfaceReady(false);setView('earth');setFocusRequest(n=>n+1);}}><Earth size={18}/><span><b>From Earth</b><small>Camera facing the Moon</small></span></button>
          {scientific?<button className={`view-item ${surfaceReady||cameraFocus==='southPole'?'selected':''}`} onClick={zoomSouthPole}><Target size={18}/><span><b>South Pole · Zoom</b><small>LOLA terrain and 360° horizon</small></span></button>:<button className={`view-item ${view==='surface'?'selected':''}`} onClick={()=>{setView('surface');setFocusRequest(n=>n+1);}}><Crosshair size={18}/><span><b>From surface</b><small>Illustrative lunar surface camera</small></span></button>}
        </div>
        {scientific?<>
          <div className="section-label heading-sites"><span>03</span> SOUTH POLE OBSERVERS</div>
          <div className="site-list">
            <button className={`site-option ${science.active==='A'?'current':''}`} onClick={()=>{science.selectExisting('A');zoomSouthPole();setDetailsOpen(true);}}><span className="site-index">A</span><span className="site-text"><b>Point A</b><small>{science.pointA.latitude_deg.toFixed(4)}° · {science.pointA.longitude_deg_east.toFixed(4)}° E</small></span><MapPin size={14}/></button>
            {science.pointB&&<button className={`site-option ${science.active==='B'?'current':''}`} onClick={()=>{science.selectExisting('B');zoomSouthPole();setDetailsOpen(true);}}><span className="site-index">B</span><span className="site-text"><b>Point B</b><small>{science.pointB.latitude_deg.toFixed(4)}° · {science.pointB.longitude_deg_east.toFixed(4)}° E</small></span><MapPin size={14}/></button>}
            <button className="import-snapshot" onClick={()=>{science.setTarget('B');setDetailsOpen(true);requestAnimationFrame(()=>document.getElementById('south-pole-map')?.scrollIntoView({block:'center',behavior:'smooth'}));}}>Add / change Point B on the polar map</button>
            <button className="import-snapshot" onClick={()=>setDetailsOpen(true)}>Show NASA data tables</button>
          </div>
        </>:<>
          <div className="section-label heading-sites"><span>03</span> LANDING SITES</div>
          <div className="search"><Search size={15}/><input placeholder="Search sites..." value={search} onChange={e=>setSearch(e.target.value)}/></div>
          <div className="site-list">{sites.map((s,i)=><button key={s.id} className={`site-option ${s.id===siteId?'current':''}`} onClick={()=>{setSiteId(s.id);setDetailsOpen(true);}}><span className="site-index">0{i+1}</span><span className="site-text"><b>{s.name}</b><small>{s.latitudeDeg.toFixed(2)}° · {s.longitudeDeg.toFixed(2)}°</small></span><MapPin size={14}/></button>)}{!sites.length&&<div className="empty">No matching sites</div>}</div>
        </>}
      </div>
      <div className="sidebar-footer"><span className="connection-dot"/><span>SCENE RENDERER ACTIVE</span><small>SPACEVIEW · 2 MODES</small></div>
    </aside>
    <main className="workspace">
      <header className="topbar"><button type="button" className="icon-action" aria-label="Open controls menu" title="Open controls menu" onClick={()=>setMenuOpen(true)}><Menu size={21}/></button><div className="breadcrumbs">EXPLORATION <span>/</span> LUNAR SOUTH POLE <span>/</span> <strong>SPACEVIEW</strong></div><div className="profile-top-tabs" role="group" aria-label="User profile"><button className={profile==='student'?'active':''} onClick={()=>selectProfile('student')}><GraduationCap size={14}/> Educational</button><button className={profile==='professional'?'active':''} onClick={()=>selectProfile('professional')}><BriefcaseBusiness size={14}/> Professional</button></div><div className="topbar-right"><button type="button" className="icon-action" onClick={()=>setDetailsOpen(v=>!v)} title="Toggle information panel" aria-label="Toggle information panel"><PanelRight size={19}/></button><button type="button" className="icon-action" onClick={()=>setImmersive(v=>!v)} title={immersive?'Exit immersive view':'Expand viewer'} aria-label={immersive?'Exit immersive view':'Expand viewer'}>{immersive?<Minimize2 size={19}/>:<Maximize2 size={19}/>}</button><div className="status"><span/>{scientific?'NASA SCIENCE':loadedSnapshot?'UNVERIFIED JSON':educationMissions.length?'NASA HISTORY':'DEMO DATA'}</div><span className="topbar-divider"/><div className="avatar">SV</div></div></header>
      <div className="content">
        <div className="title-row"><div><div className="eyebrow"><Telescope size={14}/> INTERACTIVE SPACE VISUALIZATION</div><h1>Lunar explorer <span>3D</span></h1><p>{scientific?'Explore the same Moon with NASA terrain, horizon, and Sun/Earth calculations.':'Explore an illustrative Earth–Moon orbital model and historical NASA landing sites.'}</p></div><button className="reset" onClick={()=>{focus('moon');setIsPlaying(false);setMinutes(1080);setDate('2026-11-14');setSearch('');}}><RotateCcw size={15}/> Reset view</button></div>
        <section className="scene-wrap">
          <div className="scene">
            {scientific&&surfaceReady?<MissionTerrainView terrain={science.terrain} horizon={science.horizon} sample={science.sample} observerHeight={science.site?.observer_height_m??1.5} onHeading={setHeading}/>:<SpaceView
              snapshot={scientific?scienceSnapshot:snapshot}
              view={view}
              selectedSiteId={scientific?`science-${science.active}`:siteId}
              onSiteSelect={id=>{if(scientific){science.selectExisting(id==='science-B'?'B':'A');zoomSouthPole();}else{setSiteId(id);setFocusRequest(n=>n+1);}setDetailsOpen(true);}}
              showLabels={labels} cameraFocus={cameraFocus} focusRequest={focusRequest}
              lighting={lighting} celestialState={celestial} orbitPaths={orbital.orbitPaths}
              onPolarPick={scientific?(lat,lon)=>{void selectPolarCoordinates(lat,lon);}:undefined}
              onMoonClick={scientific?()=>{setDetailsOpen(true);zoomSouthPole();}:undefined}
              onSouthPoleArrival={scientific?()=>setSurfaceReady(true):undefined}
            />}
          </div>
          <div className="focus-bar" aria-label="Camera focus">
            <button className={view==='orbital'&&cameraFocus==='moon'&&!surfaceReady?'active':''} onClick={()=>focus('moon')}><Moon size={15}/> Moon</button>
            <button className={view==='orbital'&&cameraFocus==='earth'&&!surfaceReady?'active':''} onClick={()=>focus('earth')}><Earth size={15}/> Earth</button>
            <button className={view==='orbital'&&cameraFocus==='overview'&&!surfaceReady?'active':''} onClick={()=>focus('overview')}><Compass size={15}/> Overview</button>
            {scientific&&<button className={surfaceReady||cameraFocus==='southPole'?'active':''} onClick={zoomSouthPole}><Target size={15}/> South Pole</button>}
            <button className="lighting-control" onClick={()=>setLighting(x=>x==='exploration'?'directional':'exploration')} title="Switch between exploration and directional lighting"><Sun size={15}/> {lighting==='exploration'?'Exploration light':'Directional light'}</button>
            <button onClick={()=>setDetailsOpen(v=>!v)} title={scientific?'NASA data tables':'NASA landing facts'}>{scientific?<PanelRight size={15}/>:<BookOpen size={15}/>} {scientific?'Science Data':'Learn'}</button>
          </div>
          <div className="scene-top"><span className="live-dot"/> {scientific&&surfaceReady?'SOUTH POLE · LOLA TERRAIN':view==='orbital'?'ORBITAL VIEW':view==='earth'?'EARTH VIEW':'SURFACE VIEW'} <span className="scene-top-right">{scientific&&surfaceReady?'SUN / EARTH DIRECTIONS: JPL SPICE': 'EARTH/MOON DIAMETERS TO SCALE · DISTANCES NOT TO SCALE'}</span></div>
          {scientific&&surfaceReady&&<div className="science-horizon-ribbon"><div className="science-ribbon-heading">360° TERRAIN HORIZON · CAMERA {heading.toFixed(0)}°</div><HorizonChart horizon={science.horizon} sample={science.sample} heading={heading}/></div>}
          <Timeline date={date} onDateChange={d=>{setDate(d);setIsPlaying(false);}} minutes={minutes} onMinutesChange={setMinutes} earthDegrees={celestial.earthDegrees} moonDegrees={celestial.moonDegrees} isPlaying={isPlaying} onTogglePlay={()=>setIsPlaying(p=>!p)} speed={playbackSpeed} onSpeedChange={setPlaybackSpeed} scientific={scientific}/>
          <div className="scene-bottom"><div className="scene-hint"><span className="mouse-symbol">◎</span> DRAG TO ROTATE <span className="sep">·</span> {scientific&&surfaceReady?'LOOK AROUND THE LOCAL HORIZON':'SCROLL TO ZOOM'}</div><button className={`label-toggle ${labels?'on':''}`} onClick={()=>setLabels(v=>!v)}><Layers3 size={14}/> Labels {labels?'ON':'OFF'}</button></div>
          <div className="scene-warning"><Info size={14}/>{scientific&&surfaceReady?'Scientific terrain and body-center geometry; not a landing safety or communication guarantee.':(orbital.hasRealOrbits?'NASA JPL DE440 geometric orbits; distances rescaled for visibility, axial rotations illustrative. South polar terrain remains unchanged.':'Orbital ephemerides unavailable or loading: illustrative fallback. South polar terrain uses NASA data after zoom.')}</div>
          {scientific&&detailsOpen&&<SciencePanel science={science} date={date} minutes={minutes} heading={heading} onZoom={zoomSouthPole} onClose={()=>setDetailsOpen(false)} onJumpToTime={jumpToTime}/>}
        </section>
        {!scientific&&<div className={`bottom-grid ${detailsOpen?'details-open':''}`}><EducationPanel mission={activeMission} count={educationMissions.length} loading={educationLoading} error={educationError}/></div>}
        {!scientific&&<div className="lower-note"><Info size={15}/><span>{orbital.hasRealOrbits?'Orbital positions and paths: NASA/JPL DE440 J2000 (geometric); relative display scales, illustrative axial spins.':'Illustrative orbital fallback active until JPL DE440 is available.'}</span></div>}
        {scientific&&!immersive&&<div className="lower-note"><Info size={15}/><span>Selected observer: {currentSite.latitude_deg.toFixed(5)}° latitude, {currentSite.longitude_deg_east.toFixed(5)}° east longitude. The science tables remain available in the same scene.</span></div>}
      </div>
    </main>
  </div>;
}
