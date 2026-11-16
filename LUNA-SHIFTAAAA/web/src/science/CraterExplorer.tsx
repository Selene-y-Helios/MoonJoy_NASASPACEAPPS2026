import {useEffect,useState} from 'react';
import {MapPin,Info} from 'lucide-react';
import type {MissionSite} from '../mission/missionTypes';
import type {SiteLetter} from './useLunarScience';
import {useLunarScience} from './useLunarScience';

type Science=ReturnType<typeof useLunarScience>;
interface Crater {id:string;name:string;latitude_deg:number;longitude_deg_east:number;diameter_km:number;region:string;description:string;map_x_m:number;map_y_m:number;preview_url:string;preview_type:string;coordinate_source:string}
function markerPosition(x:number,y:number,map:NonNullable<Science['map']>){const b=map.bounds_projected_m;return {left:`${(x-b.left)/(b.right-b.left)*100}%`,top:`${(b.top-y)/(b.top-b.bottom)*100}%`};}
function LetterPin({site,science,letter}:{site:MissionSite|null;science:Science;letter:SiteLetter}){return site&&science.map&&site.map_x_m!==undefined&&site.map_y_m!==undefined?<span className={`science-map-pin ${letter.toLowerCase()}`} style={markerPosition(site.map_x_m,site.map_y_m,science.map)}>{letter}</span>:null;}
export default function CraterExplorer({science,onZoom,educational=false}:{science:Science;onZoom:()=>void;educational?:boolean}){
  const [craters,setCraters]=useState<Crater[]>([]);
  const [selected,setSelected]=useState<string>('shackleton');
  const [error,setError]=useState('');
  useEffect(()=>{const controller=new AbortController();void fetch('/api/craters',{signal:controller.signal}).then(async r=>{const data=await r.json();if(!r.ok)throw Error(data.detail??`HTTP ${r.status}`);setCraters(data.craters??[]);}).catch(e=>{if(e.name!=='AbortError')setError(e.message);});return()=>controller.abort();},[]);
  const crater=craters.find(c=>c.id===selected)??craters[0];
  const pickMap=async(e:React.MouseEvent<HTMLDivElement>)=>{if(!science.map||science.pickBusy)return;const rect=e.currentTarget.getBoundingClientRect(),b=science.map.bounds_projected_m;const x=b.left+(e.clientX-rect.left)/rect.width*(b.right-b.left),y=b.top-(e.clientY-rect.top)/rect.height*(b.top-b.bottom);await science.selectMapPoint(x,y,science.target);};
  const useCenter=async()=>{if(!crater)return;await science.selectCoordinates(crater.latitude_deg,crater.longitude_deg_east,science.target);};
  return <div className="crater-explorer" id="south-pole-map">
    <p className="science-caption">{educational?'Choose A or B, then click a valid pixel on the map. Craters help you recognize the landscape.':'Click the map to position A or B. Crater labels are geographic references, not safe landing sites.'}</p>
    <div className="science-switch"><button className={science.target==='A'?'selected':''} onClick={()=>science.setTarget('A')}>Place Point A</button><button className={science.target==='B'?'selected':''} onClick={()=>science.setTarget('B')}>Place Point B</button></div>
    <p className="science-target-status" role="status">Currently placing <strong>POINT {science.target}</strong>{science.pointB?' · Points A and B saved':' · Point B still needed'}</p>
    <div className="science-polar-map" role="button" tabIndex={0} aria-label={`NASA LOLA polar map; select point ${science.target}`} onClick={e=>void pickMap(e)} onKeyDown={e=>{if(e.key==='Enter'&&science.map){const b=science.map.bounds_projected_m;void science.selectMapPoint((b.left+b.right)/2,(b.top+b.bottom)/2,science.target);}}}>
      {science.map?<img src={science.map.url} alt="NASA LOLA elevation map of the lunar south pole"/>:<span>Loading NASA south-pole terrain map…</span>}
      {science.map&&craters.map(c=><button type="button" key={c.id} className={`crater-map-label ${crater?.id===c.id?'active':''}`} title={`${c.name} crater · click to see area and data`} style={markerPosition(c.map_x_m,c.map_y_m,science.map!)} onClick={e=>{e.stopPropagation();setSelected(c.id);}}>{c.name}</button>)}
      <LetterPin site={science.pointA} science={science} letter="A"/><LetterPin site={science.pointB} science={science} letter="B"/>
    </div>
    {error&&<p className="science-error" role="alert">Crater catalog: {error}</p>}
    <button className="science-primary" onClick={onZoom} type="button">Explore selected site in 3D</button>
    <p className="science-caption">Crater positions: NASA/JPL approximate centers. Map and image crops: NASA LOLA digital elevation model.</p>
    {crater&&<div className="crater-detail">
      <div className="crater-preview"><img src={crater.preview_url} alt={`NASA LOLA elevation view of ${crater.name} crater and surrounding region`}/><span>LOLA elevation · not optical imagery</span></div>
      <div className="crater-copy"><b>{crater.name} crater</b><small>{crater.region} · {crater.diameter_km.toFixed(1)} km across</small><p>{crater.description}</p><small>{Math.abs(crater.latitude_deg).toFixed(3)}°S · {crater.longitude_deg_east.toFixed(3)}°E</small></div>
      <button className="science-link" onClick={()=>void useCenter()} disabled={science.pickBusy}><MapPin size={13}/> Try crater center as Point {science.target}</button>
      <p className="science-caption"><Info size={12}/> A crater center may have no valid elevation pixel or unsuitable visibility. Use the map to choose another point on a nearby rim.</p>
    </div>}
    <a className="science-external" href="https://ipnpr.jpl.nasa.gov/progress_report/42-176/176C.pdf" target="_blank" rel="noopener noreferrer">NASA/JPL crater coordinates · source</a>
  </div>;
}
