from src.analyzer.site_analyzer import capture_page
import sys

url = "https://www.baystars.co.jp/game/schedule/2026"
try:
    print(f"Capturing {url}...")
    html, logs = capture_page(url)
    print(f"Success! HTML length: {len(html)}, Logs: {len(logs)}")
except Exception as e:
    print(f"Failed: {e}")
    sys.exit(1)
