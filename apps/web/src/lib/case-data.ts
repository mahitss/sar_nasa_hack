// RIVET investigation data model.
// Values are copied from committed manifests and scientific notes.
// No derived claims beyond those sources.

import { FIFTY_EVIDENCE_RECORDS } from "./evidence-50";

export const CASE = {
  name: "Kuwari landslide-dammed lake",
  place: "Bageshwar district, Uttarakhand, India",
  period: "6 September 2026 – 30 September 2026 (NISAR acquisition pair)",
  status: "Historical case investigation. No confirmed water detection.",
  warning:
    "No confirmed water detection, lake area, shoreline, or breach prediction exists in this record. P05023 is provisional.",
} as const;

export const DISCOVERY = {
  west: 79.75,
  south: 30.03,
  east: 79.87,
  north: 30.15,
  label: "Discovery window (not a surveyed lake boundary)",
} as const;

export const ACRONYMS = {
  CRID: "Composite Release Identifier",
  GCOV: "Geocoded Covariance",
  GSLC: "Geocoded Single Look Complex",
  SCL: "Scene Classification Layer",
  DEM: "Digital Elevation Model",
  MOE: "Medium precision Orbit Ephemeris (observed)",
  NOE: "Near real-time Orbit Ephemeris (expected by filename token N)",
  NRP: "Near real-time Radar Pointing (expected by filename token N)",
} as const;

export type EvidenceStatus = "Observation" | "Provisional" | "Gap" | "Unresolved";
export type EvidenceKind = "observation" | "measurement" | "interpretation" | "hypothesis" | "gap" | "model";
export type EvidenceCategory = "SAR" | "Optical" | "Terrain" | "Review" | "Metadata" | "Hydrology";

export interface EvidenceItem {
  id: string;
  title: string;
  mission: string;
  category: EvidenceCategory;
  date?: string;
  status: EvidenceStatus;
  kind: EvidenceKind;
  reviewState?: "accepted" | "needs_investigation" | "draft" | "submitted" | "rejected";
  instrument?: string;
  coordinates?: [number, number];
  elevation?: string;
  metrics?: Record<string, string | number>;
  summary: string;
  details: string[];
  source: string;
  limitations: string[];
}

export const EVIDENCE: EvidenceItem[] = FIFTY_EVIDENCE_RECORDS;

export const ACQUISITIONS = [
  {
    date: "6 September 2026",
    iso: "2026-09-06",
    granule:
      "NISAR_L2_PR_GCOV_030_005_D_073_4005_DHDH_A_20260906T132236_20260906T132311_P05023_N_F_J_001.h5",
    rawStable: 6,
    filteredStable: 0,
  },
  {
    date: "30 September 2026",
    iso: "2026-09-30",
    granule:
      "NISAR_L2_PR_GCOV_032_005_D_073_4005_DHDH_A_20260930T132236_20260930T132311_P05023_N_F_J_001.h5",
    rawStable: 12,
    filteredStable: 0,
  },
] as const;

export const COMPARISON_FIELDS = [
  { label: "Group", value: "D40" },
  { label: "CRID", value: "P05023, provisional" },
  { label: "Track / frame", value: "5 / 73, descending" },
  { label: "Mode", value: "Frequency A, 40 MHz, HH+HV" },
  { label: "Look / pass", value: "Left / Descending" },
  { label: "orbitType", value: "MOE" },
  { label: "attitudeType", value: "Custom" },
  { label: "Filename token N", value: "Expects NOE and NRP. Unresolved mismatch." },
  { label: "X coordinates", value: "710 samples, step +500 m" },
  { label: "Y coordinates", value: "699 samples, step -500 m" },
  { label: "Height samples", value: "21 values, step +500 m, WGS84 ellipsoid" },
  { label: "Incidence cube", value: "21 x 699 x 710. Values not extracted." },
  { label: "shadowMaskingApplied", value: "The string False" },
  {
    label: "Processor DEM",
    value: "Copernicus DEM 30 m release 2023_1, WGS84 ellipsoid. Not the local Mission 011 tiles.",
  },
] as const;

export const MISSION012 = {
  wrapperBytesRead: 68021,
  orbitType: "MOE",
  attitudeType: "Custom",
  shadowMaskingApplied: "False",
  grid: { x: 710, y: 699, height: 21 },
  steps: { x: 500, y: -500, height: 500 },
  incidenceShape: "21 x 699 x 710",
  cubeValuesRead: false,
  processorDem:
    "Copernicus DEM 30 m release 2023_1, COP-DEM_GLO-30-DGED/2023_1, referenced to the WGS84 ellipsoid",
} as const;

