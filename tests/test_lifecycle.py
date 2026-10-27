from datetime import UTC

import pytest

from app.imports.lifecycle import LifeCycleError, parse_csv, parse_duration

UTC_EXPORT = """\ufeffSTART DATE(UTC),END DATE(UTC),DURATION(s),NAME,ACTIVITY,LATITUDE,LONGITUDE
2026-06-02 12:00:00,2026-06-02 15:30:00,12600,School,Work,40.1,-75.2
2026-06-02 16:00:00,,1800,Gym,Exercise,,
,2026-06-02 17:00:00,60,Ignored,,,
"""


def test_parses_utc_columns_and_duration_fallback():
    places = parse_csv(UTC_EXPORT)
    assert [p.name for p in places] == ["School", "Gym"]
    school, gym = places
    assert school.start.tzinfo is not None
    assert school.start.astimezone(UTC).hour == 12
    assert (school.end - school.start).total_seconds() == 12600
    assert school.activity == "Work"
    assert school.latitude == pytest.approx(40.1)
    assert (gym.end - gym.start).total_seconds() == 1800
    assert gym.latitude is None


def test_local_time_headers_and_us_dates():
    text = "Start,End,Location\n06/02/2026 9:00 AM,06/02/2026 10:15 AM,Home\n"
    (place,) = parse_csv(text)
    assert place.start.hour == 9
    assert place.start.utcoffset() is not None
    assert (place.end - place.start).total_seconds() == 75 * 60


def test_missing_columns_is_an_error():
    with pytest.raises(LifeCycleError, match="start column"):
        parse_csv("foo,bar\n1,2\n")


def test_bad_date_reports_line():
    with pytest.raises(LifeCycleError, match="Line 3"):
        parse_csv("start,end,name\n2026-06-02 10:00,2026-06-02 11:00,A\nnope,2026-06-02 11:00,B\n")


def test_end_before_start_rejected():
    with pytest.raises(LifeCycleError, match="before start"):
        parse_csv("start,end,name\n2026-06-02 10:00,2026-06-02 09:00,A\n")


@pytest.mark.parametrize("raw,seconds", [("90", 90), ("1:30", 90), ("01:02:03", 3723)])
def test_parse_duration(raw, seconds):
    assert parse_duration(raw) == seconds
