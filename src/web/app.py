import os
import yaml
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from typing import List, Dict, Any

from src.store.local_store import LocalStore

app = FastAPI(title="Idol Live Tracker API")

# Path setup
BASE_DIR = Path(__file__).resolve().parent.parent.parent
CONFIG_PATH = BASE_DIR / "config" / "artists.yaml"
IMG_DIR = BASE_DIR / "frontend" / "public" / "img"

# Enable CORS for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all for PoC to avoid port issues
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount images directory
if IMG_DIR.exists():
    app.mount("/img", StaticFiles(directory=str(IMG_DIR)), name="img")

# Store setup
store = LocalStore(db_path=str(BASE_DIR / "data" / "events.db"))

def load_artists() -> List[Dict[str, Any]]:
    if not CONFIG_PATH.exists():
        return []
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
    artists = config.get("artists", [])
    
    # Ensure image_url points to our local /img endpoint if not already
    for artist in artists:
        name = artist.get("name")
        if name and (IMG_DIR / f"{name}.png").exists():
            artist["image_url"] = f"/img/{name}.png"
            
    return artists

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
    
    # Sort by date (descending for history, or ascending for upcoming - here we return all)
    artist_events.sort(key=lambda x: x.date if x.date else x.date.max)
    
    return artist_events

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
