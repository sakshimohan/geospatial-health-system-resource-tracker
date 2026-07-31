"""Cost-distance (isotropic, MCP_Geometric-based) accessibility computation."""

import numpy as np
from skimage.graph import MCP_Geometric

from .population import PopulationGrid


def facility_rowcols(facilities_gdf, ref: PopulationGrid) -> list[tuple[int, int]]:
    """Convert facility lon/lat (already reprojected to ref's CRS if needed) to
    (row, col) indices on ref's grid."""
    inv = ~ref.transform
    rowcols = []
    for geom in facilities_gdf.geometry:
        col, row = inv * (geom.x, geom.y)
        row, col = int(row), int(col)
        if 0 <= row < ref.population.shape[0] and 0 <= col < ref.population.shape[1]:
            rowcols.append((row, col))
    return rowcols


def solve_travel_time(friction: np.ndarray, starts: list[tuple[int, int]]) -> np.ndarray:
    """Cumulative minimum travel time (minutes) from every cell to its nearest start."""
    if not starts:
        return np.full(friction.shape, np.inf, dtype="float32")
    mcp = MCP_Geometric(friction, fully_connected=True)
    costs, _ = mcp.find_costs(starts)
    return costs.astype("float32")


def coverage_stats(travel_time_min: np.ndarray, population: np.ndarray, threshold_min: float) -> dict:
    covered_mask = travel_time_min <= threshold_min
    total_pop = float(population.sum())
    covered_pop = float(population[covered_mask].sum())
    return {
        "total_population": total_pop,
        "covered_population": covered_pop,
        "pct_covered": (covered_pop / total_pop * 100.0) if total_pop > 0 else 0.0,
    }


def downsample_for_map(array: np.ndarray, factor: int, agg="mean") -> np.ndarray:
    """Coarsen array by `factor` for display only (not for stats)."""
    h, w = array.shape
    h_trim, w_trim = h - h % factor, w - w % factor
    trimmed = array[:h_trim, :w_trim]
    reshaped = trimmed.reshape(h_trim // factor, factor, w_trim // factor, factor)
    if agg == "mean":
        return reshaped.mean(axis=(1, 3))
    if agg == "min":
        return reshaped.min(axis=(1, 3))
    if agg == "sum":
        return reshaped.sum(axis=(1, 3))
    raise ValueError(f"Unknown agg: {agg}")
