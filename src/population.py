"""Load the WorldPOP population raster."""

from dataclasses import dataclass

import numpy as np
import rasterio

from . import config


@dataclass
class PopulationGrid:
    population: np.ndarray  # 2D float array, person-count per 100m cell
    valid_mask: np.ndarray  # True where the cell is inside Malawi (not raster nodata)
    transform: rasterio.Affine
    crs: str


def load_population_grid(path=config.POPULATION_TIF) -> PopulationGrid:
    with rasterio.open(path) as src:
        arr = src.read(1, masked=True).astype("float32")
        valid_mask = ~arr.mask if np.ma.is_masked(arr) else np.ones(arr.shape, dtype=bool)
        population = np.where(valid_mask, arr.filled(0.0), 0.0)
        return PopulationGrid(
            population=population,
            valid_mask=valid_mask,
            transform=src.transform,
            crs=src.crs,
        )
