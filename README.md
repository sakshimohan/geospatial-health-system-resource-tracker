# Malawi Health Facility Accessibility (v1)

For a chosen walking travel-time threshold, what share of Malawi's population can reach
a health facility? First milestone toward a broader tool assessing access to health
services against the resources actually available at each facility. See
`.claude` plan history for the fuller roadmap and scope decisions.

Travel time is estimated with an **isotropic cost-distance model** (land cover + roads,
no terrain/slope) — the same family of method as AccessMod, simplified. Output is
travel *time* in minutes, not straight-line distance.

## Setup

```bash
conda env create -f environment.yml
conda activate gis-vibe
```

## Data

Already in the repo:
- `facility_data.csv` — 677 facilities (district, name, level_of_care, lat/long, owner)
- `Malawi_100m_Population/MWI_ppp_2020_adj_v2.tif` — WorldPOP 100m population count
  (gitignored — large file, not committed)

Fetched automatically at first run (no manual download needed):
- **Land cover**: ESA WorldCover 10m 2021, streamed directly from its public S3 bucket
  (Cloud-Optimized GeoTIFF, read via HTTP range requests — only the Malawi-extent window
  is transferred, not full 3°x3° tiles). Reprojected onto the population grid and cached
  locally to `landcover/malawi_landcover_100m.tif` (gitignored) after the first run.
- **Roads**: OpenStreetMap Malawi extract from Geofabrik
  (`https://download.geofabrik.de/africa/malawi-latest-free.shp.zip`). Extract
  `gis_osm_roads_free_1.shp` (+ its `.dbf`/`.shx`/`.prj`) into `roads/` (gitignored).

## Run

```bash
python scripts/sanity_check.py   # quick data/CRS/friction checks
streamlit run app.py
```

The first run builds the friction surface (land cover + roads → walking-speed raster)
and caches it to `landcover/malawi_landcover_100m.tif`; subsequent runs and facility
filter changes are fast except for the cost-distance solve itself, which reruns
whenever the level_of_care/owner filter changes (shows a spinner).

## What's in scope for v1 / what's not

- Walking mode only; no vehicle/multi-modal travel.
- Isotropic cost-distance (no DEM/slope) — terrain is a candidate future addition if it
  turns out to matter.
- No district-level aggregation or boundary polygons — national totals only.
- `level_of_care` grouping (1a/1b→Primary, 2→Secondary, 3/4→Tertiary) in
  `src/config.py` is an assumption, not a confirmed official classification — check
  before relying on it.
