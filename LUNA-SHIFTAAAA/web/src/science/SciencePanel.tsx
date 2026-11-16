import {useEffect,useState} from 'react';
import {CalendarDays,Clock3,Compass,MapPin,Radio,ShieldAlert,Sun,Target,X} from 'lucide-react';
import HorizonChart from '../mission/HorizonChart';
import {durationLabel} from '../mission/missionMath';
import {SHACKLETON,useLunarScience} from './useLunarScience';
import CraterExplorer from './CraterExplorer';
import VisibilityChart from './VisibilityChart';
import './unified.css';

type Science=ReturnType<typeof useLunarScience>;
interface Props {science:Science;date:string;minutes:number;heading:number;onZoom:()=>void;onClose:()=>void;onJumpToTime:(iso:string)=>void;}
const n=(value:number|undefined,digits=2)=>value===undefined?'—':value.toFixed(digits);
const fmt=(iso:string)=>iso.replace('T',' ').replace(/(\.\d+)?Z$/,' UTC');
export default function SciencePanel({science,heading,onZoom,onClose,onJumpToTime}:Props){
  const utcInput=(value:string)=>value.slice(0,16);
  const toUTC=(value:string)=>new Date(`${value}:00Z`).toISOString();
  const [rangeStart,setRangeStart]=useState(utcInput(science.start));
  const [rangeEnd,setRangeEnd]=useState(utcInput(science.end));
  const [rangeStep,setRangeStep]=useState(science.step);
  const [rangeError,setRangeError]=useState('');
  const [lat,setLat]=useState(String(SHACKLETON.latitude_deg));
  const [lon,setLon]=useState(String(SHACKLETON.longitude_deg_east));
  useEffect(()=>{setLat(String(science.selected.latitude_deg));setLon(String(science.selected.longitude_deg_east));},[science.selected.latitude_deg,science.selected.longitude_deg_east]);
  useEffect(()=>{setRangeStart(utcInput(science.start));setRangeEnd(utcInput(science.end));setRangeStep(science.step);},[science.start,science.end,science.step]);
  const applyRange=()=>{
    try{
      const accepted=science.setAnalysisRange(toUTC(rangeStart),toUTC(rangeEnd),rangeStep);
      setRangeError(accepted?'':'Invalid date range. Check the start, end, and sample interval.');
      if(accepted)onJumpToTime(toUTC(rangeStart));
    }catch{setRangeError('Enter valid UTC start and end dates.');}
  };
  const place=async()=>{if(await science.selectCoordinates(Number(lat),Number(lon),science.target))onZoom();};
  const earthWindow=science.visibility?.windows.earth.find(w=>science.sample&&Date.parse(w.start_utc)<=Date.parse(science.sample.time_utc)&&Date.parse(w.end_utc)>=Date.parse(science.sample.time_utc));
  const upcomingEarth=science.visibility?.windows.earth.find(w=>science.sample&&Date.parse(w.start_utc)>Date.parse(science.sample.time_utc));
  const currentTime=science.sample?Date.parse(science.sample.time_utc):NaN;
  const earthUntil=earthWindow&&Number.isFinite(currentTime)?(Date.parse(earthWindow.end_utc)-currentTime)/3600000:null;
  const exportCsv=()=>{
    if(!science.comparison||!science.pointB)return;
    const c=science.comparison,rows=[['metric','point_A','point_B'],
      ['latitude_deg',String(science.pointA.latitude_deg),String(science.pointB.latitude_deg)],
      ['longitude_deg_east',String(science.pointA.longitude_deg_east),String(science.pointB.longitude_deg_east)],
      ['sun_visible_hours',String(c.points.A.sun_visible_hours),String(c.points.B.sun_visible_hours)],
      ['earth_visible_hours',String(c.points.A.earth_visible_hours),String(c.points.B.earth_visible_hours)],
      ['sun_earth_overlap_hours',String(c.points.A.sun_earth_overlap_hours),String(c.points.B.sun_earth_overlap_hours)],
      ['longest_continuous_overlap_hours',String(c.points.A.opportunity.longest_window_hours),String(c.points.B.opportunity.longest_window_hours)]];
    const blob=new Blob([rows.map(r=>r.join(',')).join('\r\n')],{type:'text/csv;charset=utf-8'});
    const href=URL.createObjectURL(blob);const a=document.createElement('a');a.href=href;a.download='LUNA_SHIFT_Comparison_A_B.csv';a.click();setTimeout(()=>URL.revokeObjectURL(href),1000);
  };
  const selected= science.active==='A'?science.pointA:science.pointB;
  return <div className="science-dock" role="region" aria-label="Professional science data">
    <div className="science-dock-header"><span><span className="live-dot"/> NASA SCIENCE DATA</span><button aria-label="Close science panel" title="Close science panel" onClick={onClose}><X size={16}/></button></div>
    <div className="science-dock-body">
      <div className="science-source">LOLA terrain · JPL SPICE geometry · UTC</div>
      {science.health&&(!science.health.regional_dem_ready||!science.health.spice_ready)&&<p className="science-error" role="alert">Missing NASA assets: {science.health.regional_dem_ready?'':'regional LOLA DEM '}{science.health.spice_ready?'':'SPICE kernels or spiceypy'}. Run IMPORT_NASA_DATA.bat and check /api/health.</p>}
      {science.error&&<p className="science-error" role="alert">{science.error}</p>}
      <section className="science-section"><div className="science-heading"><MapPin size={14}/> SOUTH POLE SITE <span>{science.siteBusy||science.pickBusy?'LOADING':'LOLA'}</span></div>
        <div className="science-switch"><button className={science.active==='A'?'selected':''} onClick={()=>{science.selectExisting('A');onZoom();}}>View Point A</button><button className={science.active==='B'?'selected':''} onClick={()=>{if(science.pointB){science.selectExisting('B');onZoom();}else science.setTarget('B');}}>{science.pointB?'View Point B':'Create Point B'}</button></div>
        <p className="science-action-hint">To set Point B: choose <b>Place Point B</b> above the polar map, then click a different valid location. The A/B table appears automatically.</p>
        <div className="science-coordinates"><span>Latitude <b>{n(selected?.latitude_deg,5)}°</b></span><span>Longitude E <b>{n(selected?.longitude_deg_east,5)}°</b></span></div>
        <CraterExplorer science={science} onZoom={onZoom}/>
        <div className="science-input-row"><label>Latitude<input type="number" min={-90} max={-80} step="any" value={lat} onChange={e=>setLat(e.target.value)}/></label><label>Longitude E<input type="number" step="any" value={lon} onChange={e=>setLon(e.target.value)}/></label></div>
        <button className="science-link" disabled={science.pickBusy} onClick={()=>void place()}>Set Point {science.target} from coordinates</button>
        <button className="science-primary" onClick={onZoom}><Target size={14}/> View selected site horizon in 3D</button>
      </section>
      <section className="science-section" aria-label="UTC analysis calendar"><div className="science-heading"><CalendarDays size={14}/> ANALYSIS PERIOD · UTC</div>
        <p className="science-caption">Choose the exact period to analyze. Both sites use these dates to calculate Earth visibility, sunlight, and simultaneous operational windows.</p>
        <div className="science-calendar"><label>Start (UTC)<input aria-label="Analysis start UTC" type="datetime-local" value={rangeStart} onChange={e=>setRangeStart(e.target.value)}/></label><label>End (UTC)<input aria-label="Analysis end UTC" type="datetime-local" value={rangeEnd} onChange={e=>setRangeEnd(e.target.value)}/></label></div>
        <label className="science-step-label">Sampling interval <select aria-label="Sampling interval" value={rangeStep} onChange={e=>setRangeStep(Number(e.target.value))}><option value={15}>15 minutes</option><option value={30}>30 minutes</option><option value={60}>60 minutes</option><option value={120}>120 minutes</option></select></label>
        <button className="science-primary" onClick={applyRange} disabled={science.timeBusy||science.siteBusy}>Calculate selected period</button>
        {rangeError&&<p className="science-error" role="alert">{rangeError}</p>}
        <p className="science-caption">Active analysis: {fmt(science.start)} to {fmt(science.end)} · every {science.step} min. Dates are separate from the playback cursor.</p>
      </section>
      <section className="science-section"><div className="science-heading"><Compass size={14}/> SITE CONDITIONS</div>
        <table className="science-table"><tbody>
          <tr><th>Elevation (LOLA)</th><td>{science.site?.dem_elevation_m===undefined?'—':`${n(science.site.dem_elevation_m,1)} m`}</td></tr>
          <tr><th>Observer height</th><td>{n(science.site?.observer_height_m,1)} m</td></tr>
          <tr><th>Sun elevation</th><td>{science.sample?`${n(science.sample.sun.elevation_deg)}°`:'—'}</td></tr>
          <tr><th>Sun azimuth</th><td>{science.sample?`${n(science.sample.sun.azimuth_deg)}°`:'—'}</td></tr>
          <tr><th>Sun status</th><td>{science.sample?(science.sample.sun.visible_center===null?'Unknown':science.sample.sun.visible_center?'Visible':'Blocked'):'—'}</td></tr>
          <tr><th>Earth elevation</th><td>{science.sample?`${n(science.sample.earth.elevation_deg)}°`:'—'}</td></tr>
          <tr><th>Earth azimuth</th><td>{science.sample?`${n(science.sample.earth.azimuth_deg)}°`:'—'}</td></tr>
          <tr><th>Earth status</th><td>{science.sample?(science.sample.earth.visible_center===null?'Unknown':science.sample.earth.visible_center?'Visible':'Blocked'):'—'}</td></tr>
          <tr><th>Earth view remaining</th><td>{earthUntil!==null?`${earthUntil.toFixed(2)} h`:(upcomingEarth?`Next: ${fmt(upcomingEarth.start_utc)}`:'No visible window in range')}</td></tr>
        </tbody></table>
        <p className="science-caption">{science.sample?fmt(science.sample.time_utc):'Awaiting SPICE timeline'} · {science.site?.elevation_dem??'NASA DEM'}</p>
      </section>
      <section className="science-section"><div className="science-heading"><Sun size={14}/> VISIBILITY SUMMARY <span>{science.timeBusy?'CALCULATING':'SELECTED PERIOD'}</span></div>
        <table className="science-table"><thead><tr><th>Metric</th><th>Hours</th></tr></thead><tbody>
          <tr><td>Sun visible</td><td>{science.visibility?durationLabel(science.visibility.summary.sun.visible_hours):'—'}</td></tr>
          <tr><td>Earth visible</td><td>{science.visibility?durationLabel(science.visibility.summary.earth.visible_hours):'—'}</td></tr>
          <tr><td>Sun + Earth overlap</td><td>{science.visibility?durationLabel(science.visibility.summary.both.visible_hours):'—'}</td></tr>
          <tr><td>Unknown Sun</td><td>{science.visibility?durationLabel(science.visibility.summary.sun.unknown_hours):'—'}</td></tr>
        </tbody></table>
      </section>
      <section className="science-section"><div className="science-heading"><Clock3 size={14}/> SUN / EARTH VS TERRAIN HORIZON · TIME SERIES</div>
        <p className="science-caption">Solid curves are geometric body-center elevations. Dashed curves are the terrain horizon in each body's changing direction. Move Daniela's timeline to see the UTC cursor advance.</p>
        <VisibilityChart timeline={science.visibility?.timeline??[]} selectedTime={science.sample?.time_utc??null} kind="sun"/>
        <VisibilityChart timeline={science.visibility?.timeline??[]} selectedTime={science.sample?.time_utc??null} kind="earth"/>
      </section>
      <section className="science-section"><div className="science-heading"><Radio size={14}/> EARTH VISIBILITY WINDOWS</div>
        <p className="science-caption">These are estimated intervals when the center of Earth is above this site's terrain horizon. They are potential direct-to-Earth communication opportunities, not verified radio links.</p>
        {science.visibility?.windows.earth.length?<table className="science-table"><thead><tr><th>From (UTC)</th><th>Until (UTC)</th><th>Hours</th></tr></thead><tbody>{science.visibility.windows.earth.map((w,i)=><tr key={i}><td>{fmt(w.start_utc)}</td><td>{fmt(w.end_utc)}</td><td>{durationLabel(w.duration_hours)}</td></tr>)}</tbody></table>:<p className="science-caption">{science.timeBusy?'Computing Earth visibility…':science.visibility?'No confirmed Earth visibility in this interval.':'Set an analysis period to calculate.'}</p>}
      </section>
      {science.reference&&<section className="science-section"><div className="science-heading">RESEARCH FILE · FIXED SHACKLETON OBSERVER</div>
        <p className="science-caption">Uploaded reference at {science.reference.site_latitude_deg.toFixed(6)}°, {science.reference.site_longitude_deg_east.toFixed(6)}° E. {fmt(science.reference.start_utc)} through {fmt(science.reference.end_utc)}. These numbers are NOT results for any newly selected Point A or B.</p>
        <table className="science-table"><tbody><tr><td>Reference Sun visible</td><td>{durationLabel(science.reference.summary.sun.visible_hours)}</td></tr><tr><td>Reference Earth visible</td><td>{durationLabel(science.reference.summary.earth.visible_hours)}</td></tr><tr><td>Reference both visible</td><td>{durationLabel(science.reference.summary.both.visible_hours)}</td></tr></tbody></table>
      </section>}
      <section className="science-section"><div className="science-heading"><Compass size={14}/> 360° TERRAIN HORIZON <span>{heading.toFixed(0)}° VIEW</span></div><HorizonChart horizon={science.horizon} sample={science.sample} heading={heading}/><p className="science-caption">The terrain horizon is calculated for the selected point. Sun and Earth markers move with the timeline.</p></section>
      <section className="science-section"><div className="science-heading"><Clock3 size={14}/> OPERATIONAL WINDOWS</div>
        {science.visibility?.windows.both.length?<table className="science-table"><thead><tr><th>Start UTC</th><th>End UTC</th><th>Duration</th></tr></thead><tbody>{science.visibility.windows.both.map((w,i)=><tr key={i}><td>{fmt(w.start_utc)}</td><td>{fmt(w.end_utc)}</td><td>{durationLabel(w.duration_hours)}</td></tr>)}</tbody></table>:<p className="science-caption">{science.visibility?'No simultaneous Sun/Earth visibility window on this date.':'Waiting for SPICE data…'}</p>}
      </section>
      <section className="science-section" id="point-comparison"><div className="science-heading"><Radio size={14}/> POINT A / B COMPARISON <span>{science.pointB?'TWO SITES':'SELECT B'}</span></div>
        <p className="science-caption">Earth visibility is a first-order geometric opportunity for direct-to-Earth communication, not a guarantee of radio contact. Compare the two sites over the selected UTC period.</p>
        {science.pointB?science.comparison?<><table className="science-table"><thead><tr><th>Metric</th><th>A</th><th>B</th></tr></thead><tbody>
          <tr><td>Sun visible</td><td>{durationLabel(science.comparison.points.A.sun_visible_hours)}</td><td>{durationLabel(science.comparison.points.B.sun_visible_hours)}</td></tr>
          <tr><td><b>Earth view (communication opportunity)</b></td><td>{durationLabel(science.comparison.points.A.earth_visible_hours)}</td><td>{durationLabel(science.comparison.points.B.earth_visible_hours)}</td></tr>
          <tr><td>Overlap</td><td>{durationLabel(science.comparison.points.A.sun_earth_overlap_hours)}</td><td>{durationLabel(science.comparison.points.B.sun_earth_overlap_hours)}</td></tr>
          <tr><td>Longest window</td><td>{durationLabel(science.comparison.points.A.opportunity.longest_window_hours)}</td><td>{durationLabel(science.comparison.points.B.opportunity.longest_window_hours)}</td></tr>
        </tbody></table><p className="science-caption">Shared A+B overlap: {durationLabel(science.comparison.shared_opportunity.total_hours)}</p><button className="science-link" onClick={exportCsv}>Download A/B results CSV</button></>:<p className="science-caption">Comparing independent terrain horizons…</p>:<p className="science-caption">Point B is not set yet. Scroll to the polar map, press <b>Place Point B</b>, and click a different valid pixel. You can also type new coordinates and press Set Point B.</p>}
        {science.comparison&&<div className="science-lay-summary"><strong>Which point is better for this objective?</strong> {science.comparison.points.A.earth_visible_hours===science.comparison.points.B.earth_visible_hours?'Both points provide the same total geometric Earth visibility.':`Point ${science.comparison.points.A.earth_visible_hours>science.comparison.points.B.earth_visible_hours?'A':'B'} has more total Earth visibility in the chosen period.`} <br/><strong>For an uninterrupted Sun + Earth operation:</strong> {science.comparison.points.A.opportunity.longest_window_hours===science.comparison.points.B.opportunity.longest_window_hours?'Both points have equally long continuous opportunities in this time range.':`Point ${science.comparison.points.A.opportunity.longest_window_hours>science.comparison.points.B.opportunity.longest_window_hours?'A':'B'} has the longer uninterrupted window where both the Sun and Earth are above the measured terrain horizon.`} {science.comparison.shared_opportunity.total_hours>0?'There are also times when both locations meet these conditions together.':'There is no confirmed shared window in this period.'} This measures geometric visibility, not landing safety or radio-link quality.</div>}
        {science.comparison&&<><div className="science-heading">A · CONTINUOUS SUN + EARTH WINDOWS</div>{science.comparison.points.A.opportunity.windows.length?<table className="science-table"><thead><tr><th>Start UTC</th><th>End UTC</th><th>Duration</th></tr></thead><tbody>{science.comparison.points.A.opportunity.windows.map((w,i)=><tr key={i}><td>{fmt(w.start_utc)}</td><td>{fmt(w.end_utc)}</td><td>{durationLabel(w.duration_hours)}</td></tr>)}</tbody></table>:<p className="science-caption">No confirmed combined window for A.</p>}<div className="science-heading">B · CONTINUOUS SUN + EARTH WINDOWS</div>{science.comparison.points.B.opportunity.windows.length?<table className="science-table"><thead><tr><th>Start UTC</th><th>End UTC</th><th>Duration</th></tr></thead><tbody>{science.comparison.points.B.opportunity.windows.map((w,i)=><tr key={i}><td>{fmt(w.start_utc)}</td><td>{fmt(w.end_utc)}</td><td>{durationLabel(w.duration_hours)}</td></tr>)}</tbody></table>:<p className="science-caption">No confirmed combined window for B.</p>}</>}
        {science.comparison&&(['A','B'] as const).map(letter=><div key={letter} className="science-section"><div className="science-heading">POINT {letter} · DIRECT EARTH VIEW WINDOWS</div>{science.comparison!.points[letter].earth_windows.length?<table className="science-table"><thead><tr><th>Start UTC</th><th>End UTC</th><th>Duration</th></tr></thead><tbody>{science.comparison!.points[letter].earth_windows.map((w,i)=><tr key={i}><td>{fmt(w.start_utc)}</td><td>{fmt(w.end_utc)}</td><td>{durationLabel(w.duration_hours)}</td></tr>)}</tbody></table>:<p className="science-caption">No confirmed direct-Earth view in this period for Point {letter}.</p>}</div>)}
        {science.compareError&&<p className="science-error">{science.compareError}</p>}
      </section>
      <p className="science-disclaimer"><ShieldAlert size={14}/> Preliminary geometric visibility model. Not a landing safety, power, or RF link certification.</p>
    </div>
  </div>;
}
