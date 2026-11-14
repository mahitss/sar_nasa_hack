# ADR-001: Project scope and first vertical slice

- Status: Accepted for the repository foundation by Mission 001
- Date: 2026-11-14
- Supersedes: none

## Context

Mission 000 ended CONDITIONAL GO. The technical architect approved the conditional architecture, subject to the founder accepting the documented scientific scope. Mission 001 instructs the repository to record that scope and to stop at the foundation.

The historical research case is the Kuwari landslide-dammed lake, Uttarakhand, India. It is not framed as an active emergency.

The foundation commit is `98a00e6f3d619ee2446f1fabc41a6837dd7ec455` on `main`, and it has been pushed to `origin`.

Mission 000 catalogue identifiers are historical inputs. They are not authoritative by themselves. Mission 002 rechecked the GCOV and GSLC collections against NASA CMR and wrote `data/manifests/nisar_kuwari_catalogue.json`. That manifest still requires architect review before a download, and it is not a raster validation.

## Decision

The first vertical slice is:

1. NISAR L-band GCOV as the measurement source.
2. Group D40 as the primary comparison group: descending track 5, frame 73, Frequency A 40 MHz, HH+HV, provisional CRID P05023.
3. Every record from that group labeled provisional.
4. One measurement that uses two acquisitions from Group D40.
5. GSLC native-grid subswath-validity mask quality control for the companion acquisitions. The selected dataset is `/science/LSAR/GSLC/grids/frequencyA/mask`. The GCOV mask is a separate valid-samples subswath layer. Neither mask is a water, shadow, or layover classification. The first water-candidate measurement must not depend on such a classification from these masks.
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
- A validated-only comparison remains blocked inside the 8 July 2026–14 November 2026 window. Mission 002 found one P05036 scene in the D40 mode, acquired 24 October 2026, and no second scene with the same geometry, bandwidth, polarization, and study-point coverage.
- The Mission 002 manifest lists rechecked granule identifiers. It does not by itself authorize a measurement claim or a bulk download.

## Unresolved

- The rank-1 D40 pair has GCOV raster quality control and GSLC subswath-validity mask quality control. It does not yet have a water-candidate measurement.
- Filename fidelity code `N` and internal `orbitType` `MOE` are an unresolved discrepancy. The Product Format Document, Version 1.2.1, section 2.2.4, defines `N` as Near Real-Time fidelity. The inspected products and CMR both carry `MOE`. The two labels are not treated as equivalent, and no correction is claimed. Orbit direction for grouping comes from `ASCENDING_DESCENDING`.
- The `F_F` token in one Group D20 granule id was not defined from a filename specification in Mission 000.
- The ASF product overview describes a GSLC water and shadow-layover mask. The Product Format Document, Version 1.2.1, and the attributes on the extracted dataset describe a valid-samples subswath mask. That documentation conflict is unresolved.
