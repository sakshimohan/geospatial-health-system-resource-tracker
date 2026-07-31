"""Load and clean the Malawi health facility dataset."""

import geopandas as gpd
import pandas as pd
from shapely.geometry import Point

from . import config


def load_facilities(path=config.FACILITY_CSV) -> gpd.GeoDataFrame:
    """Load facility_data.csv into a cleaned GeoDataFrame (EPSG:4326)."""
    df = pd.read_csv(path)

    df[config.COL_OWNER] = (
        df[config.COL_OWNER].fillna("").str.strip().replace("", config.UNKNOWN_OWNER_LABEL)
    )
    df[config.COL_LEVEL] = df[config.COL_LEVEL].astype(str).str.strip()

    bad_levels = set(df[config.COL_LEVEL]) - config.VALID_LEVELS
    if bad_levels:
        raise ValueError(f"Unexpected level_of_care values: {bad_levels}")

    missing_coords = df[config.COL_LAT].isna() | df[config.COL_LON].isna()
    if missing_coords.any():
        raise ValueError(f"{missing_coords.sum()} facilities missing lat/long")

    geometry = [Point(xy) for xy in zip(df[config.COL_LON], df[config.COL_LAT])]
    gdf = gpd.GeoDataFrame(df, geometry=geometry, crs=config.WGS84)
    return gdf
