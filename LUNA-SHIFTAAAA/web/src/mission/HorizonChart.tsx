import type {MissionHorizon,MissionSample} from './missionTypes';
export default function HorizonChart({horizon,sample,heading}:{horizon:MissionHorizon|null;sample:MissionSample|null;heading:number}){
  const left=35,right=625,top=20,bottom=145;
  const valid=horizon?.samples.filter(p=>p.horizon_elevation_deg!==null)??[];
  const min=Math.min(-8,...valid.map(p=>p.horizon_elevation_deg as number),sample?.sun.elevation_deg??0,sample?.earth.elevation_deg??0)-4;
  const max=Math.max(12,...valid.map(p=>p.horizon_elevation_deg as number),sample?.sun.elevation_deg??0,sample?.earth.elevation_deg??0)+4;
  const x=(a:number)=>left+a/360*(right-left);
  const y=(e:number)=>bottom-(e-min)/(max-min)*(bottom-top);
  let path='';let previous=false;
  for(const p of horizon?.samples??[]){if(p.horizon_elevation_deg===null){previous=false;continue;}path+=`${previous?'L':'M'}${x(p.azimuth_deg).toFixed(1)},${y(p.horizon_elevation_deg).toFixed(1)} `;previous=true;}
  const bands=[-360,0,360].map(shift=>[Math.max(0,heading-40+shift),Math.min(360,heading+40+shift)]).filter(([a,b])=>b>a);
  return <svg viewBox="0 0 650 178" role="img" aria-label="Terrain horizon with Sun and Earth markers and camera heading" className="mc-horizon-svg">
    <rect width="650" height="178" fill="#0b1c2b" rx="10"/>
    {bands.map(([a,b],i)=><rect key={i} x={x(a)} y={top} width={x(b)-x(a)} height={bottom-top} fill="#246987" opacity="0.36"/>)}
    {[0,90,180,270,360].map(a=><g key={a}><line x1={x(a)} x2={x(a)} y1={top} y2={bottom} stroke="#315169"/><text x={x(a)} y="167" textAnchor="middle" fill="#9eb6cc" fontSize="12">{a}°</text></g>)}
    {horizon&&<path d={path} fill="none" stroke="#d0e2ef" strokeWidth="2.3"/>}
    <line x1={x(heading)} x2={x(heading)} y1={top} y2={bottom} stroke="#6ce7da" strokeDasharray="5 4"/>
    {sample&&(['sun','earth'] as const).map(kind=><circle key={kind} cx={x(sample[kind].azimuth_deg)} cy={y(sample[kind].elevation_deg)} r="6.5" fill={kind==='sun'?'#ffd37d':'#74c9ff'} stroke="#0b1c2b" strokeWidth="2"/>)}
    <text x="10" y="14" fontSize="11" fill="#a9c0d3">Azimuth / terrain elevation · camera heading {heading.toFixed(0)}°</text>
  </svg>;
}
