# Sources

Mission 000 and Mission 001 source notes remain below. Mission 002 re-queried NASA CMR on 2026-11-14T09:43:06Z and re-read the ASF product pages used for the mask and pixel-spacing statements. The revalidated granule record is `data/manifests/nisar_kuwari_catalogue.json`. It is a catalogue record, not a processed measurement. Mission 000 identifiers in `docs/science/mission-000-audit.md` are the earlier inspection, not a second authority.

## NISAR catalogue and documentation

| Source | URL | Use |
| --- | --- | --- |
| ASF, available NISAR data | https://nisar-docs.asf.alaska.edu/availability-overview/ | Release dates, CRID P05023 and P05036, instrument gap, reprocessing plan |
| ASF, product overview | https://nisar-docs.asf.alaska.edu/products-overview/ | Product roles. The GSLC additional mask indicates water bodies and shadow-layover. GCOV additional layers are mask, number of looks, and the RTC factor. |
| ASF, GCOV | https://nisar-docs.asf.alaska.edu/gcov/ | Pixel spacing by bandwidth. `numberOfLooks` and the GCOV `mask` describe adaptive multi-looking, not a water class. |
| ASF, GOFF | https://nisar-docs.asf.alaska.edu/goff/ | 80 m posting and cryosphere intent |
| ASF, access | https://nisar-docs.asf.alaska.edu/access-overview/ | L-band at ASF, S-band at Bhoonidhi |
| NASA Earthdata, L-band public release | https://www.earthdata.nasa.gov/data/alerts-outages/nisar-l-band-data-now-publicly-available | July 2026 provisional release statement |
| NASA CMR UMM JSON search | https://cmr.earthdata.nasa.gov/search/granules.umm_json | Mission 002 anonymous metadata search. No science file downloaded. |
| Earthdata Login | https://urs.earthdata.nasa.gov/ | Account the founder creates later. No credential was collected |

Mission 002 query shape, repeated for each short name and each CMR page:

`https://cmr.earthdata.nasa.gov/search/granules.umm_json?short_name=NISAR_L2_GCOV_PROVISIONAL_V1&bounding_box=79.75%2C30.03%2C79.87%2C30.15&temporal=2026-07-08T00%3A00%3A00Z%2C2026-11-14T23%3A59%3A59Z&page_size=200&page_num=1`

The same bounding box, temporal range, and page size were used for `NISAR_L2_GSLC_PROVISIONAL_V1`, `NISAR_L2_GCOV_V1`, and `NISAR_L2_GSLC_V1`. Each of those searches returned one page. Hit counts were 23, 24, 5, and 5.

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

| Source | URL | State |
| --- | --- | --- |
| GitHub | https://github.com/mahitss/sar_nasa_hack | Public. Foundation commit `98a00e6f3d619ee2446f1fabc41a6837dd7ec455` is on `main` and on `origin/main`. Mission 002 changes are local until a later review approves a commit. |