export const LIMITATIONS = [
  "No confirmed water detection, lake area, or shoreline is in this record.",
  "P05023 is provisional and is not mixed with validated CRID P05036.",
  "Filename N expects NOE and NRP. Both products read orbitType MOE and attitudeType Custom. No geolocation error was measured.",
  "The GSLC valid-samples mask is not a water, shadow, or layover classification.",
  "Mission 006 filtered stability has no fully sweep-stable candidate.",
  "Mission 007 left all 23 patches as requests for independent evidence.",
  "Optical scenes are not same-date ground truth. The SCL water label is not validation.",
  "The local DEM tiles are not the ellipsoid-referenced 2023_1 DEM named by the NISAR processor.",
  "No shadow or layover mask has been created.",
  "No breach, flood, or emergency warning is claimed.",
] as const;

export const NEXT_STEPS = [
  "Resolve the filename N versus observed MOE/Custom orbit and pointing inconsistency.",
  "Extract incidence cube values and validate geometry.",
  "Acquire same-date independent optical or field evidence.",
  "Run a terrain shadow/layover model using the processor DEM, not candidate pixels as truth.",
  "Reconcile the EGM2008 versus WGS84-G1150 vertical reference before height conversion.",
  "Keep P05023 provisional; do not mix CRIDs.",
] as const;

export interface InvestigationPoint {
  id: string;
  name: string;
  category: "Dam & Hazard" | "Hydrology" | "Settlement" | "SAR Geometry" | "Observation";
  color: string;
  coordinates: [number, number]; // [lng, lat]
  elevation: string;
  description: string;
  scientificContext: string;
}

export const INVESTIGATION_POINTS: InvestigationPoint[] = [
  {
    id: "kuwari-dam",
    name: "Kuwari Landslide Dam Site",
    category: "Dam & Hazard",
    color: "#f59e0b",
    coordinates: [79.812, 30.091],
    elevation: "2,450 m",
    description: "Narrow gorge constriction identified as the primary debris damming point across the drainage channel.",
    scientificContext: "Debris blockage location analyzed in Mission 001/003. Evaluated for breach mechanics and retention capacity.",
  },
  {
    id: "upstream-basin",
    name: "Upstream Inundation Zone (Candidate Basin)",
    category: "Hydrology",
    color: "#06b6d4",
    coordinates: [79.825, 30.108],
    elevation: "2,465 m",
    description: "Low-gradient valley basin where post-dam water accumulation was evaluated by dual-date NISAR GCOV crops.",
    scientificContext: "Sweep analysis (Mission 006) yielded 0 sustained filtered candidates in both 6-Sept and 30-Sept acquisitions.",
  },
  {
    id: "kuwari-village",
    name: "Kuwari Village Outskirts",
    category: "Settlement",
    color: "#ec4899",
    coordinates: [79.795, 30.078],
    elevation: "2,120 m",
    description: "Downstream terrace settlement closest to the valley drainage outlet.",
    scientificContext: "Primary downstream vulnerability monitoring point for hydrological assessment.",
  },
  {
    id: "saryu-confluence",
    name: "Pindar / Saryu River Confluence",
    category: "Hydrology",
    color: "#3b82f6",
    coordinates: [79.772, 30.045],
    elevation: "1,780 m",
    description: "Regional hydrological confluence point where mountain runoff enters the primary river network.",
    scientificContext: "Boundary baseline for downstream surge dissipation and gauge comparison.",
  },
  {
    id: "radar-shadow-ridge",
    name: "North Ridge Radar Shadow Crest",
    category: "SAR Geometry",
    color: "#a855f7",
    coordinates: [79.782, 30.135],
    elevation: "3,580 m",
    description: "High-relief alpine ridge causing radar terrain layover and foreshortening under descending Left-look pass.",
    scientificContext: "Explains steep incidence angle distortion (~37°) evaluated in Mission 010 terrain geometry feasibility.",
  },
  {
    id: "nisar-ground-track",
    name: "NISAR Descending Track 5 Ground Reference",
    category: "SAR Geometry",
    color: "#8b5cf6",
    coordinates: [79.855, 30.142],
    elevation: "2,890 m",
    description: "Descending orbit line-of-sight reference (Track 5, Frame 73, Frequency A 40 MHz).",
    scientificContext: "Acquisition geometry anchor for provisional CRID P05023 granule comparisons.",
  },
  {
    id: "bageshwar-gauge",
    name: "Bageshwar Valley Meteorological Gauge",
    category: "Observation",
    color: "#10b981",
    coordinates: [79.865, 30.038],
    elevation: "1,650 m",
    description: "Monsoon precipitation monitoring station recording late-monsoon rainfall events.",
    scientificContext: "Precipitation timeline correlates with September 2026 satellite acquisition intervals.",
  },
];
