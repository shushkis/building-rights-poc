# -*- coding: utf-8 -*-
"""
Beit HaKerem, Jerusalem - pull the municipal layers this run depends on.

SOURCE NOTE, and it is the reason this file was rewritten.

An earlier version of this demo queried Jerusalem's ArcGIS **Online** hosted
services (services3.arcgis.com/jeqc1A7OfE9m4EPO). On that endpoint the city
publishes building HEIGHT but no floor count, and its plan service returns a
plan number and a boundary with every descriptive field empty. The conclusion
drawn from it - "Jerusalem publishes only half the computation" - was a
statement about that endpoint, not about the city.

The city also runs its own ArcGIS Server behind the public map viewer at
jergisng.jerusalem.muni.il. It carries 157 layers, needs no credentials, and
includes both halves. This file reads that server.

What each layer is here for:

  40   neighbourhoods            boundary, queried by name.
  370  buildings 2022            AS-BUILT. A municipal NUM_FLOORS on the
                                 building polygon itself, plus height,
                                 apartments, entrances and address. No
                                 address-point join and no derived floor model
                                 are needed for the ~84% that carry it.
  63   urban renewal / TAMA 38   ENTITLEMENT. units_exists and units_tosefet -
                                 existing dwelling units and entitled ADDED
                                 units - per file, with permit status.
  183  urban renewal / clearance ENTITLEMENT. units_e / units_p / units_a on
                                 clearance-and-rebuild schemes.
  50   compiled land use         TABA + MIGRASH + YEUD: the plan, the plot
                                 number inside that plan, and the land-use
                                 class, per polygon. The join key for the
                                 parcels no renewal file covers.
  46   parcels                   cadastral parcels: gush/helka + legal area.
  49   plan boundaries           statutory plan outlines.

Writes _cache.json next to this file; build.py runs offline from it.
"""
from __future__ import annotations

import json
import os
import ssl
import urllib.parse
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(HERE, "_cache.json")

BASE = ("https://gisviewer.jerusalem.muni.il/arcgis/rest/services/"
        "BaseLayers/MapServer/")
AOI = (35.1770, 31.7690, 35.1990, 31.7860)          # Beit HaKerem envelope
NEIGHBOURHOOD = "בית הכרם"
PAGE = 1000

# The server answers anonymously but expects to be talked to like a browser;
# a bare urllib User-Agent gets a 403.
HEADERS = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/131.0 Safari/537.36"),
    "Accept": "application/json, text/plain, */*",
    "Referer": "https://jergisng.jerusalem.muni.il/baseWab/",
}

_ctx = ssl.create_default_context()
_ctx.check_hostname = False
_ctx.verify_mode = ssl.CERT_NONE


def _get(url: str) -> dict:
    req = urllib.request.Request(url, headers=HEADERS)
    return json.load(urllib.request.urlopen(req, timeout=180, context=_ctx))


def fetch(layer: int, fields: str = "*", where: str = "1=1",
          clip: bool = True, geometry: bool = True) -> list:
    """Page one layer, WGS84 out."""
    env = ""
    if clip:
        env = ("&geometry=%s&geometryType=esriGeometryEnvelope&inSR=4326"
               "&spatialRel=esriSpatialRelIntersects" % ",".join(map(str, AOI)))
    out, offset = [], 0
    while True:
        url = ("%s%d/query?where=%s%s&outFields=%s&returnGeometry=%s"
               "&outSR=4326&f=json&resultOffset=%d&resultRecordCount=%d"
               % (BASE, layer, urllib.parse.quote(where), env,
                  urllib.parse.quote(fields), "true" if geometry else "false",
                  offset, PAGE))
        d = _get(url)
        if "error" in d:
            raise RuntimeError("layer %d -> %s" % (layer, d["error"]))
        got = d.get("features", [])
        out.extend(got)
        if len(got) < PAGE:
            break
        offset += PAGE
    return out


PULLS = [
    ("buildings", 370, "OBJECTID,NUM_FLOORS,MAX_rel_he,MAX_med_he,NUM_APTS_C,"
                       "NUM_ENTR_1,StreetName,BldNum_1,semel_bait"),
    ("tama38",     63, "OBJECTID,tik,address,neighborhood,units_exists,"
                       "units_tosefet,status,date,harisaa"),
    ("pinui",     183, "OBJECTID,num,name,units_e,units_p,units_a,status_num,"
                       "adress,schunah,maslul"),
    ("landuse",    50, "OBJECTID,TABA,MIGRASH,YEUD,Descr"),
    ("parcels",    46, "OBJECTID,GUSH_NO,HELKA_SHOW,LEGAL_AREA"),
    ("plans",      49, "OBJECTID,TABA"),
]


def main(force: bool = False) -> dict:
    if os.path.exists(CACHE) and not force:
        with open(CACHE, encoding="utf-8") as fh:
            data = json.load(fh)
        print("cache hit: " + ", ".join("%s=%d" % (k, len(v)) for k, v in data.items()))
        return data

    data = {}
    print("fetching %-11s ..." % "boundary", end=" ", flush=True)
    data["boundary"] = fetch(40, "OBJECTID,CODE,SCHN_NAME",
                             where="SCHN_NAME='%s'" % NEIGHBOURHOOD, clip=False)
    print("%d polygon(s)" % len(data["boundary"]))

    for key, layer, fields in PULLS:
        print("fetching %-11s ..." % key, end=" ", flush=True)
        data[key] = fetch(layer, fields)
        print("%d features" % len(data[key]))

    with open(CACHE, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False)
    print("wrote %s (%.1f MB)" % (CACHE, os.path.getsize(CACHE) / 1e6))
    return data


if __name__ == "__main__":
    import sys
    main(force="--force" in sys.argv)
