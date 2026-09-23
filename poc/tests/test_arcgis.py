"""T1.1 AC: a mocked 2-page response returns all features exactly once."""
import poc.ingest.arcgis as arcgis


def _feat(oid):
    return {"attributes": {"OBJECTID": oid}, "geometry": {"x": oid, "y": oid}}


def test_pagination_returns_all_features_exactly_once(monkeypatch):
    pages = [
        {
            "objectIdFieldName": "OBJECTID",
            "features": [_feat(i) for i in range(1, 4)],
            "exceededTransferLimit": True,
        },
        {
            "objectIdFieldName": "OBJECTID",
            "features": [_feat(i) for i in range(4, 6)],
            "exceededTransferLimit": False,
        },
    ]
    calls = []

    def fake_post(layer_id, params, session):
        calls.append(int(params["resultOffset"]))
        return pages[len(calls) - 1]

    monkeypatch.setattr(arcgis, "_post_query", fake_post)

    result = arcgis.query_layer(999, chunk=3)
    oids = [f["attributes"]["OBJECTID"] for f in result["features"]]

    assert oids == [1, 2, 3, 4, 5]
    assert len(oids) == len(set(oids)), "features must not be duplicated"
    assert calls == [0, 3], "second page must be requested at the right offset"
    assert "exceededTransferLimit" not in result


def test_duplicate_oids_across_pages_are_deduped(monkeypatch):
    pages = [
        {
            "objectIdFieldName": "OBJECTID",
            "features": [_feat(1), _feat(2)],
            "exceededTransferLimit": True,
        },
        {
            "objectIdFieldName": "OBJECTID",
            "features": [_feat(2), _feat(3)],
            "exceededTransferLimit": False,
        },
    ]
    calls = []

    def fake_post(layer_id, params, session):
        calls.append(int(params["resultOffset"]))
        return pages[len(calls) - 1]

    monkeypatch.setattr(arcgis, "_post_query", fake_post)

    result = arcgis.query_layer(999, chunk=2)
    oids = [f["attributes"]["OBJECTID"] for f in result["features"]]
    assert oids == [1, 2, 3]


def test_stops_when_server_returns_no_new_features(monkeypatch):
    """Defensive: a server that always claims more must not spin forever."""
    page = {
        "objectIdFieldName": "OBJECTID",
        "features": [_feat(1)],
        "exceededTransferLimit": True,
    }
    calls = []

    def fake_post(layer_id, params, session):
        calls.append(int(params["resultOffset"]))
        return dict(page)

    monkeypatch.setattr(arcgis, "_post_query", fake_post)

    result = arcgis.query_layer(999, chunk=1)
    assert len(result["features"]) == 1
    assert len(calls) <= 3
