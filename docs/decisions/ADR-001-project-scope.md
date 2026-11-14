# ADR-001: Project scope and first vertical slice

- Status: Accepted for the repository foundation by Mission 001
- Date: 2026-11-14
- Supersedes: none

## Context

Mission 000 ended CONDITIONAL GO. The technical architect approved the conditional architecture, subject to the founder accepting the documented scientific scope. Mission 001 instructs the repository to record that scope and to stop at the foundation.

The historical research case is the Kuwari landslide-dammed lake, Uttarakhand, India. It is not framed as an active emergency.

Mission 000 catalogue identifiers are inputs. They were not rechecked while this ADR was written.

## Decision

The first vertical slice is:

1. NISAR L-band GCOV as the measurement source.
2. Group D40 as the primary comparison group: descending track 5, frame 73, Frequency A 40 MHz, HH+HV, provisional CRID P05023.
3. Every record from that group labeled provisional.
4. One measurement that uses two acquisitions from Group D40.
5. Inspection of the companion GSLC mask for water, radar shadow, and layover.
6. A water-candidate evidence record, stored as a measurement, not as a confirmed shoreline.
7. Human review with an accept or reject decision.
8. One report that can be traced to those evidence and decision ids.

Group A40 (ascending track 127) may be stored later as a separate comparability group. It is not differenced against Group D40. Group D20 (20 MHz quad-pol on track 5) is a separate group and is not part of the first measurement.

## Out of scope for the first slice

- S-band products and Bhoonidhi access
- GUNW and any deformation claim
- GOFF and pixel-offset claims
- Breach, outburst, or other hydrological simulation
- Infrastructure exposure scoring
- Field operations
- A national command centre or early-warning service

## Consequences

- Later missions that add a model must store it with claim level `model`.
- A validated-only comparison remains blocked inside the 8 July 2026–14 November 2026 window until a second same-mode P05036 scene is confirmed in CMR.
- Manifest files that list granule ids are not created in this mission, so the provisional ids are not mistaken for a rechecked catalogue.

## Unresolved

- The repository has no licence.
- No commit or push has been approved.
- The founder still needs an Earthdata Login before any download mission.
- The `F_F` token in one Group D20 granule id was not defined from a filename specification in Mission 000.
