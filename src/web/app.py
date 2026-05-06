import yaml
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from typing import Any

from src.store.local_store import LocalStore

app = FastAPI(title="Live Tracker API")

BASE_DIR = Path(__file__).resolve().parent.parent.parent
CONFIG_PATH = BASE_DIR / "config" / "artists.yaml"
IMG_DIR = BASE_DIR / "frontend" / "public" / "img"

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

if IMG_DIR.exists():
    app.mount("/img", StaticFiles(directory=str(IMG_DIR)), name="img")

store = LocalStore(db_path=str(BASE_DIR / "data" / "events.db"))


def load_artists() -> list[dict[str, Any]]:
    if not CONFIG_PATH.exists():
        return []
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
    artists = config.get("artists", [])
    for artist in artists:
        name = artist.get("name")
        if name and (IMG_DIR / f"{name}.jpg").exists():
            artist["image_url"] = f"/img/{name}.jpg"
    return artists


def _serialize_event(event: Any, extra: dict | None = None) -> dict:
    return {
        "title": event.title,
        "artist": event.artist,
        "date": event.date.isoformat() if event.date else None,
        "start_time": event.start_time or None,
        "venue": event.venue or None,
        "ticket_url": event.ticket_url or None,
        "source_url": event.source_url or None,
        "fetch_status": event.fetch_status,
        **(extra or {}),
    }


@app.get("/api/artists")
async def get_artists():
    return load_artists()


@app.get("/api/artists/{artist_id}/events")
async def get_artist_events(artist_id: str):
    artists = load_artists()
    artist = next((a for a in artists if a["name"] == artist_id), None)
    if not artist:
        raise HTTPException(status_code=404, detail="Artist not found")

    all_events = store.get_all()
    artist_events = [e for e in all_events if e.artist == artist_id]
    artist_events.sort(key=lambda x: (x.date is None, str(x.date) if x.date else ""))

    return [_serialize_event(e) for e in artist_events]


@app.get("/api/events")
async def get_all_events():
    artists = load_artists()
    artist_map = {a["name"]: a for a in artists}
    all_events = store.get_all()

    result = []
    for event in all_events:
        info = artist_map.get(event.artist, {})
        result.append(
            _serialize_event(
                event,
                extra={
                    "display_name": info.get("display_name", event.artist),
                    "theme_color": info.get("theme_color", "#888888"),
                    "image_url": info.get("image_url", ""),
                },
            )
        )

    result.sort(key=lambda x: (x["date"] is None, x["date"] or ""))
    return result


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
