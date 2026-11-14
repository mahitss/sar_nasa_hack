# RIVET

River Incident Verification & Evidence Twin.

RIVET is a repository foundation for an evidence-backed geospatial record of the historical Kuwari landslide-dammed lake in Bageshwar, Uttarakhand, India. The case is a research record. This repository does not operate an emergency response system.

The application is not implemented, not deployed, not validated, and not operational.

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

No application code or dependencies are installed in this mission.

## Scientific limits of the first slice

Mission 000 found comparable provisional NISAR L-band GCOV scenes on descending track 5, frame 73, at 40 MHz and HH+HV (Group D40, CRID P05023). That group is the primary comparison set. The scenes are provisional, not validated. ASF's initial validated release uses a different composite release ID, P05036, and this date window did not contain a second validated scene in the same mode.

The first vertical slice, when later missions implement it, is limited to:

- NISAR L-band GCOV
- Group D40, with provisional CRID P05023 labeled on every record
- one measurement from two acquisitions
- inspection of the GSLC shadow and layover mask
- a water-candidate evidence record
- human review
- one reproducible report

S-band, GUNW, GOFF, deformation claims, breach simulation, and infrastructure exposure are outside that slice.

Granule identifiers copied from Mission 000 are provisional until a later mission rechecks them against NASA CMR. See `docs/science/mission-000-audit.md` and `docs/science/limitations.md`.

## Research sources

- NASA CMR and the ASF DAAC for NISAR L-band catalogue metadata
- ASF NISAR documentation for product definitions, posting, and maturity
- ISRO Bhoonidhi for S-band distribution, which is out of scope until a separate mission
- Ghoke and colleagues, *Discover Geoscience*, 5 September 2026, as prior published research
- NRSC/NDEM 2022 Kunwari note, Bisht and colleagues 2022, and the SANDRP 2024 commentary, as prior context

Links and citation status are in `docs/submission/sources.md`. No science files have been downloaded.

## Provisional maturity

The L-band scenes proposed for the first comparison were processed as provisional products at CRID P05023. Validated L0–L2 products at CRID P05036 begin with acquisitions on 21 October 2026. Mixing those two CRIDs is not an approved comparison. Validated reprocessing of the earlier record is a stated 2027 ASF campaign, not data this repository holds.

## Setup status

| Item | State |
| --- | --- |
| Working directory | `C:\Projects\RIVET` |
| Git | Initialized on `main`. No commit yet. |
| Remote | `origin` = `https://github.com/mahitss/sar_nasa_hack.git` |
| Application code | Not created |
| Dependencies | Not installed |
| Supabase project | Not created |
| Database migrations | Not created |
| Docker services | Not defined and not started |
| Satellite data | Not downloaded. `data/raw`, `data/processed`, and `data/derived` are gitignored |

Local setup for later missions is documented in `.env.example`. That file contains names and placeholders only.

## Layout

```text
apps/web/                 Next.js application (not created yet)
services/api/             Go API (not created yet)
services/worker/          Python worker (not created yet)
data/manifests/           Versioned metadata only
data/raw/                 Gitignored satellite inputs
data/processed/           Gitignored intermediates
data/derived/             Gitignored derived outputs
docs/                     Architecture, science, security, decisions
tests/                    Integration, end-to-end, and scientific tests
```

Engineering rules for agents and reviewers are in `AGENTS.md`.
