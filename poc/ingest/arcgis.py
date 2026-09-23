"""ArcGIS REST client with pagination, disk caching and rate limiting."""
from __future__ import annotations

import hashlib
import json
import time
from typing import Any, Iterable

import requests

from poc import config

_last_request_ts = 0.0


def _throttle() -> None:
    """Keep to <= MAX_REQUESTS_PER_SEC."""
    global _last_request_ts
    min_gap = 1.0 / config.MAX_REQUESTS_PER_SEC
    delta = time.monotonic() - _last_request_ts
    if delta < min_gap:
        time.sleep(min_gap - delta)
    _last_request_ts = time.monotonic()


def _cache_path(layer_id: int, params: dict) -> Any:
    key = json.dumps(params, sort_keys=True, ensure_ascii=False)
    digest = hashlib.sha1(key.encode("utf-8")).hexdigest()[:16]
    return config.RAW_DIR / f"layer{layer_id}_{digest}.json"


def _post_query(layer_id: int, params: dict, session: requests.Session) -> dict:
    """One page. Cached to data/raw/ before parsing; never re-fetched."""
    path = _cache_path(layer_id, params)
    if path.exists():
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)

    _throttle()
    url = f"{config.BASE_URL}/{layer_id}/query"
    resp = session.post(url, data=params, timeout=config.REQUEST_TIMEOUT)
    resp.raise_for_status()
    payload = resp.json()

    if "error" in payload:
        raise RuntimeError(f"ArcGIS error on layer {layer_id}: {payload['error']}")

    with open(path, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False)
    return payload


def query_layer(
    layer_id: int,
    where: str = "1=1",
    geometry: dict | None = None,
    geometry_type: str = "esriGeometryEnvelope",
    out_fields: str | Iterable[str] = "*",
    chunk: int = config.CHUNK_SIZE,
    return_geometry: bool = True,
    session: requests.Session | None = None,
) -> dict:
    """Query a layer, following resultOffset pagination to exhaustion.

    Returns a single Esri-JSON FeatureSet with all features concatenated.
    Loops while ``exceededTransferLimit`` is true.
    """
    if not isinstance(out_fields, str):
        out_fields = ",".join(out_fields)

    own_session = session is None
    session = session or requests.Session()

    base = {
        "f": "json",
        "where": where,
        "outFields": out_fields,
        "returnGeometry": str(return_geometry).lower(),
        "inSR": str(config.CRS_ITM),
        "outSR": str(config.CRS_ITM),
        "resultRecordCount": str(chunk),
    }
    if geometry is not None:
        base.update(
            {
                "geometry": json.dumps(geometry),
                "geometryType": geometry_type,
                "spatialRel": "esriSpatialRelIntersects",
            }
        )

    features: list[dict] = []
    merged: dict | None = None
    offset = 0
    seen_oids: set = set()

    try:
        while True:
            params = dict(base, resultOffset=str(offset))
            page = _post_query(layer_id, params, session)

            if merged is None:
                merged = {k: v for k, v in page.items() if k != "features"}

            page_features = page.get("features", []) or []
            oid_field = page.get("objectIdFieldName") or merged.get(
                "objectIdFieldName"
            )

            new_in_page = 0
            for feat in page_features:
                oid = (feat.get("attributes") or {}).get(oid_field) if oid_field else None
                if oid is not None:
                    if oid in seen_oids:
                        continue
                    seen_oids.add(oid)
                features.append(feat)
                new_in_page += 1

            if not page.get("exceededTransferLimit"):
                break
            if new_in_page == 0:
                # Defensive: server claims more but gave us nothing new.
                break
            offset += len(page_features)
    finally:
        if own_session:
            session.close()

    merged = merged or {}
    merged["features"] = features
    merged.pop("exceededTransferLimit", None)
    return merged
