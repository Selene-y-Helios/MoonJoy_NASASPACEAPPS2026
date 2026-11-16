export interface MissionSite {
  latitude_deg: number;
  longitude_deg_east: number;
  observer_height_m: number;
  dem_elevation_m?: number;
  elevation_dem?: string;
  map_x_m?: number;
  map_y_m?: number;
}
export interface MissionWindow {
  start_utc: string;
  end_utc: string;
  duration_hours: number;
}
export interface MissionBody {
  azimuth_deg: number;
  elevation_deg: number;
  visible_center: boolean | null;
  horizon_elevation_deg: number | null;
  direction_local_east_north_up: [number,number,number];
}
export interface MissionSample { time_utc: string; sun: MissionBody; earth: MissionBody }
export interface MissionVisibility {
  metadata: {start_utc:string;end_utc:string;warnings:string[]};
  timeline: MissionSample[];
  summary: Record<'sun'|'earth'|'both', {visible_hours:number;unknown_hours:number;visible_percent_of_interval:number}>;
  windows: Record<'sun'|'earth'|'both', MissionWindow[]>;
}
export interface MissionHorizon { samples: {azimuth_deg:number;horizon_elevation_deg:number|null}[] }
export interface MissionTerrain { positions:number[];indices:number[];metadata:{dem_source:string;valid_vertices:number} }
export interface MissionComparisonPoint {
  sun_visible_hours:number;earth_visible_hours:number;sun_earth_overlap_hours:number;
  earth_windows:MissionWindow[];sun_windows:MissionWindow[];
  opportunity:{total_hours:number;longest_window_hours:number;window_count:number;windows:MissionWindow[]};
}
export interface MissionComparison {
  points:Record<'A'|'B',MissionComparisonPoint>;
  shared_opportunity:{total_hours:number;windows:MissionWindow[]};
}
export interface MissionEvaluation {
  passed:boolean;status:string;message:string;
  checks:{delay_respected:boolean;within_analysis_range:boolean;continuous_sun_earth_visibility:boolean};
  earliest_allowed_start_utc:string;operation_start_utc:string;operation_end_utc:string;
  recommended_start_utc:string|null;
  overlap_hours:number;sun_visible_hours:number;earth_visible_hours:number;
  candidate_windows:MissionWindow[];
}
export interface MapMetadata {
  url:string;
  bounds_projected_m:{left:number;right:number;top:number;bottom:number};
}
