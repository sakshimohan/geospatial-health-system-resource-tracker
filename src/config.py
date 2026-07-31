"""Paths, CRS, and lookup tables for the Malawi accessibility app."""

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

FACILITY_CSV = PROJECT_ROOT / "facility_data.csv"
POPULATION_TIF = PROJECT_ROOT / "Malawi_100m_Population" / "MWI_ppp_2020_adj_v2.tif"
ROADS_SHP = PROJECT_ROOT / "roads" / "gis_osm_roads_free_1.shp"

WGS84 = "EPSG:4326"

# ESA WorldCover 10m COGs (public S3), read via windowed/warped access — no local
# download needed. Tiles are named by their lower-left (S, E) corner, 3x3 degrees.
WORLDCOVER_BASE_URL = (
    "https://esa-worldcover.s3.eu-central-1.amazonaws.com/v200/2021/map/"
    "ESA_WorldCover_10m_2021_v200_{tile}_Map.tif"
)
# Tiles covering the WorldPOP Malawi raster's bounding box (lon 32.67-35.92,
# lat -17.13 to -9.36).
WORLDCOVER_TILES = [
    "S18E030", "S18E033",
    "S15E030", "S15E033",
    "S12E030", "S12E033",
]

# Facility CSV column names (as found in facility_data.csv)
COL_DISTRICT = "district"
COL_NAME = "fac_name"
COL_LEVEL = "level_of_care"
COL_LAT = "lat"
COL_LON = "long"
COL_OWNER = "fac_owner"

VALID_LEVELS = {"1a", "1b", "2", "3", "4"}
UNKNOWN_OWNER_LABEL = "Unknown"

# Loose grouping for map legend / future filtering — level_of_care codes as used in
# facility_data.csv don't map to a documented official standard here, so this grouping
# is an assumption (1a/1b treated as primary, 2 as secondary, 3/4 as tertiary) and
# should be checked against the actual Malawi MOH facility classification.
LEVEL_GROUP = {
    "1a": "Primary",
    "1b": "Primary",
    "2": "Secondary",
    "3": "Tertiary",
    "4": "Tertiary",
}

LEVEL_COLORS = {
    "1a": "#66c2a5",
    "1b": "#3288bd",
    "2": "#fee08b",
    "3": "#f46d43",
    "4": "#9e0142",
}

# ESA WorldCover class codes -> off-road walking speed (km/h).
# Reference values only — reasonable defaults, not a validated calibration.
LANDCOVER_SPEED_KMH = {
    10: 2.5,   # tree cover
    20: 3.0,   # shrubland
    30: 4.0,   # grassland
    40: 4.5,   # cropland
    50: 5.0,   # built-up
    60: 4.0,   # bare / sparse vegetation
    70: 0.0,   # snow and ice (impassable; not expected in Malawi)
    80: 0.0,   # permanent water bodies (barrier)
    90: 1.5,   # herbaceous wetland
    95: 0.5,   # mangroves
    100: 4.0,  # moss and lichen
}
DEFAULT_LANDCOVER_SPEED_KMH = 3.0  # fallback for any unmapped/nodata class

# OSM `fclass` (Geofabrik roads layer) -> walking speed (km/h). Roads give a modest
# boost over open-ground walking; unpaved tracks/paths less so.
ROAD_SPEED_KMH = {
    "motorway": 5.5, "motorway_link": 5.5,
    "trunk": 5.5, "trunk_link": 5.5,
    "primary": 5.5, "primary_link": 5.5,
    "secondary": 5.5, "secondary_link": 5.5,
    "tertiary": 5.0, "tertiary_link": 5.0,
    "unclassified": 4.5,
    "residential": 4.5,
    "living_street": 4.5,
    "service": 4.5,
    "track": 4.0,
    "track_grade1": 4.0, "track_grade2": 3.8, "track_grade3": 3.6,
    "track_grade4": 3.4, "track_grade5": 3.2,
    "path": 3.5,
    "footway": 4.0,
    "pedestrian": 4.5,
    "steps": 2.0,
    "cycleway": 4.0,
    "bridleway": 3.5,
}
DEFAULT_ROAD_SPEED_KMH = 4.5  # fallback for any unmapped road class

# Impassable / barrier cost (minutes per 100m cell) used for permanent water and
# outside-country nodata cells, so cost-distance paths route around them.
BARRIER_COST_MIN = 1e6
