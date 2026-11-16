import type {MissionBody,MissionHorizon,MissionSample,MissionWindow} from './missionTypes';
export const utcValue = (dateTimeLocal:string):string => `${dateTimeLocal.length===16?dateTimeLocal+':00':dateTimeLocal}Z`;
export const utcInput = (iso:string):string => new Date(iso).toISOString().slice(0,16);
export const durationLabel = (hours:number):string => `${hours.toFixed(2)} h`;
export function horizonAt(horizon:MissionHorizon|null,az:number):number|null {
  if(!horizon||!horizon.samples.length)return null;
  const pts=horizon.samples;
  const a=((az%360)+360)%360;
  for(let i=0;i<pts.length;i++){
    const p=pts[i],n=pts[(i+1)%pts.length],lo=p.azimuth_deg,hi=i===pts.length-1?n.azimuth_deg+360:n.azimuth_deg;
    const query=a<lo?a+360:a;
    if(query>=lo&&query<=hi){
      if(p.horizon_elevation_deg===null||n.horizon_elevation_deg===null)return null;
      const f=(query-lo)/(hi-lo);
      return p.horizon_elevation_deg+(n.horizon_elevation_deg-p.horizon_elevation_deg)*f;
    }
  }
  return null;
}
export function interpolateBody(a:MissionBody,b:MissionBody,f:number,horizon:MissionHorizon|null):MissionBody {
  const vector=a.direction_local_east_north_up.map((v,i)=>v*(1-f)+b.direction_local_east_north_up[i]*f) as [number,number,number];
  const len=Math.hypot(...vector)||1;
  const [east,north,up]=vector.map(v=>v/len);
  const azimuth_deg=(Math.atan2(east,north)*180/Math.PI+360)%360;
  const elevation_deg=Math.asin(Math.max(-1,Math.min(1,up)))*180/Math.PI;
  const h=horizonAt(horizon,azimuth_deg);
  return {azimuth_deg,elevation_deg,horizon_elevation_deg:h,visible_center:h===null?null:elevation_deg>h,direction_local_east_north_up:[east,north,up]};
}
export function interpolateFrame(timeline:MissionSample[],ms:number,horizon:MissionHorizon|null):MissionSample|null {
  if(!timeline.length)return null;
  let lo=0,hi=timeline.length-1;
  while(lo<hi){const mid=(lo+hi)>>1;if(Date.parse(timeline[mid].time_utc)<ms)lo=mid+1;else hi=mid;}
  const next=timeline[lo],prev=timeline[Math.max(0,lo-1)];
  const a=Date.parse(prev.time_utc),b=Date.parse(next.time_utc),f=b===a?0:Math.max(0,Math.min(1,(ms-a)/(b-a)));
  return {time_utc:new Date(Math.max(Date.parse(timeline[0].time_utc),Math.min(Date.parse(timeline[timeline.length-1].time_utc),ms))).toISOString(),
    sun:interpolateBody(prev.sun,next.sun,f,horizon),earth:interpolateBody(prev.earth,next.earth,f,horizon)};
}
export function recommendedWindow(windows:MissionWindow[],analysisStart:string,delayHours:number,durationHours:number):string|null {
  const earliest=Date.parse(analysisStart)+delayHours*3600000;
  for(const w of windows){const candidate=Math.max(earliest,Date.parse(w.start_utc));if(candidate+durationHours*3600000<=Date.parse(w.end_utc)+1)return new Date(candidate).toISOString();}
  return null;
}
