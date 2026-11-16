export type Vector3Km = readonly [number, number, number];
export type ViewMode = 'orbital' | 'earth' | 'surface';
export interface LandingSite { id:string; name:string; latitudeDeg:number; longitudeDeg:number; description:string; tag:string; }
export interface SpaceSnapshot {
  timestampUTC:string;
  frame:'MOON_ME';
  earthFromMoonKm:Vector3Km;
  sunFromMoonKm:Vector3Km;
  sites:LandingSite[];
  source:string;
  status:'demo'|'verified';
}
