# Presence

> Your activity, location, mood, and habits — tracked locally, synced privately.

A personal time, location, and health tracker that replaces the need for multiple apps. Runs locally, syncs via Syncthing, and pulls data from:

- **Desktop activity** — via ActivityWatch (cross-platform, per-window/app)
- **Browser tabs** — via a Chrome extension
- **Location history** — via Life Cycle app CSV exports (iOS)
- **Calendar & mood** — manual daily check-ins, integrated with Obsidian vault

Long-term goal: a fully online personal analytics dashboard that learns your patterns and helps plan your day.

## Phases

### Phase 1 — MVP (local, single-user)
- ActivityWatch integration — shows today's tracked apps and windows
- Life Cycle import — upload CSV, see where you've been
- Simple FastAPI dashboard with today's timeline
- SQLite storage

### Phase 2 — Browser extension
- Chrome extension sends active tab URL to Presence API
- Combines desktop + web activity in one timeline

### Phase 3 — Health vault
- Daily check-in form (mood, sleep, habits)
- Calendar integration from Obsidian vault
- Combined timeline: screen time + location + mood + calendar

### Phase 4 — Patterns
- "You usually spend 45 min on FBLA study" → auto-schedule
- Insights on when you're most productive, what drains you

## Stack
- **Backend:** Python, FastAPI, SQLite
- **Frontend:** Vanilla JS, HTML/CSS
- **Desktop tracking:** ActivityWatch (open source)
- **Phone tracking:** Life Cycle app → CSV import
- **Sync:** Syncthing (now) → hosted server (later)

## Structure
```
Presence/
├── app/
│   ├── main.py            # FastAPI app, CORS, static mount
│   ├── models.py          # SQLite models and schemas
│   ├── routes/
│   │   └── api.py         # API endpoints
│   ├── imports/
│   │   ├── activitywatch.py  # ActivityWatch API client
│   │   └── lifecycle.py      # Life Cycle CSV parser
│   └── static/
│       └── index.html     # Dashboard frontend
├── data/                  # SQLite DB, imports, config
├── tests/
├── requirements.txt
└── README.md
```
