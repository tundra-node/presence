from datetime import UTC, datetime

import httpx
import pytest

from app.imports.activitywatch import ActivityWatchError, fetch_window_events

START = datetime(2026, 6, 2, tzinfo=UTC)
END = datetime(2026, 6, 3, tzinfo=UTC)


def test_fetches_only_window_buckets_and_drops_zero_duration(aw_client):
    events = fetch_window_events("http://aw.test", START, END, client=aw_client)
    assert [e.app for e in events] == ["Code", "Firefox", "Code"]
    assert all(e.source == "activitywatch" for e in events)
    assert events[0].title == "presence"


def test_connection_error_is_wrapped():
    def boom(request):
        raise httpx.ConnectError("refused", request=request)

    client = httpx.Client(transport=httpx.MockTransport(boom))
    with pytest.raises(ActivityWatchError, match="Could not reach ActivityWatch"):
        fetch_window_events("http://aw.test", START, END, client=client)
