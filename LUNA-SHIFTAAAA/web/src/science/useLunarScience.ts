import {useCallback,useEffect,useMemo,useRef,useState} from 'react';
import {interpolateFrame} from '../mission/missionMath';
import type {MapMetadata,MissionComparison,MissionHorizon,MissionSite,MissionTerrain,MissionVisibility} from '../mission/missionTypes';

export type SiteLetter='A'|'B';
export const SHACKLETON:MissionSite={latitude_deg:-89.8026005358603,longitude_deg_east:155.95074562959945,observer_height_m:1.5};
const params=(site:MissionSite)=>new URLSearchParams({latitude_deg:String(site.latitude_deg),longitude_deg_east:String(site.longitude_deg_east),observer_height_m:String(site.observer_height_m)});
const readError=(body:unknown,status:number)=>typeof body==='object'&&body!==null&&'detail' in body&&typeof body.detail==='string'?body.detail:`NASA science API returned HTTP ${status}`;
async function getJSON<T>(url:string,signal?:AbortSignal):Promise<T>{
  const response=await fetch(url,{signal});
  const body:unknown=await response.json().catch(()=>null);
  if(!response.ok)throw new Error(readError(body,response.status));
  return body as T;
}
export function useLunarScience(enabled:boolean,date:string,minutes:number,missionBaseline:string|null=null){
  const [pointA,setPointA]=useState<MissionSite>(SHACKLETON);
  const [pointB,setPointB]=useState<MissionSite|null>(null);
  const [active,setActive]=useState<SiteLetter>('A');
  const [target,setTarget]=useState<SiteLetter>('A');
  const [map,setMap]=useState<MapMetadata|null>(null);
  const [reference,setReference]=useState<{kind:string;site_name:string;site_latitude_deg:number;site_longitude_deg_east:number;start_utc:string;end_utc:string;summary:{sun:{visible_hours:number};earth:{visible_hours:number};both:{visible_hours:number}}}|null>(null);
  const [health,setHealth]=useState<{regional_dem_ready:boolean;spice_ready:boolean}|null>(null);
  const [site,setSite]=useState<MissionSite|null>(null);
  const [terrain,setTerrain]=useState<MissionTerrain|null>(null);
  const [horizon,setHorizon]=useState<MissionHorizon|null>(null);
  const [visibility,setVisibility]=useState<MissionVisibility|null>(null);
  const [comparison,setComparison]=useState<MissionComparison|null>(null);
  const [siteBusy,setSiteBusy]=useState(false);
  const [timeBusy,setTimeBusy]=useState(false);
  const [pickBusy,setPickBusy]=useState(false);
  const [error,setError]=useState('');
  const [compareError,setCompareError]=useState('');
  const pickSequence=useRef(0);
  const selected=active==='A'?pointA:pointB??pointA;
  // The analysis interval is independent of the playback cursor. A user can
  // scrub Daniela's scene without recomputing every SPICE sample on each frame.
  const [analysis,setAnalysis]=useState(()=>({
    start:`${date}T00:00:00Z`,
    end:new Date(Date.parse(`${date}T00:00:00Z`)+7*86400000).toISOString(),
    step:60,
  }));
  const start=missionBaseline?`${missionBaseline}T00:00:00Z`:analysis.start;
  const end=missionBaseline?new Date(Date.parse(start)+7*86400000).toISOString():analysis.end;
  const step=analysis.step;
  const setAnalysisRange=useCallback((nextStart:string,nextEnd:string,nextStep:number)=>{
    const begin=Date.parse(nextStart),finish=Date.parse(nextEnd);
    if(!Number.isFinite(begin)||!Number.isFinite(finish)||finish<=begin){
      setError('End UTC must be later than start UTC.');return false;
    }
    if(finish-begin>31*86400000){setError('Choose a maximum of 31 days.');return false;}
    if(![15,30,60,120].includes(nextStep)||(finish-begin)/(nextStep*60000)>3000){
      setError('Choose a larger sample interval for this time range (maximum 3000 samples).');return false;
    }
    setError('');setAnalysis({start:nextStart,end:nextEnd,step:nextStep});return true;
  },[]);

  useEffect(()=>{
    if(!enabled)return;
    const controller=new AbortController();
    void Promise.allSettled([
      getJSON<{regional_dem_ready:boolean;spice_ready:boolean}>('/api/health',controller.signal),
      getJSON<MapMetadata>('/api/map/metadata',controller.signal),
    ]).then(([h,m])=>{
      if(controller.signal.aborted)return;
      if(h.status==='fulfilled')setHealth(h.value);else setError(h.reason?.message??'Science backend is unavailable.');
      if(m.status==='fulfilled')setMap(m.value);else setError(m.reason?.message??'NASA polar map is unavailable.');
    });
    void getJSON<NonNullable<typeof reference>>('/api/reference/shackleton/summary',controller.signal).then(r=>{if(!controller.signal.aborted)setReference(r);}).catch(()=>{});
    return()=>controller.abort();
  },[enabled]);

  useEffect(()=>{
    if(!enabled)return;
    const controller=new AbortController();
    setSite(null);setHorizon(null);setTerrain(null);setVisibility(null);setError('');setSiteBusy(true);
    const query=params(selected).toString();
    void (async()=>{
      try{
        const result=await getJSON<MissionSite>(`/api/site?${query}`,controller.signal);
        if(controller.signal.aborted)return;
        setSite(result);
        const [h,t]=await Promise.all([
          getJSON<MissionHorizon>(`/api/horizon?${query}`,controller.signal),
          getJSON<MissionTerrain>(`/api/terrain?${query}`,controller.signal),
        ]);
        if(controller.signal.aborted)return;
        setHorizon(h);setTerrain(t);
      }catch(e){if(!controller.signal.aborted)setError(e instanceof Error?e.message:String(e));}
      finally{if(!controller.signal.aborted)setSiteBusy(false);}
    })();
    return()=>controller.abort();
  },[enabled,selected.latitude_deg,selected.longitude_deg_east,selected.observer_height_m]);

  useEffect(()=>{
    if(!enabled)return;
    const controller=new AbortController();
    setVisibility(null);setTimeBusy(true);
    const query=params(selected);query.set('start',start);query.set('end',end);query.set('step_minutes',String(step));
    void getJSON<MissionVisibility>(`/api/visibility?${query.toString()}`,controller.signal)
      .then(v=>{if(!controller.signal.aborted)setVisibility(v);})
      .catch(e=>{if(!controller.signal.aborted)setError(e instanceof Error?e.message:String(e));})
      .finally(()=>{if(!controller.signal.aborted)setTimeBusy(false);});
    return()=>controller.abort();
  },[enabled,start,end,selected.latitude_deg,selected.longitude_deg_east,selected.observer_height_m]);

  useEffect(()=>{
    if(!enabled||!pointB){setComparison(null);setCompareError('');return;}
    const controller=new AbortController();
    setComparison(null);setCompareError('');
    const query=new URLSearchParams({
      a_latitude_deg:String(pointA.latitude_deg),a_longitude_deg_east:String(pointA.longitude_deg_east),
      b_latitude_deg:String(pointB.latitude_deg),b_longitude_deg_east:String(pointB.longitude_deg_east),
      a_observer_height_m:String(pointA.observer_height_m),b_observer_height_m:String(pointB.observer_height_m),
      start,end,step_minutes:String(step),
    });
    void getJSON<MissionComparison>(`/api/compare?${query}`,controller.signal)
      .then(v=>{if(!controller.signal.aborted)setComparison(v);})
      .catch(e=>{if(!controller.signal.aborted)setCompareError(e instanceof Error?e.message:String(e));});
    return()=>controller.abort();
  },[enabled,start,end,pointA.latitude_deg,pointA.longitude_deg_east,pointA.observer_height_m,pointB?.latitude_deg,pointB?.longitude_deg_east,pointB?.observer_height_m]);

  const selectExisting=useCallback((letter:SiteLetter)=>{setActive(letter);setTarget(letter);},[]);
  const setSelected=useCallback((value:MissionSite,letter:SiteLetter)=>{
    if(letter==='A')setPointA(value);else setPointB(value);
    setActive(letter);setTarget(letter);setError('');
  },[]);
  const selectCoordinates=useCallback(async(latitude:number,longitude:number,letter:SiteLetter=target)=>{
    if(!Number.isFinite(latitude)||latitude < -90||latitude > -80||!Number.isFinite(longitude)){
      setError('Select a valid lunar south polar latitude between -90° and -80°.');return false;
    }
    const request=++pickSequence.current;
    setPickBusy(true);setError('');
    try{
      const query=new URLSearchParams({latitude_deg:String(latitude),longitude_deg_east:String(longitude),observer_height_m:'1.5'});
      const result=await getJSON<MissionSite>(`/api/site?${query}`);
      if(request!==pickSequence.current)return false;
      setSelected(result,letter);return true;
    }catch(e){if(request===pickSequence.current)setError(e instanceof Error?e.message:String(e));return false;}
    finally{if(request===pickSequence.current)setPickBusy(false);}
  },[target,setSelected]);
  const selectMapPoint=useCallback(async(x:number,y:number,letter:SiteLetter=target)=>{
    const request=++pickSequence.current;setPickBusy(true);setError('');
    try{
      const query=new URLSearchParams({x_m:String(x),y_m:String(y),observer_height_m:'1.5'});
      const result=await getJSON<MissionSite>(`/api/site/from-map?${query}`);
      if(request!==pickSequence.current)return false;
      setSelected(result,letter);return true;
    }catch(e){if(request===pickSequence.current)setError(e instanceof Error?e.message:String(e));return false;}
    finally{if(request===pickSequence.current)setPickBusy(false);}
  },[target,setSelected]);

  const sample=useMemo(()=>{
    const instant=Date.parse(`${date}T00:00:00Z`)+Math.min(1439,minutes)*60000;
    if(!visibility||instant<Date.parse(start)||instant>Date.parse(end))return null;
    return interpolateFrame(visibility.timeline,instant,horizon);
  },[visibility,horizon,date,minutes,start,end]);
  return {reference,pointA,pointB,active,target,setTarget,selectExisting,selected,selectCoordinates,selectMapPoint,map,health,site,terrain,horizon,visibility,comparison,sample,siteBusy,timeBusy,pickBusy,error,compareError,start,end,step,setAnalysisRange};
}
