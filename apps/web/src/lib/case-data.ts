// RIVET investigation data model.
// Values are copied from committed manifests and scientific notes.
// No derived claims beyond those sources.

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
export type EvidenceKind = "observation" | "measurement" | "interpretation" | "hypothesis" | "gap";
export type EvidenceCategory = "SAR" | "Optical" | "Terrain" | "Review" | "Metadata";

export interface EvidenceItem {
  id: string;
  title: string;
  mission: string;
  category: EvidenceCategory;
  date?: string;
  status: EvidenceStatus;
  kind: EvidenceKind;
  summary: string;
  details: string[];
  source: string;
  limitations: string[];
}

export const EVIDENCE: EvidenceItem[] = [
  {
    id: "gcov-raster-qc",
    title: "GCOV raster quality control",
    mission: "003",
    category: "SAR",
    date: "2026-09-06",
    status: "Observation",
    kind: "measurement",
    summary:
      "Both Frequency A crops share EPSG:32644, 1171 x 1343 pixels, 10 m posting. The GCOV mask is a valid-samples subswath mask.",
    details: [
      "Mask codes on the crops are 0 and 1. Code 0 is invalid or partially focused. Code 1 is a valid subswath sample.",
      "numberOfLooks is adaptive multi-looking, not a confidence score.",
      "The QC did not classify water.",
    ],
    source: "data/manifests/mission003_raster_qc.json",
    limitations: [
      "Mask is a valid-samples subswath mask, not water, shadow, or layover.",
      "numberOfLooks is not a confidence score.",
    ],
  },
  {
    id: "gslc-mask-qc",
    title: "GSLC validity-mask quality control",
    mission: "003",
    category: "SAR",
    date: "2026-09-06",
    status: "Observation",
    kind: "measurement",
    summary:
      "Both native GSLC masks are constant code 1 on a 5 m grid. That code is a valid sample, not water, shadow, or layover.",
    details: [
      "Inspected path: /science/LSAR/GSLC/grids/frequencyA/mask.",
      "Masks were not resampled onto the GCOV grid and were not used as a terrain mask.",
    ],
    source: "data/manifests/mission003_gslc_mask_qc.json",
    limitations: [
      "GSLC valid-samples mask is not a water, shadow, or layover classification.",
    ],
  },
  {
    id: "gcov-pair",
    title: "NISAR P05023 GCOV pair",
    mission: "003/012",
    category: "SAR",
    date: "2026-09-06",
    status: "Provisional",
    kind: "observation",
    summary:
      "Group D40, descending track 5, frame 73, Frequency A 40 MHz, HH+HV. CRID P05023 stays provisional.",
    details: [
      "6 September 2026 granule NISAR_L2_PR_GCOV_030_005_D_073_4005_DHDH_A_20260906T132236_20260906T132311_P05023_N_F_J_001, start 13:22:36Z.",
      "30 September 2026 granule NISAR_L2_PR_GCOV_032_005_D_073_4005_DHDH_A_20260930T132236_20260930T132311_P05023_N_F_J_001, start 13:22:36Z.",
      "Ascending scenes and other CRIDs are not part of this comparison.",
    ],
    source: "data/manifests/nisar_kuwari_catalogue.json",
    limitations: [
      "P05023 is provisional and is not mixed with validated CRID P05036.",
      "Filename N expects NOE and NRP; observed orbitType is MOE and attitudeType is Custom. Unresolved.",
    ],
  },
  {
    id: "candidate-sweep",
    title: "Mission 006 candidate sensitivity sweep",
    mission: "006",
    category: "SAR",
    date: "2026-09-06",
    status: "Observation",
    kind: "measurement",
    summary:
      "1,092 frozen parameter sets on each date. No pixel is a filtered candidate in every set.",
    details: [
      "6 September: 6 raw fully sweep-stable pixels. Filtered fully sweep-stable count is 0.",
      "30 September: 12 raw fully sweep-stable pixels. Filtered fully sweep-stable count is 0.",
      "These are algorithmic stability counts, not water detections.",
    ],
    source: "data/manifests/mission006_sweep_manifest.json",
    limitations: [
      "Mission 006 filtered stability has no fully sweep-stable candidate.",
      "Counts are algorithmic stability, not water.",
    ],
  },
  {
    id: "patch-review",
    title: "Mission 007 human patch review",
    mission: "007",
    category: "Review",
    date: "2026-09-06",
    status: "Provisional",
    kind: "interpretation",
    summary: "23 patches were inventoried in crop row and column. Every record requests independent evidence.",
    details: [
      "No reviewer accepted or rejected a patch as water.",
      "All 23 patches require independent evidence.",
    ],
    source: "data/manifests/mission007_review_manifest.json",
    limitations: [
      "Mission 007 left all 23 patches as requests for independent evidence.",
      "No patch is confirmed water.",
    ],
  },
  {
    id: "optical-catalogue",
    title: "Mission 008 optical catalogue",
    mission: "008",
    category: "Optical",
    date: "2026-09-06",
    status: "Gap",
    kind: "gap",
    summary: "No Sentinel-2 or Landsat scene was found on either NISAR date.",
    details: [
      "Nearest low scene-cloud Level-2A neighbour is Sentinel-2B on 2 October 2026, tile 44RLU, scene cloud 8.01%, about 40.1 hours after 30 September.",
      "Landsat 8 on 1 October 2026, path 145 row 39, has scene cloud 4.82%.",
      "Nearby scenes are not same-date ground truth.",
    ],
    source: "docs/science/mission008-optical-archive-discovery.md",
    limitations: [
      "Optical scenes are not same-date ground truth.",
    ],
  },
  {
    id: "cloud-mask-qc",
    title: "Mission 009 cloud-mask QC",
    mission: "009",
    category: "Optical",
    date: "2026-10-02",
    status: "Observation",
    kind: "measurement",
    summary:
      "The 2 October Sentinel-2 window is not cloud-free. The SCL water label is not validation.",
    details: [
      "384,510 SCL pixels. Cloud/cirrus classes cover 17.557%. Cloud shadow covers 8.963%.",
      "The SCL water label covers 19 pixels and was not used as a water measurement.",
      "The Landsat QA_PIXEL file was not downloaded.",
    ],
    source: "data/manifests/mission009_optical_mask_review.json",
    limitations: [
      "The SCL water label is not validation.",
      "Nearby scenes are not same-date ground truth.",
    ],
  },
  {
    id: "geometry-feasibility",
    title: "Mission 010 geometry feasibility",
    mission: "010",
    category: "Terrain",
    date: "2026-11-14",
    status: "Unresolved",
    kind: "gap",
    summary:
      "A shadow model was not run. Filename N expects NOE while the recorded orbit type was MOE.",
    details: [
      "Copernicus GLO-30 is the proposed DEM. NASADEM was not treated as interchangeable.",
      "The GSLC valid-samples mask was excluded from the terrain inputs.",
    ],
    source: "data/manifests/mission010_terrain_geometry.json",
    limitations: [
      "No shadow or layover mask has been created.",
      "No validated terrain-shadow model.",
    ],
  },
  {
    id: "dem-acquisition",
    title: "Mission 011 DEM acquisition",
    mission: "011",
    category: "Terrain",
    date: "2026-11-14",
    status: "Observation",
    kind: "observation",
    summary:
      "Two GLO-30 geocells were stored locally. The buffered elevation crop is 793 x 793 and matches the source values.",
    details: [
      "Stored geocells Copernicus_DSM_COG_10_N29_00_E079_00_DEM and Copernicus_DSM_COG_10_N30_00_E079_00_DEM.",
      "Grids are 3600 x 3600 point samples at 1 arc second. They do not share a boundary posting.",
      "The XML names EGM2008 and also WGS84-G1150. Those statements were not reconciled. No height conversion was applied.",
      "The rasters are gitignored. The manifest holds the checksums.",
    ],
    source: "data/manifests/mission011_terrain_geometry_acquisition.json",
    limitations: [
      "The local DEM tiles are not the ellipsoid-referenced 2023_1 DEM named by the NISAR processor.",
      "No height conversion applied; vertical reference unreconciled.",
    ],
  },
  {
    id: "nisar-access",
    title: "Mission 012 authenticated NISAR metadata",
    mission: "012",
    category: "Metadata",
    date: "2026-09-30",
    status: "Observation",
    kind: "observation",
    summary:
      "Both products were opened by authenticated HTTPS streaming. Neither complete HDF5 file was stored.",
    details: [
      "Both have orbitType MOE, attitudeType Custom, look direction Left, and orbit pass Descending.",
      "shadowMaskingApplied is the string False.",
      "Incidence cubes are 21 x 699 x 710. Cube values were not extracted.",
      "Coordinate steps are 500 m in X, -500 m in Y, and 500 m in height. A step is grid spacing, not a claim of independent resolution.",
      "demSource names Copernicus DEM 30 m release 2023_1, referenced to the WGS84 ellipsoid. That is not the local Mission 011 tile set.",
      "Geometric accuracy bias and standard deviation are NaN.",
    ],
    source: "data/manifests/mission012_nisar_access.json",
    limitations: [
      "No complete HDF5 downloaded.",
      "Cube values not extracted.",
      "Processor DEM is not the local Mission 011 tiles.",
    ],
  },
];

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
