export const discovery = {
  name: "Kuwari discovery window",
  place: "Bageshwar, Uttarakhand, India",
  west: 79.75,
  south: 30.03,
  east: 79.87,
  north: 30.15,
  role: "Catalogue discovery area. Not a surveyed lake boundary.",
} as const;

export const caseSummary = {
  title: "RIVET",
  subtitle: "River Incident Verification & Evidence Twin",
  caseName: "Kuwari historical investigation",
  period: "6 and 30 September 2026",
  status: "Provisional research record",
  warning: "No confirmed water detection, area, or shoreline exists in this repository.",
};

export type EvidenceItem = {
  id: string;
  title: string;
  source: string;
  status: "Provisional" | "Observation" | "Gap";
  summary: string;
  details: string[];
};

export const evidenceItems: EvidenceItem[] = [
  {
    id: "gcov-pair",
    title: "NISAR P05023 GCOV pair",
    source: "data/manifests/nisar_kuwari_catalogue.json",
    status: "Provisional",
    summary: "Group D40, descending track 5, frame 73, Frequency A 40 MHz, HH+HV. CRID P05023 stays provisional.",
    details: [
      "6 September 2026 granule NISAR_L2_PR_GCOV_030_005_D_073_4005_DHDH_A_20260906T132236_20260906T132311_P05023_N_F_J_001, start 13:22:36Z.",
      "30 September 2026 granule NISAR_L2_PR_GCOV_032_005_D_073_4005_DHDH_A_20260930T132236_20260930T132311_P05023_N_F_J_001, start 13:22:36Z.",
      "Filename accuracy token N expects orbit ephemeris NOE. Both products' HDF5 orbitType is MOE. Attitude type is Custom, not the NRP implied by N. The mismatch is unresolved.",
      "Look direction Left. Orbit pass descending. Radar-grid spacing is 500 m. Incidence cubes were not extracted.",
    ],
  },
  {
    id: "sweep",
    title: "Mission 006 candidate sweep",
    source: "data/manifests/mission006_sweep_manifest.json",
    status: "Observation",
    summary: "1,092 frozen parameter sets on each date. No pixel is a filtered candidate in every set.",
    details: [
      "6 September: 6 raw fully sweep-stable pixels. Filtered fully sweep-stable count is 0.",
      "30 September: 12 raw fully sweep-stable pixels. Filtered fully sweep-stable count is 0.",
      "These counts are algorithmic candidate tallies. They are not a water extent.",
    ],
  },
  {
    id: "review-patches",
    title: "Mission 007 human review",
    source: "data/manifests/mission007_review_manifest.json",
    status: "Provisional",
    summary: "23 patches were inventoried in crop row and column. Every record requests independent evidence.",
    details: [
      "No reviewer accepted or rejected a patch as water.",
      "Coordinates were not converted to longitude and latitude.",
      "A patch is not a lake.",
    ],
  },
  {
    id: "optical",
    title: "Optical catalogue and cloud masks",
    source: "docs/science/mission008-optical-archive-discovery.md",
    status: "Gap",
    summary: "No Sentinel-2 or Landsat scene was found on either NISAR date.",
    details: [
      "Nearest low scene-cloud Level-2A neighbour is Sentinel-2B on 2 October 2026, tile 44RLU, scene cloud 8.01%, about 40.1 hours after 30 September.",
      "Inside that discovery window, 17.557% of SCL pixels are cloud and 8.963% are cloud shadow. The SCL water label covers 19 pixels and is not validation.",
      "Landsat 8 on 1 October 2026 has scene cloud 4.82%. Its QA_PIXEL file was not downloaded.",
    ],
  },
  {
    id: "terrain",
    title: "DEM and radar geometry",
    source: "docs/science/mission011-terrain-acquisition-and-geometry-inspection.md",
    status: "Observation",
    summary: "Two Copernicus GLO-30 geocells were acquired. No shadow or layover mask exists.",
    details: [
      "Geocells Copernicus_DSM_10_N30_00_E079_00 and Copernicus_DSM_10_N29_00_E079_00. The buffered crop is 793 by 793 point samples.",
      "The public GeoTIFF vertical reference is not reconciled: the XML names EGM2008 and also WGS84-G1150.",
      "The NISAR processor names a different input: Copernicus DEM 30 m release 2023_1, referenced to the WGS84 ellipsoid. shadowMaskingApplied is the string False.",
    ],
  },
];

export const limitations = [
  "No confirmed water detection, lake area, or shoreline is in this record.",
  "P05023 is provisional and is not mixed with validated CRID P05036.",
  "Filename N and HDF5 orbitType MOE disagree. No geolocation error was measured.",
  "The GSLC valid-samples mask is not a water, shadow, or layover classification.",
  "Mission 006 filtered stability has no fully sweep-stable candidate.",
  "Mission 007 left all 23 patches as requests for independent evidence.",
  "Optical scenes are not same-date ground truth.",
  "A stored DEM is not a validated terrain-shadow model.",
  "No breach, flood, or emergency warning is claimed.",
];

export const reportExport = {
  product: "RIVET submission prototype",
  persistedToBackend: false,
  case: caseSummary,
  discovery,
  evidence: evidenceItems,
  limitations,
};
