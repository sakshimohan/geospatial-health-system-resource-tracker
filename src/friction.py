"""Build a walking-speed friction (time-cost) surface from land cover + roads."""

import geopandas as gpd
import numpy as np
import rasterio
from rasterio.features import rasterize
from rasterio.warp import reproject, Resampling

from . import config
from .population import PopulationGrid

CELL_SIZE_KM = 0.1  # ~100m WorldPOP cell


def _fetch_landcover(ref: PopulationGrid, cache_path=None) -> np.ndarray:
    """Reproject+mosaic ESA WorldCover COGs (streamed over HTTP) onto ref's grid."""
    if cache_path and cache_path.exists():
        with rasterio.open(cache_path) as src:
            return src.read(1)

    shape = ref.population.shape
    mosaic = np.zeros(shape, dtype="uint8")
    for tile in config.WORLDCOVER_TILES:
        url = config.WORLDCOVER_BASE_URL.format(tile=tile)
        dst = np.zeros(shape, dtype="uint8")
        with rasterio.open(url) as src:
            reproject(
                source=rasterio.band(src, 1),
                destination=dst,
                src_transform=src.transform,
                src_crs=src.crs,
                dst_transform=ref.transform,
                dst_crs=ref.crs,
                resampling=Resampling.nearest,
            )
        mosaic = np.where(mosaic == 0, dst, mosaic)

    if cache_path:
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        with rasterio.open(
            cache_path, "w", driver="GTiff", height=shape[0], width=shape[1],
            count=1, dtype="uint8", crs=ref.crs, transform=ref.transform,
            compress="deflate",
        ) as dst_ds:
            dst_ds.write(mosaic, 1)

    return mosaic


def _landcover_speed(landcover: np.ndarray) -> np.ndarray:
    lookup = np.full(256, config.DEFAULT_LANDCOVER_SPEED_KMH, dtype="float32")
    for code, speed in config.LANDCOVER_SPEED_KMH.items():
        lookup[code] = speed
    lookup[0] = 0.0  # unfilled/nodata mosaic cells -> barrier
    return lookup[landcover]


def _road_speed(ref: PopulationGrid) -> np.ndarray:
    roads = gpd.read_file(config.ROADS_SHP).to_crs(ref.crs)
    shape = ref.population.shape
    speed = np.zeros(shape, dtype="float32")

    # Rasterize slowest classes first so faster classes win where roads overlap a cell.
    classes_by_speed = sorted(
        roads["fclass"].dropna().unique(),
        key=lambda c: config.ROAD_SPEED_KMH.get(c, config.DEFAULT_ROAD_SPEED_KMH),
    )
    for fclass in classes_by_speed:
        geoms = roads.loc[roads["fclass"] == fclass, "geometry"]
        if geoms.empty:
            continue
        class_speed = config.ROAD_SPEED_KMH.get(fclass, config.DEFAULT_ROAD_SPEED_KMH)
        burned = rasterize(
            [(geom, 1) for geom in geoms if geom is not None],
            out_shape=shape,
            transform=ref.transform,
            fill=0,
            dtype="uint8",
        )
        speed = np.where(burned == 1, class_speed, speed)

    return speed


def build_friction_surface(ref: PopulationGrid, landcover_cache_path=None) -> np.ndarray:
    """Return a (minutes-to-cross-one-cell) friction array, same shape as ref.population."""
    landcover = _fetch_landcover(ref, cache_path=landcover_cache_path)
    landcover_speed = _landcover_speed(landcover)
    road_speed = _road_speed(ref)

    speed_kmh = np.where(road_speed > 0, road_speed, landcover_speed)
    speed_kmh = np.where(ref.valid_mask, speed_kmh, 0.0)

    friction = np.full(speed_kmh.shape, config.BARRIER_COST_MIN, dtype="float32")
    passable = speed_kmh > 0
    friction[passable] = (CELL_SIZE_KM / speed_kmh[passable]) * 60.0
    return friction
