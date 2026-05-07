import yaml
import asyncio
import uuid
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, BackgroundTasks
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from typing import Any
from pydantic import BaseModel

from src.store.local_store import LocalStore

app = FastAPI(title="Live Tracker API")

# --- Job Management ---

class JobManager:
    def __init__(self):
        self.active_jobs: dict[str, dict[str, Any]] = {}
        self.connections: dict[str, list[WebSocket]] = {}

    async def connect(self, job_id: str, websocket: WebSocket):
        await websocket.accept()
        if job_id not in self.connections:
            self.connections[job_id] = []
        self.connections[job_id].append(websocket)

    def disconnect(self, job_id: str, websocket: WebSocket):
        if job_id in self.connections:
            self.connections[job_id].remove(websocket)
            if not self.connections[job_id]:
                del self.connections[job_id]

    async def broadcast(self, job_id: str, message: dict):
        if job_id in self.connections:
            for connection in self.connections[job_id]:
                await connection.send_json(message)

job_manager = JobManager()

class ArtistCreatePayload(BaseModel):
    name: str
    display_name: str
    theme_color: str
    image_url: str
    base_url: str

async def create_artist_task(job_id: str, payload: ArtistCreatePayload):
    try:
        # 1. Start analysis
        await job_manager.broadcast(job_id, {"status": "processing", "message": f"Analyzing {payload.display_name}'s URL..."})
        await asyncio.sleep(2)  # Simulate analysis delay

        # 2. Update yaml
        config_path = Path(__file__).resolve().parent.parent.parent / "config" / "artists.yaml"
        if not config_path.exists():
            await job_manager.broadcast(job_id, {"status": "error", "message": "config/artists.yaml not found"})
            return

        with open(config_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        artists = data.get("artists", [])
        
        # 重複チェック
        if any(a.get("name") == payload.name for a in artists):
            await job_manager.broadcast(job_id, {"status": "error", "message": f"Artist ID '{payload.name}' already exists"})
            return

        # 新規アーティストを追加
        new_artist = {
            "name": payload.name,
            "display_name": payload.display_name,
            "theme_color": payload.theme_color,
            "image_url": payload.image_url,
            "base_url": payload.base_url,
            "fetch": {"dynamic": False},
            "navigation": {"type": "single_page", "range_months": 3},
            "selectors": {
                "event_list": "",
                "title": "",
                "date": "",
                "venue": "",
            }
        }
        artists.append(new_artist)

        # アトミックな書き換え (簡易版)
        with open(config_path, "w", encoding="utf-8") as f:
            yaml.dump(data, f, allow_unicode=True, default_flow_style=False, sort_keys=False)

        await job_manager.broadcast(job_id, {"status": "completed", "message": f"Successfully added {payload.display_name}!"})
    except Exception as e:
        await job_manager.broadcast(job_id, {"status": "error", "message": str(e)})

# --- End Job Management ---

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


@app.post("/api/artists/create")
async def create_artist(payload: ArtistCreatePayload, background_tasks: BackgroundTasks):
    job_id = str(uuid.uuid4())
    background_tasks.add_task(create_artist_task, job_id, payload)
    return {"job_id": job_id}


@app.websocket("/api/ws/jobs/{job_id}")
async def websocket_endpoint(websocket: WebSocket, job_id: str):
    await job_manager.connect(job_id, websocket)
    try:
        while True:
            # クライアントからのメッセージ待機（キープアライブ等）
            await websocket.receive_text()
    except WebSocketDisconnect:
        job_manager.disconnect(job_id, websocket)


@app.get("/api/admin/config/artists.yaml")
async def download_config():
    if not CONFIG_PATH.exists():
        raise HTTPException(status_code=404, detail="Config file not found")
    from fastapi.responses import FileResponse
    return FileResponse(CONFIG_PATH, media_type="application/x-yaml", filename="artists.yaml")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
