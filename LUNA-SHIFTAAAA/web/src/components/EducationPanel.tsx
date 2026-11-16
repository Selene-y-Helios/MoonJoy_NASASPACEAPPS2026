import {BookOpen, ExternalLink, Info, MapPin, Rocket} from 'lucide-react';

export interface HistoricalMission {
  id: string;
  name: string;
  mission_type: 'robotic_lander' | 'crewed_landing';
  landing_date_utc: string;
  landing_site: string;
  latitude_deg: number;
  longitude_deg_east: number;
  coordinate_quality: string;
  achievement: string;
  description: string;
  educational_question: string;
  sources: Array<{title:string;url:string;fact_role:string}>;
}

interface Props {mission:HistoricalMission | null; count:number; error:string; loading:boolean;}
export default function EducationPanel({mission,count,error,loading}:Props) {
  return <>
    <section className="detail-card education-card">
      <div className="card-heading"><span><BookOpen size={16}/> STUDENT EXPLORER</span><span className="card-pill">NASA HISTORY</span></div>
      <h2>{mission?.name ?? 'Explore the Moon'}</h2>
      {error ? <p role="alert">{error}</p> : loading ? <p>Loading the NASA landing catalog...</p> : mission ? <>
        <p>{mission.description}</p>
        <div className="education-facts">
          <span><Rocket size={14}/> {mission.mission_type==='crewed_landing'?'Crewed landing':'Robotic landing'}</span>
          <span><MapPin size={14}/> {mission.landing_site}</span>
          <span>Landing date: {mission.landing_date_utc}</span>
        </div>
        <p><strong>Historic milestone:</strong> {mission.achievement}</p>
        <p className="education-question"><strong>Think about it:</strong> {mission.educational_question}</p>
      </> : <p>Choose a NASA landing marker on the Moon to discover its mission, location, and scientific achievements. {count} historical landing sites are available.</p>}
    </section>
    <section className="detail-card education-card">
      <div className="card-heading"><span><Info size={16}/> DATA & SOURCES</span><span className="card-pill outline">EDUCATIONAL</span></div>
      {mission ? <>
        <p>Latitude {mission.latitude_deg.toFixed(4)}°, east longitude {mission.longitude_deg_east.toFixed(4)}°.</p>
        {mission.coordinate_quality==='approximate_historical'&&<p>Historical coordinates are approximate.</p>}
        <div className="education-sources">{mission.sources.map((source,index)=><a key={`${source.url}-${index}`} href={source.url} target="_blank" rel="noreferrer"><ExternalLink size={13}/> {source.title}</a>)}</div>
      </> : <p>Student mode uses historical NASA landing coordinates, not the south-polar LOLA elevation model. Orbital positions are an illustrative visualization. Scientific Sun/Earth visibility is calculated in Professional mode.</p>}
    </section>
  </>;
}
