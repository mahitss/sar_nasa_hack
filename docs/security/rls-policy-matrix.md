# RIVET RLS policy matrix (Mission 017.1)

| Table | Read | Insert | Update | Delete |
|---|---|---|---|---|
| profiles | own row | own row | own row (display_name only) | (cascade) |
| user_roles | none (client) | none | none | none |
| incidents | members | authenticated (created_by = uid) | owner | none (soft archive) |
| incident_members | members | owner | owner (role only) | owner (last-owner protected) |
| acquisitions | members | owner/analyst | owner/analyst (source_metadata only) | none |
| evidence_records | members | owner/analyst (draft only) | owner/analyst (not review_state/identity) | none |
| processing_jobs | members | owner/analyst | none (client) | none |
| decisions | members | via submit_evidence_decision only | none | none |
| reports | members | owner/analyst | none | none |
| audit_events | members (non-null incident) | trigger only | denied | denied |

Column-level grants enforce immutability of identity/provenance fields. SECURITY DEFINER helpers live in `private` schema with search_path=''.
