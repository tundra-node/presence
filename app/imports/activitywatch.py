"""Client for a local ActivityWatch server (https://activitywatch.net).

Only the REST API is used: list buckets, then pull events from every
`currentwindow` bucket for a time range.
"""

from datetime import datetime

import httpx

from app.models import ActivityEvent

WINDOW_BUCKET_TYPE = "currentwindow"


class ActivityWatchError(RuntimeError):
    pass


def parse_timestamp(value: str) -> datetime:
    # ActivityWatch emits e.g. "2026-06-02T14:03:11.123000+00:00" or a trailing "Z".
    return datetime.fromisoformat(value)


def window_buckets(client: httpx.Client, base_url: str) -> list[str]:
    resp = client.get(f"{base_url}/api/0/buckets/")
    resp.raise_for_status()
    buckets = resp.json()
    return sorted(bid for bid, b in buckets.items() if b.get("type") == WINDOW_BUCKET_TYPE)


def parse_events(raw: list[dict]) -> list[ActivityEvent]:
    events = []
    for item in raw:
        data = item.get("data") or {}
        duration = float(item.get("duration") or 0)
        if duration <= 0:
            continue
        events.append(
            ActivityEvent(
                source="activitywatch",
                start=parse_timestamp(item["timestamp"]),
                duration_s=duration,
                app=data.get("app") or "unknown",
                title=data.get("title") or "",
            )
        )
    return events


def fetch_window_events(
    base_url: str, start: datetime, end: datetime, client: httpx.Client | None = None, timeout: float = 10
) -> list[ActivityEvent]:
    owns_client = client is None
    client = client or httpx.Client(timeout=timeout)
    try:
        events: list[ActivityEvent] = []
        for bucket in window_buckets(client, base_url):
            resp = client.get(
                f"{base_url}/api/0/buckets/{bucket}/events",
                params={"start": start.isoformat(), "end": end.isoformat()},
            )
            resp.raise_for_status()
            events.extend(parse_events(resp.json()))
        return sorted(events, key=lambda e: e.start)
    except httpx.HTTPError as exc:
        raise ActivityWatchError(f"Could not reach ActivityWatch at {base_url}: {exc}") from exc
    finally:
        if owns_client:
            client.close()
