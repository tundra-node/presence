"""JSON API used by the dashboard."""

from datetime import date

from fastapi import APIRouter, HTTPException, Request, UploadFile

from app import models
from app.imports import activitywatch, lifecycle

router = APIRouter(prefix="/api")

MAX_UPLOAD_BYTES = 20 * 1024 * 1024


def _day(value: date | None) -> date:
    return value or date.today()


@router.get("/health")
def health() -> dict:
    return {"ok": True}


@router.post("/sync/activitywatch")
def sync_activitywatch(request: Request, day: date | None = None) -> dict:
    settings = request.app.state.settings
    start, end = models.day_bounds(_day(day))
    try:
        events = activitywatch.fetch_window_events(
            settings.aw_url, start, end, client=request.app.state.http_client, timeout=settings.aw_timeout
        )
    except activitywatch.ActivityWatchError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    added = models.insert_activity(request.app.state.db, events)
    return {"fetched": len(events), "added": added}


@router.get("/activity")
def activity(request: Request, day: date | None = None) -> dict:
    events = models.activity_for_day(request.app.state.db, _day(day))
    return {"day": _day(day).isoformat(), "events": events, "apps": models.app_totals(events)}


@router.post("/import/lifecycle")
async def import_lifecycle(request: Request, file: UploadFile) -> dict:
    raw = await file.read(MAX_UPLOAD_BYTES + 1)
    if len(raw) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="File too large (20 MB max)")
    try:
        text = raw.decode("utf-8-sig")
        places = lifecycle.parse_csv(text)
    except UnicodeDecodeError as exc:
        raise HTTPException(status_code=400, detail="File is not UTF-8 text") from exc
    except lifecycle.LifeCycleError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    added = models.insert_places(request.app.state.db, places)
    return {"parsed": len(places), "added": added}


@router.get("/places")
def places(request: Request, day: date | None = None) -> dict:
    return {"day": _day(day).isoformat(), "places": models.places_for_day(request.app.state.db, _day(day))}


@router.get("/timeline")
def timeline(request: Request, day: date | None = None) -> dict:
    """Activity and places for one day merged into a single list sorted by start time."""
    db = request.app.state.db
    items = [
        {"kind": "app", "start": e["start"], "seconds": round(e["duration_s"]), "label": e["app"], "detail": e["title"]}
        for e in models.activity_for_day(db, _day(day))
    ]
    for p in models.places_for_day(db, _day(day)):
        seconds = (models.parse_iso(p["end"]) - models.parse_iso(p["start"])).total_seconds()
        items.append(
            {
                "kind": "place",
                "start": p["start"],
                "seconds": round(seconds),
                "label": p["name"],
                "detail": p["activity"],
            }
        )
    items.sort(key=lambda i: i["start"])
    return {"day": _day(day).isoformat(), "items": items}
