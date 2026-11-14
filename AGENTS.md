# Engineering rules

These rules apply to every mission. A later task does not weaken them.

## Evidence

- State a claim only after naming the evidence for it.
- Do not fabricate observations, granule identifiers, measurements, citations, or test results.
- Do not fabricate accuracy, confidence, or validation metrics.
- Do not present a simulation or a model as an observation.
- Label unverified assumptions as unverified.
- Keep Mission 000 catalogue extracts provisional until they are rechecked against NASA CMR. Do not promote them by copying them into a manifest without that recheck.

## Provenance

- Every measurement stores its source granule identifiers, composite release ID (CRID), processing version, code version, and parameters.
- Every comparison names its comparability group.
- A comparability group matches track, frame, orbit direction, frequency bandwidth, polarization, and CRID.
- Do not mix CRIDs.
- Do not mix incompatible acquisition modes, including 20 MHz quad-pol with 40 MHz dual-pol.
- Do not difference ascending and descending scenes and call the result one change measurement.

## Secrets and data

- Do not commit secrets, tokens, `.env` files, or real credentials.
- `.env.example` may contain variable names and placeholders only.
- Do not commit `data/raw/`, `data/processed/`, `data/derived/`, or satellite products (`*.h5`, `*.hdf5`, `*.tif`, `*.tiff`, and the other patterns in `.gitignore`).
- `data/manifests/` is the only data directory that belongs in Git, and only for small metadata and reproducibility records.
- The Next.js app must not receive the Supabase service-role key or a database password.

## Ownership

- Go owns business logic, authentication verification, authorization, incidents, evidence records, job orchestration, decisions, reports, and audit history.
- Python owns satellite processing, raster analysis, geospatial transforms, measurements, and scientific artifacts.
- Next.js owns the interface, maps, and review workflow.
- Supabase owns Auth, PostgreSQL, PostGIS, and authorized storage.
- Do not add FastAPI as a second business API.
- Do not add Kafka, Kubernetes, or extra services that the approved architecture does not name.
- Do not add a second PostgreSQL database. Docker Compose is not a database host.

## Scope and missions

- Implement the approved mission only. Do not expand into adjacent features.
- The first vertical slice is Group D40 provisional GCOV, one two-acquisition water-candidate measurement, GSLC native-grid subswath-validity mask quality control, human review, and one report. The water-candidate measurement must not treat the GSLC mask as a water, shadow, or layover classification.
- S-band, GUNW, GOFF, deformation, breach simulation, and infrastructure exposure stay out of that slice.
- Every mission states acceptance criteria before implementation and reports test or inspection evidence afterward.
- Do not commit or push unless the founder explicitly asks.
