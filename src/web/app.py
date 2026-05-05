import os
import yaml
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pathlib import Path

from src.store.local_store import LocalStore

app = FastAPI(title="Idol Live Tracker PoC")

# Path setup
BASE_DIR = Path(__file__).resolve().parent.parent.parent
TEMPLATES_DIR = BASE_DIR / "templates" / "web"
STATIC_DIR = TEMPLATES_DIR / "static"
CONFIG_PATH = BASE_DIR / "config" / "artists.yaml"

# Mount static files
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# Templates setup
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

# Store setup
store = LocalStore(db_path=str(BASE_DIR / "data" / "events.db"))

def load_artists():
    if not CONFIG_PATH.exists():
        return []
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
    return config.get("artists", [])

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    artists = load_artists()
    return templates.TemplateResponse(
        request=request, name="index.html", context={"artists": artists}
    )

@app.get("/artist/{artist_id}", response_class=HTMLResponse)
async def artist_detail(request: Request, artist_id: str):
    artists = load_artists()
    artist = next((a for a in artists if a["name"] == artist_id), None)
    
    if not artist:
        raise HTTPException(status_code=404, detail="Artist not found")
    
    # Fetch upcoming events (next 90 days for the PoC)
    all_events = store.get_all()
    artist_events = [e for e in all_events if e.artist == artist_id]
    
    # Sort by date
    artist_events.sort(key=lambda x: x.date if x.date else x.date.max)
    
    return templates.TemplateResponse(
        request=request, name="detail.html", context={"artist": artist, "events": artist_events}
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
