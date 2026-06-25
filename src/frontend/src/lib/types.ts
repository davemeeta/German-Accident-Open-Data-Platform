export interface Provenance { source: string; license: string | null; license_url: string | null; }
export interface CountResponse { query: Record<string, unknown>; accident_count: number; provenance: Provenance[]; }
export interface RegionCount { ags: string; name: string | null; level: string; year: number | null; accident_count: number; }
export interface Hotspot {
  lat: number; lon: number; district: string | null; district_ags: string;
  total: number; fatal: number; serious: number; light: number;
  pedestrian: number; bicycle: number; severity_score: number;
}
export interface HotspotResponse {
  ranked_by: string; severity_weights: Record<string, number>;
  approx_cell_size_m: number; hotspot_count: number;
  hotspots: Hotspot[]; provenance: Provenance[];
}
export interface TrendPoint { year: number; accident_count: number; }
export interface TrendResponse { state: string | null; series: TrendPoint[]; provenance: Provenance[]; }
export interface ChoroplethFeature {
  type: "Feature"; geometry: GeoJSON.Geometry;
  properties: { ags: string; name: string | null; value: number | null };
}
export interface ChoroplethResponse {
  type: "FeatureCollection"; metric: string; value_label: string;
  year: number; feature_count: number; features: ChoroplethFeature[];
}
