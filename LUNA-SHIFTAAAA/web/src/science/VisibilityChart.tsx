import {useMemo} from 'react';
import type {MissionSample} from '../mission/missionTypes';
type Kind='sun'|'earth';
interface Props {timeline:MissionSample[];selectedTime:string|null;kind:Kind}
const W=338,H=134,LEFT=32,RIGHT=8,TOP=15,BOTTOM=22;
const finite=(v:number|null|undefined):v is number=>typeof v==='number'&&Number.isFinite(v);
export default function VisibilityChart({timeline,selectedTime,kind}:Props){
  const plot=useMemo(()=>{
    if(timeline.length<2)return null;
    const t0=Date.parse(timeline[0].time_utc),t1=Date.parse(timeline[timeline.length-1].time_utc);
    if(!(t1>t0))return null;
    const all=timeline.flatMap(p=>[p[kind].elevation_deg,p[kind].horizon_elevation_deg]).filter(finite);
    if(!all.length)return null;
    const ymin=Math.floor((Math.min(...all,0)-2)/5)*5,ymax=Math.ceil((Math.max(...all,0)+2)/5)*5;
    const x=(time:number)=>LEFT+(time-t0)/(t1-t0)*(W-LEFT-RIGHT);
    const y=(value:number)=>H-BOTTOM-(value-ymin)/(ymax-ymin)*(H-TOP-BOTTOM);
    const paths=(type:'elevation_deg'|'horizon_elevation_deg')=>{
      const fragments:string[]=[];let path='';
      for(const frame of timeline){const elevation=frame[kind][type];
        if(!finite(elevation)){if(path){fragments.push(path);path='';}continue;}
        const p=`${x(Date.parse(frame.time_utc)).toFixed(2)},${y(elevation).toFixed(2)}`;
        path+=`${path?'L':'M'}${p}`;
      }
      if(path)fragments.push(path);
      return fragments;
    };
    const cursor=selectedTime?Date.parse(selectedTime):NaN;
    return {line:paths('elevation_deg'),horizon:paths('horizon_elevation_deg'),
      x0:LEFT,x1:W-RIGHT,y0:TOP,y1:H-BOTTOM,
      zero:y(0),min:ymin,max:ymax,
      cursor:Number.isFinite(cursor)&&cursor>=t0&&cursor<=t1?x(cursor):null,
      labelStart:new Date(t0).toISOString().slice(5,10),labelEnd:new Date(t1).toISOString().slice(5,10)};
  },[timeline,kind,selectedTime]);
  if(!plot)return <p className="science-caption">Awaiting a computed SPICE time series.</p>;
  const color=kind==='sun'?'#ffd07a':'#82cdf6';
  return <div className="science-timeseries"><div className="science-timeseries-title">{kind==='sun'?'SUN ELEVATION':'EARTH ELEVATION'} <span>Body center vs terrain horizon</span></div>
  <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label={`${kind} elevation and terrain horizon over the selected UTC interval`}>
    <line x1={plot.x0} y1={plot.zero} x2={plot.x1} y2={plot.zero} stroke="#51647c" strokeWidth="0.7"/>
    <line x1={plot.x0} y1={plot.y0} x2={plot.x0} y2={plot.y1} stroke="#466074" strokeWidth="0.7"/>
    <text x="2" y={plot.y0+4} fontSize="9" fill="#8eabc1">{plot.max}°</text><text x="5" y={plot.y1} fontSize="9" fill="#8eabc1">{plot.min}°</text>
    {plot.horizon.map((p,i)=><path key={'h'+i} d={p} fill="none" stroke="#c2cbd6" strokeWidth="1.4" strokeDasharray="4 3"/>)}
    {plot.line.map((p,i)=><path key={'e'+i} d={p} fill="none" stroke={color} strokeWidth="1.8"/>)}
    {plot.cursor!==null&&<line x1={plot.cursor} y1={plot.y0} x2={plot.cursor} y2={plot.y1} stroke="#69e3cc" strokeWidth="1.2"/>}
    <text x={plot.x0} y={H-5} fill="#8eabc1" fontSize="9">{plot.labelStart}</text>
    <text x={plot.x1} y={H-5} textAnchor="end" fill="#8eabc1" fontSize="9">{plot.labelEnd} UTC</text>
  </svg><div className="science-timeseries-key"><span style={{color}}>━━━━ Body elevation</span><span>┄┄ Terrain horizon</span><span style={{color:'#69e3cc'}}>│ Playback UTC</span></div></div>;
}
