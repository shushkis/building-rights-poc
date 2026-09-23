"""Esri-JSON -> GeoPandas conversion helpers (ITM 2039 throughout)."""
from __future__ import annotations

import geopandas as gpd
import pandas as pd
from shapely.geometry import (LineString, MultiLineString, MultiPolygon,
                              Point, Polygon)
from shapely.geometry.polygon import orient
from shapely.ops import unary_union

from poc import config


def _rings_to_polygons(rings: list) -> list[Polygon]:
    """Esri rings: clockwise = outer, counter-clockwise = hole.

    Ring orientation in the wild is unreliable, so we build candidate
    polygons and assign holes by containment rather than trusting winding.
    """
    polys = [Polygon(r) for r in rings if r and len(r) >= 4]
    polys = [p if p.is_valid else p.buffer(0) for p in polys]
    polys = [p for p in polys if not p.is_empty and p.area > 0]
    if not polys:
        return []

    polys.sort(key=lambda p: p.area, reverse=True)
    outers: list[Polygon] = []
    holes: list[Polygon] = []
    for p in polys:
        if any(o.contains(p.representative_point()) for o in outers):
            holes.append(p)
        else:
            outers.append(p)

    result = []
    for o in outers:
        my_holes = [h.exterior.coords for h in holes if o.contains(h.representative_point())]
        poly = Polygon(o.exterior.coords, my_holes)
        result.append(poly if poly.is_valid else poly.buffer(0))
    return [r for r in result if not r.is_empty]


def esri_geometry_to_shapely(geom: dict | None):
    if not geom:
        return None
    if "rings" in geom:
        polys = _rings_to_polygons(geom["rings"])
        if not polys:
            return None
        return polys[0] if len(polys) == 1 else MultiPolygon(
            [g for p in polys for g in (p.geoms if p.geom_type == "MultiPolygon" else [p])]
        )
    if "paths" in geom:
        lines = [LineString(p) for p in geom["paths"] if p and len(p) >= 2]
        if not lines:
            return None
        return lines[0] if len(lines) == 1 else MultiLineString(lines)
    if "x" in geom and "y" in geom:
        if geom["x"] is None or geom["y"] is None:
            return None
        return Point(geom["x"], geom["y"])
    return None


def featureset_to_gdf(fs: dict) -> gpd.GeoDataFrame:
    """Convert an Esri FeatureSet into a GeoDataFrame in EPSG:2039."""
    rows, geoms = [], []
    for feat in fs.get("features", []):
        rows.append(feat.get("attributes", {}) or {})
        geoms.append(esri_geometry_to_shapely(feat.get("geometry")))
    df = pd.DataFrame(rows)
    if df.empty:
        df = pd.DataFrame(index=range(len(geoms)))
    return gpd.GeoDataFrame(df, geometry=geoms, crs=f"EPSG:{config.CRS_ITM}")


def envelope_param(geom) -> dict:
    """Bounding-box query param for a shapely geometry."""
    minx, miny, maxx, maxy = geom.bounds
    return {
        "xmin": minx,
        "ymin": miny,
        "xmax": maxx,
        "ymax": maxy,
        "spatialReference": {"wkid": config.CRS_ITM},
    }


def polygon_param(geom) -> dict:
    """Exact-polygon query param (rings) for a shapely (Multi)Polygon."""
    geom = unary_union(geom)
    parts = geom.geoms if geom.geom_type == "MultiPolygon" else [geom]
    rings = []
    for part in parts:
        part = orient(part, sign=-1.0)  # Esri outer ring = clockwise
        rings.append([list(c) for c in part.exterior.coords])
        for interior in part.interiors:
            rings.append([list(c) for c in reversed(list(interior.coords))])
    return {"rings": rings, "spatialReference": {"wkid": config.CRS_ITM}}
