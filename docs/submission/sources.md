# Sources

Statuses describe how Mission 000 used the source. Mission 001 did not fetch these pages again. Granule-level records derived from them stay provisional. See `docs/science/mission-000-audit.md`.

## NISAR catalogue and documentation

| Source | URL | Use |
| --- | --- | --- |
| ASF, available NISAR data | https://nisar-docs.asf.alaska.edu/availability-overview/ | Release dates, CRID P05023 and P05036, instrument gap, reprocessing plan |
| ASF, product overview | https://nisar-docs.asf.alaska.edu/products-overview/ | GCOV, GSLC, GUNW, GOFF roles and posting summary |
| ASF, GCOV | https://nisar-docs.asf.alaska.edu/gcov/ | Frequency-A posting of 10 m at 40 MHz and 20 m at 20 MHz |
| ASF, GOFF | https://nisar-docs.asf.alaska.edu/goff/ | 80 m posting and cryosphere intent |
| ASF, access | https://nisar-docs.asf.alaska.edu/access-overview/ | L-band at ASF, S-band at Bhoonidhi |
| NASA Earthdata, L-band public release | https://www.earthdata.nasa.gov/data/alerts-outages/nisar-l-band-data-now-publicly-available | July 2026 provisional release statement |
| NASA CMR search | https://cmr.earthdata.nasa.gov/search/granules.json | Anonymous metadata search. No science file downloaded |
| Earthdata Login | https://urs.earthdata.nasa.gov/ | Account the founder creates later. No credential was collected |

Example query, provisional GCOV, discovery box and window:

`https://cmr.earthdata.nasa.gov/search/granules.umm_json?short_name=NISAR_L2_GCOV_PROVISIONAL_V1&bounding_box=79.75,30.03,79.87,30.15&temporal=2026-07-08T00:00:00Z,2026-11-14T23:59:59Z&page_size=50`

## S-band distribution, out of the first slice

| Source | URL | Use |
| --- | --- | --- |
| ISRO S-band release note, 24 July 2026 | https://www.isro.gov.in/NISARS_Band_SAR_Data_Products_Release.html | Cycle 25 start, baseline v1.4.0, CRID P00500 |
| Bhoonidhi NISAR products | https://bhoonidhi.nrsc.gov.in/NISAR/NisarProducts.html | Product list and registration path |
| Bhoonidhi home | https://bhoonidhi.nrsc.gov.in/bhoonidhi/home.html | Portal entry |

No Bhoonidhi search was completed. Granule coverage of Kuwari is blocked on authentication.

## Kuwari research

| Source | URL | Use |
| --- | --- | --- |
| Ghoke and colleagues, *Discover Geoscience*, 5 September 2026 | https://link.springer.com/article/10.1007/s44288-026-00717-w | Primary prior study. Optical, Sentinel-1 SBAS, field, MOI/HDSI, HEC-RAS |
| Bisht and colleagues, *Journal of the Geological Society of India*, 2022 | https://doi.org/10.1007/s12594-022-1927-3 | Earlier LLOF note |
| NRSC/NDEM Kunwari observation, 2022 | https://ndem.nrsc.gov.in/documents/Disaster_Document/2022/UK/Kunwari_landslide_lake_Uttarakhand.pdf | Earlier lake observations. Uses the name Baura gad |
| SANDRP, 22 November 2024 | https://sandrp.in/2024/11/22/uttarakhand-kunwari-potentially-dangerous-for-landslides-dam-in-pindar-valley/ | Secondary commentary. Source of the coordinate used in the point test |

The 2026 paper states that its NRSC analysis data are not openly posted. This repository does not copy those figures or rasters.

## Other systems, for differentiation only

| Source | URL | What it is |
| --- | --- | --- |
| NRSC disaster applications, including NDEM | https://www.nrsc.gov.in/nrscnew/Apps_DMS.php | National operational geospatial support. RIVET does not replace it |
| myDEWETRA.world | https://www.infomydewetra.world/ | Monitoring and forecasting platform |
| GNS DBI tool | https://eild.gns.cri.nz/dbi/about.html | Preliminary landslide-dam screening index, not a breach hydrograph |

## Repository

| Source | URL | State at Mission 001 |
| --- | --- | --- |
| GitHub | https://github.com/mahitss/sar_nasa_hack | Public. Empty at the start of Mission 001. Local `main` has no commit yet |
