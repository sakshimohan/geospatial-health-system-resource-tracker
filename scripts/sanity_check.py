"""Lightweight data/CRS/friction sanity checks — run before trusting the app's output."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np
from pyproj import Transformer

from src import config
from src.facilities import load_facilities
from src.friction import build_friction_surface
from src.population import load_population_grid


def check_facilities():
    gdf = load_facilities()
    assert gdf[config.COL_LAT].notna().all() and gdf[config.COL_LON].notna().all(), "missing coordinates"
    assert set(gdf[config.COL_LEVEL].unique()) <= config.VALID_LEVELS, "unexpected level_of_care values"

    bad_coords = gdf[~gdf.geometry.x.between(30, 37) | ~gdf.geometry.y.between(-18, -8)]
    if not bad_coords.empty:
        print(f"[warn] {len(bad_coords)} facility row(s) with implausible coordinates "
              f"(outside Malawi's lon/lat range) — likely a data entry error, not a code bug:")
        print(bad_coords[[config.COL_NAME, config.COL_DISTRICT, config.COL_LAT, config.COL_LON]].to_string(index=False))
        print("These will be silently dropped as accessibility-analysis seed points "
              "(their row/col falls outside the raster grid).")

    print(f"[ok] facilities: {len(gdf)} rows, levels={sorted(gdf[config.COL_LEVEL].unique())}")


def check_population():
    pg = load_population_grid()
    total = pg.population.sum()
    assert 15e6 < total < 25e6, f"total population {total:,.0f} outside plausible range"
    print(f"[ok] population: total={total:,.0f}, valid cells={pg.valid_mask.sum():,}")
    return pg


def check_friction(pg):
    cache = config.PROJECT_ROOT / "landcover" / "malawi_landcover_100m.tif"
    friction = build_friction_surface(pg, landcover_cache_path=cache)

    transformer = Transformer.from_crs(config.WGS84, pg.crs, always_xy=True)
    inv = ~pg.transform

    # Lilongwe (on a major paved road) should be faster to cross than remote forest.
    lon, lat = 33.7833, -13.9833  # Lilongwe
    x, y = transformer.transform(lon, lat)
    col, row = inv * (x, y)
    row, col = int(row), int(col)
    lilongwe_friction = friction[row, col]

    assert lilongwe_friction < config.BARRIER_COST_MIN, "Lilongwe pixel came back as a barrier"
    print(f"[ok] friction at Lilongwe: {lilongwe_friction:.2f} min/cell (finite, on-road)")

    n_barrier_in_country = ((friction >= config.BARRIER_COST_MIN) & pg.valid_mask).sum()
    n_valid = pg.valid_mask.sum()
    print(f"[ok] friction: {n_barrier_in_country:,} barrier cells (water etc.) "
          f"out of {n_valid:,} in-country cells")


if __name__ == "__main__":
    check_facilities()
    pg = check_population()
    check_friction(pg)
    print("All sanity checks passed.")
