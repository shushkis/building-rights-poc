"""T1.3-T1.5 - fetch all AOI layers and persist as GeoParquet."""
from __future__ import annotations

import geopandas as gpd
import requests

from poc import config
from poc.ingest import esri
from poc.ingest.aoi import aoi_geometry
from poc.ingest.arcgis import query_layer

BUILDING_FIELDS = [
    "oid_mivne", "id_binyan", "ms_komot", "gova_simplex_2019",
    "dsm_mean", "dsm_max", "min_height", "max_height",
    "year", "t_sug_mivne", "shem_mivne", "t_amudim",
]
LOT_FIELDS = [
    "oid_migrash", "ms_gush", "ms_migrash", "st_taba", "st_taba_kavaa_yeud",
    "t_yeud_karka", "t_yeud_rashi", "ms_shetach_rashum",
    "ms_shetach_lechishuv_zchuyot", "ms_shetach", "id_taba",
    "k_status_migrash", "sw_migrash_betochnit_chadasha",
]
PARCEL_FIELDS = ["oid_chelka", "ms_gush", "ms_chelka", "ms_gush_vechelka", "ms_shetach"]
PERMIT_FIELDS = [
    "oid_permit", "permission_date", "permission_num", "sw_tama_38",
    "sw_tama_38_chadash", "sw_tama_38_tosefet", "yechidot_diyur",
    "building_stage", "sug_bakasha", "tochen_bakasha",
    "hakala_tosefet_achuz_shetach", "hakala_yd_mevukash", "ms_tik_binyan",
    "addresses", "request_stage", "tr_hathalat_bniya",
]
# NOTE: layer 682 advertises `bitul_logi` in its metadata but the server
# returns HTTP 400 when it is requested. Excluded deliberately.
PRESERVATION_FIELDS = ["oid", "shem_mivne", "st_taba", "t_hatraa", "hagbalot", "ktovot"]
TABA_FIELDS = [
    "oid_taba", "id_taba", "taba", "shem_taba", "tr_matan_tokef",
    "t_status", "k_status", "url_documents", "sw_hitchadshut_ironit",
]

ADDRESS_FIELDS = [
    "oid_ktovet", "t_rechov", "t_rechov_eng", "ms_bayit", "knisa",
    "t_ktovet_melea", "ms_gush", "ms_chelka",
]
STREET_LINE_FIELDS = ["oid_rechov", "k_rechov", "t_rechov", "shem_angli", "t_sug"]

DATASETS = {
    "buildings": (config.LAYER_BUILDINGS, BUILDING_FIELDS),
    "lots": (config.LAYER_LANDUSE_LOTS, LOT_FIELDS),
    "parcels": (config.LAYER_PARCELS, PARCEL_FIELDS),
    "permits": (config.LAYER_PERMITS, PERMIT_FIELDS),
    "preservation": (config.LAYER_PRESERVATION, PRESERVATION_FIELDS),
    "taba": (config.LAYER_TABA, TABA_FIELDS),
    "addresses": (config.LAYER_ADDRESSES, ADDRESS_FIELDS),
    "street_lines": (config.LAYER_STREET_LINES, STREET_LINE_FIELDS),
}


def fetch_dataset(name: str, force: bool = False) -> gpd.GeoDataFrame:
    """Fetch one AOI-intersecting dataset, clipped precisely to the AOI."""
    path = config.PROCESSED_DIR / f"{name}.parquet"
    if path.exists() and not force:
        return gpd.read_parquet(path)

    layer_id, fields = DATASETS[name]
    aoi = aoi_geometry()

    with requests.Session() as session:
        fs = query_layer(
            layer_id,
            geometry=esri.polygon_param(aoi),
            geometry_type="esriGeometryPolygon",
            out_fields=fields,
            session=session,
        )
    gdf = esri.featureset_to_gdf(fs)
    gdf = gdf[gdf.geometry.notna()].copy()

    # Server-side spatialRel is inclusive; enforce true intersection locally.
    if len(gdf):
        gdf = gdf[gdf.geometry.intersects(aoi)].copy()
        # buffer(0) repairs invalid polygons, but annihilates points/lines --
        # apply it only to areal geometry.
        is_areal = gdf.geometry.geom_type.isin(["Polygon", "MultiPolygon"])
        if is_areal.any():
            gdf.loc[is_areal, "geometry"] = gdf.loc[is_areal, "geometry"].buffer(0)
        gdf = gdf[~gdf.geometry.is_empty].copy()

    gdf.to_parquet(path)
    return gdf


def fetch_all(force: bool = False) -> dict[str, gpd.GeoDataFrame]:
    out = {}
    for name in DATASETS:
        gdf = fetch_dataset(name, force=force)
        out[name] = gdf
        print(f"  {name:<13} {len(gdf):>6} features -> {name}.parquet")
    return out


if __name__ == "__main__":
    print("Fetching AOI datasets (ITM 2039)...")
    fetch_all()
