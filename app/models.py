"""SQLite storage for activity events and visited places."""

import sqlite3
from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS activity (
    id INTEGER PRIMARY KEY,
    source TEXT NOT NULL,
    start TEXT NOT NULL,
    duration_s REAL NOT NULL,
    app TEXT NOT NULL,
    title TEXT NOT NULL DEFAULT '',
    UNIQUE (source, start, app, title)
);
CREATE INDEX IF NOT EXISTS activity_start ON activity (start);

CREATE TABLE IF NOT EXISTS places (
    id INTEGER PRIMARY KEY,
    start TEXT NOT NULL,
    end TEXT NOT NULL,
    name TEXT NOT NULL,
    activity TEXT NOT NULL DEFAULT '',
    latitude REAL,
    longitude REAL,
    UNIQUE (start, name)
);
CREATE INDEX IF NOT EXISTS places_start ON places (start);
"""


@dataclass
class ActivityEvent:
    source: str
    start: datetime
    duration_s: float
    app: str
    title: str = ""


@dataclass
class Place:
    start: datetime
    end: datetime
    name: str
    activity: str = ""
    latitude: float | None = None
    longitude: float | None = None


def iso_utc(dt: datetime) -> str:
    """Normalise to a sortable UTC ISO string. Naive datetimes are treated as UTC."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC).isoformat(timespec="seconds")


def parse_iso(value: str) -> datetime:
    return datetime.fromisoformat(value)


def day_bounds(day: date) -> tuple[datetime, datetime]:
    """Start and end of a calendar day in the machine's local timezone, as aware datetimes."""
    start = datetime.combine(day, time.min).astimezone()
    end = datetime.combine(day + timedelta(days=1), time.min).astimezone()
    return start, end


def connect(path: Path | str) -> sqlite3.Connection:
    if str(path) != ":memory:":
        Path(path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    return conn


def insert_activity(conn: sqlite3.Connection, events: list[ActivityEvent]) -> int:
    """Insert events, ignoring ones already stored. Returns the number of new rows."""
    before = conn.total_changes
    conn.executemany(
        "INSERT OR IGNORE INTO activity (source, start, duration_s, app, title) VALUES (?, ?, ?, ?, ?)",
        [(e.source, iso_utc(e.start), e.duration_s, e.app, e.title) for e in events],
    )
    conn.commit()
    return conn.total_changes - before


def insert_places(conn: sqlite3.Connection, places: list[Place]) -> int:
    before = conn.total_changes
    conn.executemany(
        "INSERT OR IGNORE INTO places (start, end, name, activity, latitude, longitude) VALUES (?, ?, ?, ?, ?, ?)",
        [(iso_utc(p.start), iso_utc(p.end), p.name, p.activity, p.latitude, p.longitude) for p in places],
    )
    conn.commit()
    return conn.total_changes - before


def activity_for_day(conn: sqlite3.Connection, day: date) -> list[dict]:
    start, end = day_bounds(day)
    rows = conn.execute(
        "SELECT source, start, duration_s, app, title FROM activity WHERE start >= ? AND start < ? ORDER BY start",
        (iso_utc(start), iso_utc(end)),
    )
    return [dict(r) for r in rows]


def app_totals(events: list[dict]) -> list[dict]:
    totals: dict[str, float] = {}
    for e in events:
        totals[e["app"]] = totals.get(e["app"], 0.0) + e["duration_s"]
    return [{"app": a, "seconds": round(s)} for a, s in sorted(totals.items(), key=lambda kv: -kv[1])]


def places_for_day(conn: sqlite3.Connection, day: date) -> list[dict]:
    """Places whose visit overlaps the given local day."""
    start, end = day_bounds(day)
    rows = conn.execute(
        "SELECT start, end, name, activity, latitude, longitude FROM places WHERE start < ? AND end > ? ORDER BY start",
        (iso_utc(end), iso_utc(start)),
    )
    return [dict(r) for r in rows]
