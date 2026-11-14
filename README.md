# RIVET

River Incident Verification & Evidence Twin.

RIVET is a repository foundation for an evidence-backed geospatial record of the historical Kuwari landslide-dammed lake in Bageshwar, Uttarakhand, India. The case is a research record. This repository does not operate an emergency response system.

A Next.js investigation prototype is implemented in `apps/web` (five routes: `/`, `/spatial`, `/acquisitions`, `/evidence`, `/report`). It is not production-deployed and is not scientifically validated. The Go API, Python worker, and Supabase are not implemented.

## Problem

Published work already reconstructed the Kuwari landslide from 2013 to 2025 with optical imagery, Sentinel-1 SBAS, field observation, and a HEC-RAS breach scenario. Those results are prior research. They are not RIVET measurements.

The question RIVET is being built to answer is:

> When new observations become available, what has changed, what evidence supports that conclusion, how reliable is it, what remains uncertain, and what should be verified next?

The first observations under consideration are NASA NISAR L-band products over the discovery box west 79.75, south 30.03, east 79.87, north 30.15, for 8 July 2026 through 14 November 2026.

## Product concept

RIVET connects a catalogue identifier, a comparability rule, a measurement, an uncertainty statement, and a human review decision. A map without that chain is outside the product.

Claim levels used throughout the project:

- **Observation.** What the source data records.
- **Measurement.** A reproducible calculation from source data, with provenance.
- **Interpretation.** A reviewed explanation supported by measurements.
- **Hypothesis.** A possible explanation that still needs verification.
- **Model.** A conditional simulation. A model is never stored as an observation.

## Technology

| Concern | Owner |
| --- | --- |
| Interface, maps, review workflow | Next.js 16, React 19, TypeScript, Tailwind CSS v4, shadcn/ui, MapLibre GL JS, Supabase SSR |
| Records, authorization, jobs, review, reports | Go 1.25 module target, Chi, pgx, sqlc, golang-migrate, OpenAPI |
| Raster measurement and scientific artifacts | Python 3.12.13, GDAL, Rasterio, GeoPandas, Shapely, PyProj, NumPy, SciPy, Xarray, rioxarray |
| Identity, PostgreSQL, PostGIS, file storage | Supabase Auth, Supabase PostgreSQL, Supabase Storage |

Go owns business logic. Python owns scientific processing. Next.js owns the interface. FastAPI, Kafka, and Kubernetes are not part of this architecture. Supabase is the only database. Docker Compose does not run a second PostgreSQL.

The Go API and scientific worker are not implemented. The Next.js web application is implemented in `apps/web` and uses Next.js 16, React 19, TypeScript, Tailwind CSS v4, and MapLibre GL JS. Supabase is not implemented. `tools/catalogue_audit.py` is a standard-library catalogue audit, not the processing pipeline.

## Scientific limits of the first slice

Group D40 is the primary comparison set: provisional NISAR L-band GCOV, descending track 5, frame 73, Frequency A 40 MHz, HH+HV, CRID P05023. A fresh CMR query on 2026-11-14 confirmed four acquisitions whose footprints contain the published study coordinate: 20 July, 13 August, 6 September, and 30 September 2026. The same query found only one validated P05036 scene in that mode, on 24 October 2026, so there is no validated pair in this window. The catalogue shortlist for the first pair is 6 September and 30 September. Mission 003 recorded GCOV raster quality control and GSLC native-grid subswath-validity mask quality control for that pair. Those records are not a water measurement.

The first vertical slice, when later missions implement it, is limited to:

- NISAR L-band GCOV
- Group D40, with provisional CRID P05023 labeled on every record
- one measurement from two acquisitions
- GSLC native-grid subswath-validity mask quality control, kept distinct from the GCOV valid-samples subswath mask
- a water-candidate evidence record
- human review
- one reproducible report

S-band, GUNW, GOFF, deformation claims, breach simulation, and infrastructure exposure are outside that slice.

The revalidated catalogue record is `data/manifests/nisar_kuwari_catalogue.json`. It is metadata, not a processed result. Mission 000 identifiers remain a historical record in `docs/science/mission-000-audit.md`. Limits are in `docs/science/limitations.md`.

## Research sources

- NASA CMR and the ASF DAAC for NISAR L-band catalogue metadata
- ASF NISAR documentation for product definitions, posting, and maturity
- ISRO Bhoonidhi for S-band distribution, which is out of scope until a separate mission
- Ghoke and colleagues, *Discover Geoscience*, 5 September 2026, as prior published research
- NRSC/NDEM 2022 Kunwari note, Bisht and colleagues 2022, and the SANDRP 2024 commentary, as prior context

Links and citation status are in `docs/submission/sources.md`. Mission 011 downloaded two Copernicus GLO-30 DEM geocells and generated a buffered elevation crop locally; those files are gitignored, while their checksums and processing records are committed in `data/manifests/mission011_terrain_geometry_acquisition.json`. No complete NISAR HDF5 product was downloaded or stored; Mission 012 performed authenticated partial HTTPS metadata reads only.

## Provisional maturity

The L-band scenes proposed for the first comparison were processed as provisional products at CRID P05023. Validated L0–L2 products at CRID P05036 begin with acquisitions on 21 October 2026. Mixing those two CRIDs is not an approved comparison. Validated reprocessing of the earlier record is a stated 2027 ASF campaign, not data this repository holds.

## Setup status

| Item | State |
| --- | --- |
| Working directory | `C:\Projects\RIVET` |
| Git | Foundation commit `98a00e6f3d619ee2446f1fabc41a6837dd7ec455` on `main`, published to `origin/main`. |
| Remote | `origin` = `https://github.com/mahitss/sar_nasa_hack.git` |
| Application code | Implemented in `apps/web` (five routes) |
| Dependencies | Locked in `apps/web/package-lock.json`; install with `npm ci` |
| Supabase project | Not created |
| Database migrations | Not created |
| Docker services | Not defined and not started |
| Satellite data | Mission 011 stored two Copernicus GLO-30 DEM geocells and a derived crop locally (gitignored); checksums/records committed. Those local tiles are not the ellipsoid-referenced 2023_1 DEM named by the NISAR processor. No complete NISAR HDF5 product was downloaded or stored; Mission 012 performed partial HTTPS metadata reads only. `data/raw`, `data/processed`, and `data/derived` are gitignored. The CMR manifest is versioned metadata only. |

Local setup for later missions is documented in `.env.example`. That file contains names and placeholders only.

## Layout

```text
apps/web/                 Next.js application (implemented; not deployed)
services/api/             Go API (not created yet)
services/worker/          Python worker (not created yet)
data/manifests/           Versioned catalogue metadata
tools/catalogue_audit.py  Standard-library CMR revalidation script
data/raw/                 Gitignored satellite inputs
data/processed/           Gitignored intermediates
data/derived/             Gitignored derived outputs
docs/                     Architecture, science, security, decisions
tests/                    Integration, end-to-end, and scientific tests
```

Engineering rules for agents and reviewers are in `AGENTS.md`.
