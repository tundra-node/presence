from datetime import UTC, date, datetime, time

import httpx
import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app

DAY = date(2026, 6, 2)


def local_utc(hour: int, minute: int = 0) -> str:
    """An ISO UTC timestamp for a local wall-clock time on DAY."""
    return datetime.combine(DAY, time(hour, minute)).astimezone().astimezone(UTC).isoformat()


AW_BUCKETS = {
    "aw-watcher-window_mac": {"id": "aw-watcher-window_mac", "type": "currentwindow"},
    "aw-watcher-afk_mac": {"id": "aw-watcher-afk_mac", "type": "afkstatus"},
}

AW_EVENTS = [
    {"id": 1, "timestamp": local_utc(9), "duration": 1800.0, "data": {"app": "Code", "title": "presence"}},
    {"id": 2, "timestamp": local_utc(9, 30), "duration": 600.0, "data": {"app": "Firefox", "title": "Docs"}},
    {"id": 3, "timestamp": local_utc(10), "duration": 1200.0, "data": {"app": "Code", "title": "tests"}},
    {"id": 4, "timestamp": local_utc(10, 20), "duration": 0.0, "data": {"app": "Finder", "title": ""}},
]


def fake_aw_handler(request: httpx.Request) -> httpx.Response:
    path = request.url.path
    if path == "/api/0/buckets/":
        return httpx.Response(200, json=AW_BUCKETS)
    if path == "/api/0/buckets/aw-watcher-window_mac/events":
        return httpx.Response(200, json=AW_EVENTS)
    return httpx.Response(404)


@pytest.fixture
def aw_client():
    return httpx.Client(transport=httpx.MockTransport(fake_aw_handler))


@pytest.fixture
def client(tmp_path, aw_client):
    settings = Settings(db_path=tmp_path / "test.db", aw_url="http://aw.test", aw_timeout=1)
    with TestClient(create_app(settings, http_client=aw_client)) as c:
        yield c
