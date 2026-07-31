"""Streamlit app: population within a given walking travel time of a health facility."""

import folium
import numpy as np
import streamlit as st
from streamlit_folium import st_folium

from src import config
from src.accessibility import (
    coverage_stats,
    downsample_for_map,
    facility_rowcols,
    solve_travel_time,
)
from src.facilities import load_facilities
from src.friction import build_friction_surface
from src.population import load_population_grid

st.set_page_config(page_title="Malawi Health Facility Accessibility", layout="wide")

MAP_DOWNSAMPLE_FACTOR = 10  # ~1km display cells (stats stay at full 100m resolution)
LANDCOVER_CACHE = config.PROJECT_ROOT / "landcover" / "malawi_landcover_100m.tif"


@st.cache_data
def get_facilities():
    return load_facilities()


@st.cache_resource
def get_population():
    return load_population_grid()


@st.cache_resource
def get_friction(_pop):
    return build_friction_surface(_pop, landcover_cache_path=LANDCOVER_CACHE)


@st.cache_resource
def get_travel_time(_friction, _pop, levels, owners):
    facilities = get_facilities()
    filtered = facilities[
        facilities[config.COL_LEVEL].isin(levels) & facilities[config.COL_OWNER].isin(owners)
    ]
    starts = facility_rowcols(filtered, _pop)
    return solve_travel_time(_friction, starts), len(filtered)


st.title("Malawi Health Facility Accessibility")
st.caption(
    "Population within a given walking travel time of a health facility "
    "(cost-distance from land cover + roads, no terrain — see project plan for scope)."
)

facilities = get_facilities()
pop_grid = get_population()

all_levels = sorted(facilities[config.COL_LEVEL].unique())
all_owners = sorted(facilities[config.COL_OWNER].unique())

with st.sidebar:
    st.header("Filters")
    levels = st.multiselect("Level of care", all_levels, default=all_levels)
    owners = st.multiselect("Facility owner", all_owners, default=all_owners)
    threshold = st.slider("Max travel time (minutes)", min_value=5, max_value=240, value=60, step=5)

if not levels or not owners:
    st.warning("Select at least one level of care and one owner.")
    st.stop()

with st.spinner("Computing travel-time surface for the selected facilities..."):
    friction = get_friction(pop_grid)
    travel_time, n_facilities = get_travel_time(friction, pop_grid, tuple(levels), tuple(owners))

stats = coverage_stats(travel_time, pop_grid.population, threshold)

c1, c2, c3, c4 = st.columns(4)
c1.metric("Total population", f"{stats['total_population']:,.0f}")
c2.metric(f"Within {threshold} min", f"{stats['covered_population']:,.0f}")
c3.metric("% covered", f"{stats['pct_covered']:.1f}%")
c4.metric("Facilities in filter", n_facilities)

# --- Map ---
m = folium.Map(location=[-13.3, 34.2], zoom_start=7, tiles="cartodbpositron")

filtered_facilities = facilities[
    facilities[config.COL_LEVEL].isin(levels) & facilities[config.COL_OWNER].isin(owners)
]
for _, row in filtered_facilities.iterrows():
    folium.CircleMarker(
        location=[row[config.COL_LAT], row[config.COL_LON]],
        radius=3,
        color=config.LEVEL_COLORS.get(row[config.COL_LEVEL], "#999999"),
        fill=True,
        fill_opacity=0.85,
        weight=1,
        popup=f"{row[config.COL_NAME]} (level {row[config.COL_LEVEL]}, {row[config.COL_OWNER]})",
    ).add_to(m)

covered = (travel_time <= threshold).astype("float32")
pop_ds = downsample_for_map(pop_grid.population, MAP_DOWNSAMPLE_FACTOR, agg="sum")
covered_pop_ds = downsample_for_map(pop_grid.population * covered, MAP_DOWNSAMPLE_FACTOR, agg="sum")
coverage_frac = np.divide(covered_pop_ds, pop_ds, out=np.zeros_like(pop_ds), where=pop_ds > 0)

max_pop = pop_ds.max() if pop_ds.max() > 0 else 1.0
alpha = np.clip(pop_ds / max_pop, 0, 1) ** 0.3 * 0.7
alpha = np.where(pop_ds > 1, alpha, 0.0)  # hide near-zero-population cells entirely

rgba = np.zeros((*coverage_frac.shape, 4), dtype="float32")
rgba[..., 0] = 1.0 - coverage_frac  # red channel: uncovered fraction
rgba[..., 1] = coverage_frac        # green channel: covered fraction
rgba[..., 2] = 0.1
rgba[..., 3] = alpha

height, width = pop_grid.population.shape
transform = pop_grid.transform
west, north = transform * (0, 0)
east, south = transform * (width, height)

folium.raster_layers.ImageOverlay(
    image=rgba,
    bounds=[[south, west], [north, east]],
    opacity=1.0,
    name=f"Coverage at {threshold} min (green=covered, red=uncovered)",
).add_to(m)

folium.LayerControl().add_to(m)
st_folium(m, width=None, height=600)

with st.expander("Legend / notes"):
    st.markdown(
        """
        - **Markers**: health facilities in the current filter, colored by level of care.
        - **Overlay**: populated ~1km cells tinted green (covered) to red (not covered)
          at the chosen travel-time threshold; opacity scales with population density.
          Unpopulated areas are left transparent.
        - Travel time is an isotropic cost-distance estimate (walking speed from land
          cover + roads only — no terrain/slope, no district boundaries yet). See the
          project plan for what's in and out of scope for this version.
        """
    )
