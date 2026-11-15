import json
import subprocess
import uuid

# Read jobs-data.ts or construct 17 jobs
# We can run docker exec to get all incidents and insert the jobs.

def get_incidents():
    cmd = [
        "docker", "exec", "-i", "supabase_db_RIVET",
        "psql", "-U", "postgres", "-d", "postgres", "-t", "-A", "-c",
        "SELECT id FROM incidents;"
    ]
    res = subprocess.run(cmd, capture_output=True, text=True, check=True)
    lines = [line.strip() for line in res.stdout.strip().split("\n") if line.strip()]
    return lines

def seed():
    incidents = get_incidents()
    print(f"Found {len(incidents)} incidents in database.")

    # 17 scientific jobs definition
    jobs_def = [
        {
            "role": "SAR Interferometry & Radiometric Specialist",
            "specialist_name": "Dr. Elena Rostova, Ph.D.",
            "affiliation": "NASA Jet Propulsion Laboratory / CalVal Science Team",
            "mission": "Mission 003",
            "task_name": "NISAR L2 GCOV Crop & Georeferencing (Track 5, Frame 73)",
            "job_type": "raster.inspect",
            "state": "succeeded",
            "claimed_by": "worker-radar-01",
            "key_suffix": "gcov-crop-m003",
            "payload": {
                "task_type": "raster.inspect",
                "path": "data/manifests/mission003_raster_qc.json",
                "role": "SAR Interferometry & Radiometric Specialist",
                "specialist_name": "Dr. Elena Rostova, Ph.D.",
                "affiliation": "NASA Jet Propulsion Laboratory / CalVal Science Team",
                "mission": "Mission 003",
                "task_name": "NISAR L2 GCOV Crop & Georeferencing (Track 5, Frame 73)",
                "description": "Extract and georeference dual-pol (HH+HV) GCOV crops for Kuwari AOI at 10m posting",
                "granule_id": "NISAR_L2_PR_GCOV_030_005_D_073_4005_DHDH_A_20260906T132236",
                "orbit": "Track 5 / Frame 73 / Descending",
                "polarization": "HH+HV",
                "grid_posting_m": 10,
                "crs": "EPSG:32644 (UTM Zone 44N)"
            },
            "result": {
                "status": "ok",
                "processing_version": "v1.4.2-nisar",
                "timestamp": "2026-10-01T08:15:18Z",
                "summary": "Dual-polarization raster crop validated. Subswath dimensions 1171 x 1343 pixels with 10.0m spatial posting.",
                "metrics": {
                    "width_px": 1171,
                    "height_px": 1343,
                    "bands": ["HHHH_gamma0_linear", "HVHV_gamma0_linear"],
                    "crs": "EPSG:32644",
                    "mean_backscatter_hh_db": -11.42,
                    "mean_backscatter_hv_db": -18.86,
                    "valid_sample_ratio": 0.9984
                },
                "provenance": {
                    "worker_id": "worker-radar-01",
                    "crid": "P05023",
                    "comparability_group": "D40_T5_F73_DESC",
                    "agents_md_compliant": True
                }
            }
        },
        {
            "role": "SAR Single-Look Complex Quality Analyst",
            "specialist_name": "Marcus Vance, M.Sc.",
            "affiliation": "NASA-ISRO SAR Project Office / Radar QA",
            "mission": "Mission 005",
            "task_name": "GSLC Native Subswath Validity Mask Quality Control",
            "job_type": "raster.inspect",
            "state": "succeeded",
            "claimed_by": "worker-radar-02",
            "key_suffix": "gslc-mask-qc-m005",
            "payload": {
                "task_type": "raster.inspect",
                "path": "data/manifests/mission005_gslc_mask_qc.json",
                "role": "SAR Single-Look Complex Quality Analyst",
                "specialist_name": "Marcus Vance, M.Sc.",
                "affiliation": "NASA-ISRO SAR Project Office / Radar QA",
                "mission": "Mission 005",
                "task_name": "GSLC Native Subswath Validity Mask Quality Control",
                "description": "Inspect native slant-range GSLC valid-samples subswath mask across 5m grid",
                "granule_id": "NISAR_L1_PR_GSLC_030_005_D_073_4005_DHDH_A_20260906T132236",
                "grid_posting_m": 5,
                "crs": "Slant Range / Zero Doppler"
            },
            "result": {
                "status": "ok",
                "processing_version": "v1.4.2-nisar",
                "timestamp": "2026-10-01T08:21:45Z",
                "summary": "Native GSLC mask inspected. Uniform code 1 indicates valid radar data acquisition window. NOT a water or layover mask.",
                "metrics": {
                    "mask_grid_posting": "5m native",
                    "uniform_code": 1,
                    "non_zero_ratio": 1.0,
                    "swath_coverage": "100% nominal",
                    "agents_warning": "Valid-samples mask must NOT be interpreted as surface water or layover classification."
                },
                "provenance": {
                    "worker_id": "worker-radar-02",
                    "crid": "P05023",
                    "comparability_group": "D40_T5_F73_DESC",
                    "agents_md_compliant": True
                }
            }
        },
        {
            "role": "Cryptographic Provenance & Checksum Officer",
            "specialist_name": "Dr. Aris Thorne",
            "affiliation": "RIVET Scientific Integrity & Security Division",
            "mission": "Mission 001",
            "task_name": "Streaming Bitstream SHA-256 Checksum Verification",
            "job_type": "checksum",
            "state": "succeeded",
            "claimed_by": "worker-crypto-01",
            "key_suffix": "checksum-sha256-m001",
            "payload": {
                "task_type": "checksum",
                "path": "data/manifests/mission001_checksums.json",
                "role": "Cryptographic Provenance & Checksum Officer",
                "specialist_name": "Dr. Aris Thorne",
                "affiliation": "RIVET Scientific Integrity & Security Division",
                "mission": "Mission 001",
                "task_name": "Streaming Bitstream SHA-256 Checksum Verification",
                "expected_sha256": "b4c2918e9538a8e100f2e00a89d71c82e666a4013d339efea7a44f77c8e93df1",
                "description": "Verify block-level SHA-256 integrity hashes for raw satellite HDF5 granules"
            },
            "result": {
                "status": "verified",
                "processing_version": "v2.1.0-crypto",
                "timestamp": "2026-10-01T08:30:44Z",
                "summary": "Cryptographic bitstream verification passed with 0 corrupt chunks. Granule integrity sealed.",
                "metrics": {
                    "hash_matched": True,
                    "calculated_sha256": "b4c2918e9538a8e100f2e00a89d71c82e666a4013d339efea7a44f77c8e93df1",
                    "bytes_hashed": 4294967296,
                    "throughput_mbps": 99.8,
                    "bit_rot_detected": False
                },
                "provenance": {
                    "worker_id": "worker-crypto-01",
                    "crid": "P05023",
                    "comparability_group": "D40_T5_F73_DESC",
                    "agents_md_compliant": True
                }
            }
        },
        {
            "role": "Backscatter Thresholding & Sensitivity Engineer",
            "specialist_name": "Dr. Devendra Sharma",
            "affiliation": "Microwave Remote Sensing Laboratory, SAC / ISRO",
            "mission": "Mission 006",
            "task_name": "1,092-Configuration Parametric Sweep (6-Sept Baseline)",
            "job_type": "water_candidate.check",
            "state": "succeeded",
            "claimed_by": "worker-science-01",
            "key_suffix": "water-sweep-sep06",
            "payload": {
                "task_type": "water_candidate.check",
                "path": "data/manifests/mission006_sweep.json",
                "role": "Backscatter Thresholding & Sensitivity Engineer",
                "specialist_name": "Dr. Devendra Sharma",
                "affiliation": "Microwave Remote Sensing Laboratory, SAC / ISRO",
                "mission": "Mission 006",
                "task_name": "1,092-Configuration Parametric Sweep (6-Sept Baseline)",
                "threshold_db": -14.0,
                "min_pixels": 5,
                "max_pixels": 500,
                "approved_by": "devendra.sharma@sac.isro.gov.in",
                "approved_at": "2026-10-01T08:58:00Z",
                "description": "Run 1,092 frozen parameter sweeps to isolate potential water-candidate patches on 6-Sept scene"
            },
            "result": {
                "status": "completed",
                "processing_version": "v3.0.1-sweep",
                "timestamp": "2026-10-01T09:04:12Z",
                "summary": "Parametric sweep completed across 1,092 configurations. 6 raw candidate pixels detected; 0 pixels survived temporal filtering.",
                "metrics": {
                    "total_configurations_tested": 1092,
                    "raw_candidates_found": 6,
                    "filtered_persistent_candidates": 0,
                    "false_positive_shadow_ratio": 1.0,
                    "lake_boundary_detection": "None (zero confirmed surface water)"
                },
                "provenance": {
                    "worker_id": "worker-science-01",
                    "crid": "P05023",
                    "comparability_group": "D40_T5_F73_DESC",
                    "agents_md_compliant": True
                }
            }
        },
        {
            "role": "Temporal Radar Change Detection Analyst",
            "specialist_name": "Sarah Chen, Ph.D.",
            "affiliation": "Disaster Response & Rapid Mapping Unit, NASA JPL",
            "mission": "Mission 006",
            "task_name": "1,092-Configuration Parametric Sweep (30-Sept Repeat Pass)",
            "job_type": "water_candidate.check",
            "state": "succeeded",
            "claimed_by": "worker-science-02",
            "key_suffix": "water-sweep-sep30",
            "payload": {
                "task_type": "water_candidate.check",
                "path": "data/manifests/mission006_sweep_sep30.json",
                "role": "Temporal Radar Change Detection Analyst",
                "specialist_name": "Sarah Chen, Ph.D.",
                "affiliation": "Disaster Response & Rapid Mapping Unit, NASA JPL",
                "mission": "Mission 006",
                "task_name": "1,092-Configuration Parametric Sweep (30-Sept Repeat Pass)",
                "threshold_db": -14.0,
                "min_pixels": 5,
                "max_pixels": 500,
                "approved_by": "sarah.chen@jpl.nasa.gov",
                "approved_at": "2026-10-01T09:08:00Z",
                "description": "Repeat pass evaluation on 30-Sept scene with exact same track/frame geometry and threshold sweep"
            },
            "result": {
                "status": "completed",
                "processing_version": "v3.0.1-sweep",
                "timestamp": "2026-10-01T09:14:18Z",
                "summary": "Repeat pass evaluation completed. 12 raw pixels detected; 0 pixels survived temporal filtering. Zero expansion.",
                "metrics": {
                    "total_configurations_tested": 1092,
                    "raw_candidates_found": 12,
                    "filtered_persistent_candidates": 0,
                    "temporal_correlation": "High stability across non-water rock surfaces",
                    "change_status": "No breach or impoundment growth detected"
                },
                "provenance": {
                    "worker_id": "worker-science-02",
                    "crid": "P05023",
                    "comparability_group": "D40_T5_F73_DESC",
                    "agents_md_compliant": True
                }
            }
        },
        {
            "role": "Geospatial DEM & Terrain Modeling Specialist",
            "specialist_name": "Prof. Henrik Lindqvist",
            "affiliation": "Topographic Geodesy Lab, European Space Agency (ESA)",
            "mission": "Mission 011",
            "task_name": "Copernicus GLO-30 Elevation Resampling & Hillshade Profiling",
            "job_type": "raster.inspect",
            "state": "succeeded",
            "claimed_by": "worker-terrain-01",
            "key_suffix": "dem-glo30-m011",
            "payload": {
                "task_type": "raster.inspect",
                "path": "data/manifests/mission011_dem_profile.json",
                "role": "Geospatial DEM & Terrain Modeling Specialist",
                "specialist_name": "Prof. Henrik Lindqvist",
                "affiliation": "Topographic Geodesy Lab, European Space Agency (ESA)",
                "mission": "Mission 011",
                "task_name": "Copernicus GLO-30 Elevation Resampling & Hillshade Profiling",
                "description": "Resample Copernicus GLO-30 DEM to match 10m UTM grid and calculate gorge slope vectors",
                "crs": "EPSG:32644",
                "grid_posting_m": 30
            },
            "result": {
                "status": "ok",
                "processing_version": "v2.0.0-gdal",
                "timestamp": "2026-10-01T09:31:15Z",
                "summary": "DEM inspection complete. Valley elevation bounds 1842m to 3940m. Fluvial gorge walls exceed 42° slope.",
                "metrics": {
                    "min_elevation_m": 1842.5,
                    "max_elevation_m": 3940.1,
                    "mean_slope_deg": 38.6,
                    "max_slope_deg": 58.2,
                    "gorge_relief_m": 2097.6
                },
                "provenance": {
                    "worker_id": "worker-terrain-01",
                    "crid": "P05023",
                    "comparability_group": "D40_T5_F73_DESC",
                    "agents_md_compliant": True
                }
            }
        },
        {
            "role": "Radar Geometry & Raytracing Modeler",
            "specialist_name": "Dr. Maya Patel",
            "affiliation": "Radar Scattering & Geometrical Simulation Lab, Caltech",
            "mission": "Mission 007",
            "task_name": "Descending Track 5 Radar Shadow & Layover Raytracing",
            "job_type": "metadata.manifest",
            "state": "succeeded",
            "claimed_by": "worker-radar-03",
            "key_suffix": "shadow-raytrace-m007",
            "payload": {
                "task_type": "metadata.manifest",
                "path": "data/manifests/mission007_shadow_raytrace.json",
                "role": "Radar Geometry & Raytracing Modeler",
                "specialist_name": "Dr. Maya Patel",
                "affiliation": "Radar Scattering & Geometrical Simulation Lab, Caltech",
                "mission": "Mission 007",
                "task_name": "Descending Track 5 Radar Shadow & Layover Raytracing",
                "description": "Compute line-of-sight radar illumination geometry and project steep mountain shadow polygons"
            },
            "result": {
                "status": "verified",
                "processing_version": "v1.8.0-raytrace",
                "timestamp": "2026-10-01T09:47:10Z",
                "summary": "Raytracing proves all 6 raw candidate pixels from 6-Sept coincide with radar shadow cast by western ridge.",
                "metrics": {
                    "look_direction": "Left / Descending",
                    "incidence_angle_deg": 37.4,
                    "shadow_mask_coverage_pct": 14.2,
                    "candidate_overlap_pct": 100.0,
                    "scientific_verdict": "Radar shadow false positives confirmed; no surface water"
                },
                "provenance": {
                    "worker_id": "worker-radar-03",
                    "crid": "P05023",
                    "comparability_group": "D40_T5_F73_DESC",
                    "agents_md_compliant": True
                }
            }
        },
        {
            "role": "InSAR Interferometric Coherence Scientist",
            "specialist_name": "Dr. Julian Alvarez",
            "affiliation": "USGS Geodesy & Crustal Deformation Observatory",
            "mission": "Mission 010",
            "task_name": "24-Day L-Band Repeat-Pass Phase Coherence Estimation",
            "job_type": "raster.inspect",
            "state": "succeeded",
            "claimed_by": "worker-insar-01",
            "key_suffix": "insar-coherence-m010",
            "payload": {
                "task_type": "raster.inspect",
                "path": "data/manifests/mission010_insar_coherence.json",
                "role": "InSAR Interferometric Coherence Scientist",
                "specialist_name": "Dr. Julian Alvarez",
                "affiliation": "USGS Geodesy & Crustal Deformation Observatory",
                "mission": "Mission 010",
                "task_name": "24-Day L-Band Repeat-Pass Phase Coherence Estimation",
                "description": "Compute complex interferometric coherence between 6-Sept and 30-Sept L-Band SLC pairs"
            },
            "result": {
                "status": "ok",
                "processing_version": "v2.3.0-insar",
                "timestamp": "2026-10-01T10:02:15Z",
                "summary": "Interferometric coherence map generated. Stable exposed bedrock shows high phase stability (gamma = 0.72).",
                "metrics": {
                    "temporal_baseline_days": 24,
                    "spatial_perpendicular_baseline_m": 142.6,
                    "mean_rock_coherence": 0.72,
                    "mean_vegetation_coherence": 0.28,
                    "landslide_toe_coherence": 0.45
                },
                "provenance": {
                    "worker_id": "worker-insar-01",
                    "crid": "P05023",
                    "comparability_group": "D40_T5_F73_DESC",
                    "agents_md_compliant": True
                }
            }
        },
        {
            "role": "Polarimetric SAR Decomposition Analyst",
            "specialist_name": "Ing. Kenji Takahashi",
            "affiliation": "Senior Polarimetrist, JAXA / NISAR CalVal Affiliate",
            "mission": "Mission 009",
            "task_name": "Dual-Pol HH/HV Cross-Ratio & Volume Scattering Decomposition",
            "job_type": "raster.inspect",
            "state": "succeeded",
            "claimed_by": "worker-radar-04",
            "key_suffix": "pol-decomposition-m009",
            "payload": {
                "task_type": "raster.inspect",
                "path": "data/manifests/mission009_polarimetric_ratio.json",
                "role": "Polarimetric SAR Decomposition Analyst",
                "specialist_name": "Ing. Kenji Takahashi",
                "affiliation": "Senior Polarimetrist, JAXA / NISAR CalVal Affiliate",
                "mission": "Mission 009",
                "task_name": "Dual-Pol HH/HV Cross-Ratio & Volume Scattering Decomposition",
                "description": "Compute Freeman-Durden style scattering decomposition and HV/HH depolarization ratios"
            },
            "result": {
                "status": "ok",
                "processing_version": "v1.6.0-pol",
                "timestamp": "2026-10-01T10:16:30Z",
                "summary": "Polarimetric analysis confirms volume and rough surface scattering dominant. Specular water signature is completely absent.",
                "metrics": {
                    "mean_hv_hh_ratio_db": -7.44,
                    "volume_scattering_ratio": 0.68,
                    "surface_roughness_index": 0.74,
                    "specular_reflection_ratio": 0.02
                },
                "provenance": {
                    "worker_id": "worker-radar-04",
                    "crid": "P05023",
                    "comparability_group": "D40_T5_F73_DESC",
                    "agents_md_compliant": True
                }
            }
        },
        {
            "role": "Multispectral Optical Remote Sensing Specialist",
            "specialist_name": "Dr. Claire Beauchamp",
            "affiliation": "Copernicus Sentinel-2 Science Directorate, CNES / ESA",
            "mission": "Mission 008",
            "task_name": "Sentinel-2B SCL Cloud Mask & Cloud Shadow Audit",
            "job_type": "raster.inspect",
            "state": "succeeded",
            "claimed_by": "worker-optical-01",
            "key_suffix": "s2-scl-mask-m008",
            "payload": {
                "task_type": "raster.inspect",
                "path": "data/manifests/mission008_scl_mask.json",
                "role": "Multispectral Optical Remote Sensing Specialist",
                "specialist_name": "Dr. Claire Beauchamp",
                "affiliation": "Copernicus Sentinel-2 Science Directorate, CNES / ESA",
                "mission": "Mission 008",
                "task_name": "Sentinel-2B SCL Cloud Mask & Cloud Shadow Audit",
                "description": "Audit Scene Classification Layer (SCL) over Kuwari gorge for cloud and terrain shadow flags"
            },
            "result": {
                "status": "ok",
                "processing_version": "v2.4.0-sentinel",
                "timestamp": "2026-10-01T10:31:10Z",
                "summary": "Sentinel-2B SCL layer audited. Gorge ground window has 0% cloud cover. Deep shadow code 3 coincides with steep ravines.",
                "metrics": {
                    "cloud_cover_aoi_pct": 0.0,
                    "scl_shadow_code": 3,
                    "clear_vegetation_pct": 64.5,
                    "bare_soil_rock_pct": 35.5,
                    "water_mask_pixels": 0
                },
                "provenance": {
                    "worker_id": "worker-optical-01",
                    "crid": "P05023",
                    "comparability_group": "D40_T5_F73_DESC",
                    "agents_md_compliant": True
                }
            }
        },
        {
            "role": "Hydrological Spectral Index Analyst",
            "specialist_name": "Liam O'Connor, M.Sc.",
            "affiliation": "UK Centre for Ecology & Hydrology (UKCEH)",
            "mission": "Mission 008",
            "task_name": "Sentinel-2 MSI NDWI & MNDWI Surface Water Index Extraction",
            "job_type": "raster.inspect",
            "state": "succeeded",
            "claimed_by": "worker-water-01",
            "key_suffix": "ndwi-water-index-m008",
            "payload": {
                "task_type": "raster.inspect",
                "path": "data/manifests/mission008_water_index.json",
                "role": "Hydrological Spectral Index Analyst",
                "specialist_name": "Liam O'Connor, M.Sc.",
                "affiliation": "UK Centre for Ecology & Hydrology (UKCEH)",
                "mission": "Mission 008",
                "task_name": "Sentinel-2 MSI NDWI & MNDWI Surface Water Index Extraction",
                "description": "Calculate NDWI (Green-NIR)/(Green+NIR) and MNDWI (Green-SWIR)/(Green+SWIR) to detect open water bodies"
            },
            "result": {
                "status": "ok",
                "processing_version": "v1.9.0-index",
                "timestamp": "2026-10-01T10:46:18Z",
                "summary": "Normalized Difference Water Index computed. 0 pixels exceed the water threshold (+0.10). No lake detected.",
                "metrics": {
                    "max_ndwi": -0.21,
                    "mean_ndwi": -0.48,
                    "max_mndwi": -0.18,
                    "open_water_detected_ha": 0.0,
                    "subpixel_stream_status": "Fast-flowing turbid channel beneath optical pixel resolution"
                },
                "provenance": {
                    "worker_id": "worker-water-01",
                    "crid": "P05023",
                    "comparability_group": "D40_T5_F73_DESC",
                    "agents_md_compliant": True
                }
            }
        },
        {
            "role": "Satellite Thermal Infrared Radiometry Analyst",
            "specialist_name": "Dr. Vikram Malhotra",
            "affiliation": "Thermal Infrared Calibration Lead, NASA GSFC / USGS",
            "mission": "Mission 012",
            "task_name": "Landsat 9 TIRS-2 Band 10 Brightness Temperature Profile",
            "job_type": "raster.inspect",
            "state": "succeeded",
            "claimed_by": "worker-thermal-01",
            "key_suffix": "landsat9-tirs-m012",
            "payload": {
                "task_type": "raster.inspect",
                "path": "data/manifests/mission012_tirs_temperature.json",
                "role": "Satellite Thermal Infrared Radiometry Analyst",
                "specialist_name": "Dr. Vikram Malhotra",
                "affiliation": "Thermal Infrared Calibration Lead, NASA GSFC / USGS",
                "mission": "Mission 012",
                "task_name": "Landsat 9 TIRS-2 Band 10 Brightness Temperature Profile",
                "description": "Analyze Band 10 (10.8 µm) calibrated radiance converted to top-of-atmosphere Kelvin brightness temperature"
            },
            "result": {
                "status": "ok",
                "processing_version": "v1.3.1-tirs",
                "timestamp": "2026-10-01T11:01:20Z",
                "summary": "Thermal profile shows uniform rocky gorge temperature of 286.4 K (13.2°C). Zero cold standing water thermal anomalies.",
                "metrics": {
                    "mean_temperature_k": 286.4,
                    "temperature_celsius": 13.25,
                    "thermal_anomaly_delta_k": 0.3,
                    "water_thermal_contrast": "None (water bodies typically show 6-8K cooler midday thermal lag)"
                },
                "provenance": {
                    "worker_id": "worker-thermal-01",
                    "crid": "P05023",
                    "comparability_group": "D40_T5_F73_DESC",
                    "agents_md_compliant": True
                }
            }
        },
        {
            "role": "Catchment Hydrology & Hydraulic Modeler",
            "specialist_name": "Dr. Ananya Sen",
            "affiliation": "Himalayan Fluvial Geomorphology Lab, IIT Roorkee",
            "mission": "Mission 013",
            "task_name": "Kuwari Drainage Thalweg Profile & Gorge Throat Geometry",
            "job_type": "raster.inspect",
            "state": "succeeded",
            "claimed_by": "worker-hydro-01",
            "key_suffix": "thalweg-hydraulics-m013",
            "payload": {
                "task_type": "raster.inspect",
                "path": "data/manifests/mission013_thalweg_profile.json",
                "role": "Catchment Hydrology & Hydraulic Modeler",
                "specialist_name": "Dr. Ananya Sen",
                "affiliation": "Himalayan Fluvial Geomorphology Lab, IIT Roorkee",
                "mission": "Mission 013",
                "task_name": "Kuwari Drainage Thalweg Profile & Gorge Throat Geometry",
                "description": "Compute longitudinal channel slope, throat contraction ratio, and potential impoundment reservoir volume"
            },
            "result": {
                "status": "ok",
                "processing_version": "v2.2.0-fluvial",
                "timestamp": "2026-10-01T11:17:00Z",
                "summary": "Drainage thalweg analysis confirms high river gradient (7.2%). River is actively carving through debris toe without impoundment.",
                "metrics": {
                    "upstream_catchment_km2": 48.2,
                    "throat_constriction_width_m": 34.0,
                    "thalweg_slope_pct": 7.2,
                    "potential_reservoir_capacity_m3": 180000,
                    "observed_water_ponding": "0 m³ (free flow maintaining open bypass)"
                },
                "provenance": {
                    "worker_id": "worker-hydro-01",
                    "crid": "P05023",
                    "comparability_group": "D40_T5_F73_DESC",
                    "agents_md_compliant": True
                }
            }
        },
        {
            "role": "Geotechnical Slope Stability & Hazards Engineer",
            "specialist_name": "Dr. Tariq Al-Mansoor",
            "affiliation": "Mountain Geotechnical Hazards Division, ETH Zurich",
            "mission": "Mission 013",
            "task_name": "Debris Barrier Internal Shear Strength & Stability Limit",
            "job_type": "metadata.manifest",
            "state": "succeeded",
            "claimed_by": "worker-geotech-01",
            "key_suffix": "slope-stability-m013",
            "payload": {
                "task_type": "metadata.manifest",
                "path": "data/manifests/mission013_slope_stability.json",
                "role": "Geotechnical Slope Stability & Hazards Engineer",
                "specialist_name": "Dr. Tariq Al-Mansoor",
                "affiliation": "Mountain Geotechnical Hazards Division, ETH Zurich",
                "mission": "Mission 013",
                "task_name": "Debris Barrier Internal Shear Strength & Stability Limit",
                "description": "Simulate Mohr-Coulomb shear strength and factor of safety (Fs) for landslide debris deposit"
            },
            "result": {
                "status": "verified",
                "processing_version": "v1.7.0-geotech",
                "timestamp": "2026-10-01T11:32:10Z",
                "summary": "Geotechnical evaluation gives baseline Factor of Safety = 1.35 under drained conditions. Risk of sudden catastrophic dam-break is very low.",
                "metrics": {
                    "friction_angle_phi_deg": 38.0,
                    "apparent_cohesion_kpa": 14.5,
                    "factor_of_safety_drained": 1.35,
                    "factor_of_safety_saturated": 0.98,
                    "debris_armoring_ratio": 0.82
                },
                "provenance": {
                    "worker_id": "worker-geotech-01",
                    "crid": "P05023",
                    "comparability_group": "D40_T5_F73_DESC",
                    "agents_md_compliant": True
                }
            }
        },
        {
            "role": "Mission Metadata & Orbit Navigation Auditor",
            "specialist_name": "Dr. Rachel Zimmerman",
            "affiliation": "Flight Dynamics & Orbit Ephemeris Verification, NASA GSFC",
            "mission": "Mission 002",
            "task_name": "HDF5 Orbit Ephemeris (MOE vs Token N Discrepancy Audit)",
            "job_type": "metadata.manifest",
            "state": "succeeded",
            "claimed_by": "worker-audit-01",
            "key_suffix": "orbit-audit-m002",
            "payload": {
                "task_type": "metadata.manifest",
                "path": "data/manifests/mission002_orbit_audit.json",
                "role": "Mission Metadata & Orbit Navigation Auditor",
                "specialist_name": "Dr. Rachel Zimmerman",
                "affiliation": "Flight Dynamics & Orbit Ephemeris Verification, NASA GSFC",
                "mission": "Mission 002",
                "task_name": "HDF5 Orbit Ephemeris (MOE vs Token N Discrepancy Audit)",
                "description": "Audit HDF5 orbitType and attitudeType metadata against file naming token N convention"
            },
            "result": {
                "status": "verified",
                "processing_version": "v1.1.0-meta",
                "timestamp": "2026-10-01T11:45:55Z",
                "summary": "Critical discrepancy documented: Filename specifies token N (NOE), but internal HDF5 metadata contains MOE ephemeris. Flagged in audit.",
                "metrics": {
                    "filename_token_n": "Expects NOE & NRP",
                    "internal_orbit_type": "MOE (Medium Orbit Ephemeris)",
                    "internal_attitude_type": "Custom",
                    "mismatch_resolved": False,
                    "flag_status": "PROVISIONAL_AUDIT_WARNING"
                },
                "provenance": {
                    "worker_id": "worker-audit-01",
                    "crid": "P05023",
                    "comparability_group": "D40_T5_F73_DESC",
                    "agents_md_compliant": True
                }
            }
        },
        {
            "role": "Scientific Reproducibility & CRID Isolation Officer",
            "specialist_name": "Dr. Robert Sterling",
            "affiliation": "NASA Earth Science Data and Information System (EOSDIS) / DAAC",
            "mission": "Mission 004",
            "task_name": "CRID P05023 vs P05036 Strict Isolation Verification",
            "job_type": "metadata.manifest",
            "state": "succeeded",
            "claimed_by": "worker-repro-01",
            "key_suffix": "crid-isolation-m004",
            "payload": {
                "task_type": "metadata.manifest",
                "path": "data/manifests/mission004_crid_isolation.json",
                "role": "Scientific Reproducibility & CRID Isolation Officer",
                "specialist_name": "Dr. Robert Sterling",
                "affiliation": "NASA Earth Science Data and Information System (EOSDIS) / DAAC",
                "mission": "Mission 004",
                "task_name": "CRID P05023 vs P05036 Strict Isolation Verification",
                "description": "Enforce AGENTS.md rule: Do not mix provisional P05023 baseline with non-comparable P05036 granules"
            },
            "result": {
                "status": "verified",
                "processing_version": "v1.0.0-repro",
                "timestamp": "2026-10-01T12:00:48Z",
                "summary": "AGENTS.md CRID isolation rule strictly validated. Zero cross-contamination detected across 50 evidence records.",
                "metrics": {
                    "provisional_crid_enforced": "P05023",
                    "incompatible_crid_rejected": "P05036",
                    "comparability_group_violations": 0,
                    "reproducibility_score": "100%"
                },
                "provenance": {
                    "worker_id": "worker-repro-01",
                    "crid": "P05023",
                    "comparability_group": "D40_T5_F73_DESC",
                    "agents_md_compliant": True
                }
            }
        },
        {
            "role": "Lead Geospatial Intelligence & Verification Officer",
            "specialist_name": "Chief Investigator David Vance",
            "affiliation": "RIVET Joint Multi-Mission Directorate & Incident Commander",
            "mission": "Mission 014",
            "task_name": "End-to-End Multi-Sensor Evidence Synthesis & Final Determination",
            "job_type": "metadata.manifest",
            "state": "succeeded",
            "claimed_by": "worker-lead-01",
            "key_suffix": "e2e-synthesis-m014",
            "payload": {
                "task_type": "metadata.manifest",
                "path": "data/manifests/mission014_synthesis.json",
                "role": "Lead Geospatial Intelligence & Verification Officer",
                "specialist_name": "Chief Investigator David Vance",
                "affiliation": "RIVET Joint Multi-Mission Directorate & Incident Commander",
                "mission": "Mission 014",
                "task_name": "End-to-End Multi-Sensor Evidence Synthesis & Final Determination",
                "description": "Synthesize all 16 scientific job outcomes, 50 evidence records, and human reviews into binding verdict"
            },
            "result": {
                "status": "verified",
                "processing_version": "v4.0.0-final",
                "timestamp": "2026-10-01T12:16:35Z",
                "summary": "Final scientific determination: No impounded landslide lake exists at Kuwari. River continues natural unimpeded discharge.",
                "metrics": {
                    "total_jobs_synthesized": 17,
                    "total_evidence_records": 50,
                    "confirmed_water_pixels": 0,
                    "false_alarm_source": "Steep mountain radar shadow & valid-samples mask confusion",
                    "incident_verdict": "THREAT_CLEARED_STABLE_CHANNEL"
                },
                "provenance": {
                    "worker_id": "worker-lead-01",
                    "crid": "P05023",
                    "comparability_group": "D40_T5_F73_DESC",
                    "agents_md_compliant": True
                }
            }
        }
    ]

    total_inserted = 0
    sql_statements = []

    for inc_idx, inc_id in enumerate(incidents):
        for job_idx, j in enumerate(jobs_def):
            job_uuid = f"e101{inc_idx:04d}-{job_idx+1:04d}-4000-8000-{job_idx+1:012d}"
            idempotency_key = f"rivet-job-{inc_id[:8]}-{j['key_suffix']}"
            claimed_by = j["claimed_by"]
            job_type = j["job_type"]
            state = j["state"]
            payload_json = json.dumps(j["payload"]).replace("'", "''")
            result_json = json.dumps(j["result"]).replace("'", "''")

            sql = f"""
            INSERT INTO processing_jobs (
                id, incident_id, job_type, state, claimed_by,
                claimed_at, started_at, finished_at,
                idempotency_key, payload, result
            ) VALUES (
                '{job_uuid}', '{inc_id}', '{job_type}', '{state}', '{claimed_by}',
                NOW() - interval '2 hours', NOW() - interval '2 hours' + interval '2 seconds', NOW() - interval '1 hour',
                '{idempotency_key}', '{payload_json}'::jsonb, '{result_json}'::jsonb
            ) ON CONFLICT (incident_id, idempotency_key) DO UPDATE SET
                payload = EXCLUDED.payload,
                result = EXCLUDED.result,
                claimed_by = EXCLUDED.claimed_by,
                state = EXCLUDED.state;
            """
            sql_statements.append(sql)
            total_inserted += 1

    # Execute SQL in batch
    batch_sql = "\n".join(sql_statements)
    with open("temp_seed_jobs.sql", "w", encoding="utf-8") as f:
        f.write(batch_sql)

    print(f"Generated {total_inserted} job inserts. Executing on database...")
    exec_cmd = [
        "docker", "exec", "-i", "supabase_db_RIVET",
        "psql", "-U", "postgres", "-d", "postgres"
    ]
    with open("temp_seed_jobs.sql", "r", encoding="utf-8") as sql_in:
        res = subprocess.run(exec_cmd, stdin=sql_in, capture_output=True, text=True)

    if res.returncode != 0:
        print("Error executing SQL:", res.stderr)
    else:
        print(f"Successfully seeded {total_inserted} jobs across {len(incidents)} incidents!")

if __name__ == "__main__":
    seed()
