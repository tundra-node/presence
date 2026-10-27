"""Parser for Life Cycle (iOS) CSV exports.

Life Cycle's export columns have changed between versions, so headers are
matched loosely: case, spaces and punctuation are ignored, and several common
names are accepted for each field. A row needs a start, an end (or a duration)
and a place name. Timestamps in a column whose header mentions UTC are read as
UTC; other naive timestamps are read as local time.
"""

import csv
import io
import re
from datetime import UTC, datetime, timedelta

from app.models import Place

START_KEYS = ["startdateutc", "starttimeutc", "startutc", "startdate", "starttime", "start", "from"]
END_KEYS = ["enddateutc", "endtimeutc", "endutc", "enddate", "endtime", "end", "to"]
DURATION_KEYS = ["durations", "durationseconds", "duration"]
NAME_KEYS = ["displayname", "name", "place", "location", "placename", "title"]
ACTIVITY_KEYS = ["activity", "activityname", "category", "type"]
LAT_KEYS = ["latitude", "lat"]
LON_KEYS = ["longitude", "lon", "lng"]

DATE_FORMATS = [
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%d %H:%M",
    "%Y/%m/%d %H:%M:%S",
    "%Y/%m/%d %H:%M",
    "%m/%d/%Y %H:%M:%S",
    "%m/%d/%Y %H:%M",
    "%m/%d/%Y %I:%M %p",
    "%d.%m.%Y %H:%M:%S",
    "%d.%m.%Y %H:%M",
]


class LifeCycleError(ValueError):
    pass


def _norm(header: str) -> str:
    return re.sub(r"[^a-z0-9]", "", header.lower())


def _find(headers: dict[str, str], keys: list[str]) -> str | None:
    for key in keys:
        if key in headers:
            return headers[key]
    return None


def parse_datetime(value: str, assume_utc: bool) -> datetime:
    value = value.strip()
    try:
        dt = datetime.fromisoformat(value)
    except ValueError:
        for fmt in DATE_FORMATS:
            try:
                dt = datetime.strptime(value, fmt)
                break
            except ValueError:
                continue
        else:
            raise LifeCycleError(f"Unrecognised date: {value!r}")
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC) if assume_utc else dt.astimezone()
    return dt


def parse_duration(value: str) -> float:
    value = value.strip()
    if ":" in value:
        parts = [float(p) for p in value.split(":")]
        while len(parts) < 3:
            parts.insert(0, 0.0)
        h, m, s = parts[-3:]
        return h * 3600 + m * 60 + s
    return float(value)


def _float_or_none(value: str | None) -> float | None:
    if value is None or not value.strip():
        return None
    try:
        return float(value)
    except ValueError:
        return None


def parse_csv(text: str) -> list[Place]:
    text = text.lstrip("\ufeff")
    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames:
        raise LifeCycleError("CSV has no header row")
    headers = {_norm(h): h for h in reader.fieldnames if h}

    start_col = _find(headers, START_KEYS)
    end_col = _find(headers, END_KEYS)
    dur_col = _find(headers, DURATION_KEYS)
    name_col = _find(headers, NAME_KEYS)
    if not start_col or not name_col or not (end_col or dur_col):
        raise LifeCycleError(
            "CSV needs a start column, a name/location column, and an end or duration column. "
            f"Found: {', '.join(reader.fieldnames)}"
        )
    act_col = _find(headers, ACTIVITY_KEYS)
    lat_col = _find(headers, LAT_KEYS)
    lon_col = _find(headers, LON_KEYS)

    places = []
    for lineno, row in enumerate(reader, start=2):
        raw_start = (row.get(start_col) or "").strip()
        name = (row.get(name_col) or "").strip()
        if not raw_start or not name:
            continue
        try:
            start = parse_datetime(raw_start, "utc" in _norm(start_col))
            raw_end = (row.get(end_col) or "").strip() if end_col else ""
            if raw_end:
                end = parse_datetime(raw_end, "utc" in _norm(end_col))
            elif dur_col and (row.get(dur_col) or "").strip():
                end = start + timedelta(seconds=parse_duration(row[dur_col]))
            else:
                continue
        except (LifeCycleError, ValueError) as exc:
            raise LifeCycleError(f"Line {lineno}: {exc}") from exc
        if end < start:
            raise LifeCycleError(f"Line {lineno}: end is before start")
        places.append(
            Place(
                start=start,
                end=end,
                name=name,
                activity=(row.get(act_col) or "").strip() if act_col else "",
                latitude=_float_or_none(row.get(lat_col)) if lat_col else None,
                longitude=_float_or_none(row.get(lon_col)) if lon_col else None,
            )
        )
    return places
