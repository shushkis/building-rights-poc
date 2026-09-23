"""T1.2 - fetch the Area of Interest polygon (Old North, northern part)."""
from __future__ import annotations

import geopandas as gpd

from poc import config
from poc.ingest import esri
from poc.ingest.arcgis import query_layer

AOI_PATH = config.PROCESSED_DIR / "aoi.geojson"


def fetch_aoi(force: bool = False) -> gpd.GeoDataFrame:
    if AOI_PATH.exists() and not force:
        return gpd.read_file(AOI_PATH).to_crs(epsg=config.CRS_ITM)

    where = f"{config.NEIGHBORHOOD_FIELD} = '{config.NEIGHBORHOOD_NAME}'"
    fs = query_layer(config.LAYER_NEIGHBORHOODS, where=where)
    gdf = esri.featureset_to_gdf(fs)

    if len(gdf) != 1:
        raise AssertionError(
            f"AC violated: expected exactly 1 AOI polygon, got {len(gdf)}"
        )

    area_km2 = float(gdf.geometry.area.iloc[0]) / 1e6
    if not (0.5 <= area_km2 <= 2.5):
        raise AssertionError(
            f"AC violated: AOI area {area_km2:.3f} km2 outside plausible 0.5-2.5 km2"
        )

    AOI_PATH.parent.mkdir(parents=True, exist_ok=True)
    gdf.to_file(AOI_PATH, driver="GeoJSON")
    return gdf


def aoi_geometry():
    return fetch_aoi().geometry.iloc[0]


if __name__ == "__main__":
    g = fetch_aoi(force=True)
    print(f"AOI features: {len(g)}")
    print(f"AOI area: {g.geometry.area.iloc[0] / 1e6:.3f} km2")
    print(f"bounds (ITM): {tuple(round(b, 1) for b in g.total_bounds)}")
