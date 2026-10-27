import httpx
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app

from .conftest import DAY, local_utc


def test_dashboard_served(client):
    resp = client.get("/")
    assert resp.status_code == 200
    assert "Presence" in resp.text


def test_sync_is_idempotent_and_totals_by_app(client):
    first = client.post(f"/api/sync/activitywatch?day={DAY}").json()
    assert first == {"fetched": 3, "added": 3}
    second = client.post(f"/api/sync/activitywatch?day={DAY}").json()
    assert second == {"fetched": 3, "added": 0}

    body = client.get(f"/api/activity?day={DAY}").json()
    assert len(body["events"]) == 3
    assert body["apps"] == [{"app": "Code", "seconds": 3000}, {"app": "Firefox", "seconds": 600}]


def test_other_day_is_empty(client):
    client.post(f"/api/sync/activitywatch?day={DAY}")
    assert client.get("/api/activity?day=2026-06-05").json()["events"] == []


def test_sync_reports_unreachable_activitywatch(tmp_path):
    def boom(request):
        raise httpx.ConnectError("refused", request=request)

    settings = Settings(db_path=tmp_path / "t.db", aw_url="http://aw.test", aw_timeout=1)
    http = httpx.Client(transport=httpx.MockTransport(boom))
    with TestClient(create_app(settings, http_client=http)) as c:
        resp = c.post(f"/api/sync/activitywatch?day={DAY}")
    assert resp.status_code == 502
    assert "ActivityWatch" in resp.json()["detail"]


def test_lifecycle_upload_and_timeline(client):
    csv_text = f"start,end,name,activity\n{local_utc(9, 15)},{local_utc(11)},Library,Study\n"
    resp = client.post("/api/import/lifecycle", files={"file": ("export.csv", csv_text, "text/csv")})
    assert resp.json() == {"parsed": 1, "added": 1}
    again = client.post("/api/import/lifecycle", files={"file": ("export.csv", csv_text, "text/csv")})
    assert again.json()["added"] == 0

    places = client.get(f"/api/places?day={DAY}").json()["places"]
    assert [p["name"] for p in places] == ["Library"]

    client.post(f"/api/sync/activitywatch?day={DAY}")
    items = client.get(f"/api/timeline?day={DAY}").json()["items"]
    assert [(i["kind"], i["label"]) for i in items] == [
        ("app", "Code"),
        ("place", "Library"),
        ("app", "Firefox"),
        ("app", "Code"),
    ]
    assert items[1]["seconds"] == 105 * 60


def test_bad_csv_returns_400(client):
    resp = client.post("/api/import/lifecycle", files={"file": ("x.csv", "a,b\n1,2\n", "text/csv")})
    assert resp.status_code == 400


def test_non_utf8_upload_returns_400(client):
    resp = client.post("/api/import/lifecycle", files={"file": ("x.csv", b"\xff\xfe\x00bad", "text/csv")})
    assert resp.status_code == 400
