-- name: ListAcquisitions :many
SELECT id, incident_id, source_provider, granule_id, acquisition_start, acquisition_end, track, frame, orbit_direction, frequency_mhz, bandwidth_mhz, polarization, crid, product_maturity, source_metadata, created_at
FROM public.acquisitions
WHERE incident_id = $1
ORDER BY created_at ASC;

-- name: GetAcquisition :one
SELECT id, incident_id, source_provider, granule_id, acquisition_start, acquisition_end, track, frame, orbit_direction, frequency_mhz, bandwidth_mhz, polarization, crid, product_maturity, source_metadata, created_at
FROM public.acquisitions
WHERE incident_id = $1 AND id = $2;

-- name: CreateAcquisition :one
INSERT INTO public.acquisitions (
  id, incident_id, source_provider, granule_id, crid, product_maturity
)
VALUES ($1, $2, $3, $4, $5, sqlc.arg('product_maturity')::product_maturity)
RETURNING id, incident_id, source_provider, granule_id, acquisition_start, acquisition_end, track, frame, orbit_direction, frequency_mhz, bandwidth_mhz, polarization, crid, product_maturity, source_metadata, created_at;
