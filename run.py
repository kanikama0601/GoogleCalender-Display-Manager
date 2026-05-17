#!/usr/bin/env python3
import argparse
import urllib.parse
from http.server import ThreadingHTTPServer
from src.backend.handler import Handler
from src.backend.services import (
    GOOGLE_API_AVAILABLE, DEFAULT_RSS_FEEDS, get_calendar_service
)

def main():
    ap = argparse.ArgumentParser(description="News Smart Monitor")
    ap.add_argument("--city",         default="高松市")
    ap.add_argument("--lat",          default=34.3401, type=float)
    ap.add_argument("--lon",          default=134.0434, type=float)
    ap.add_argument("--port",         default=8765, type=int)
    ap.add_argument("--rss",          nargs="*")
    ap.add_argument("--no-default-rss", action="store_true")
    ap.add_argument("--compact-clock", action="store_true")
    ap.add_argument("--compact-news",  action="store_true")
    ap.add_argument("--mouse-hide",    action="store_true")
    ap.add_argument("--wake-lock",     action="store_true")
    args = ap.parse_args()

    feeds = [] if args.no_default_rss else list(DEFAULT_RSS_FEEDS)
    if args.rss:
        for u in args.rss:
            feeds.append({"name": urllib.parse.urlparse(u).netloc, "url": u})

    Handler.config = {
        "city": args.city,
        "lat": args.lat,
        "lon": args.lon,
        "feeds": feeds,
        "compact_clock": args.compact_clock,
        "compact_news": args.compact_news,
        "mouse_hide": args.mouse_hide,
        "wake_lock": args.wake_lock
    }

    if GOOGLE_API_AVAILABLE:
        print("DEBUG: Pre-authenticating Google Calendar...")
        get_calendar_service()

    print(f"GoogleCalender Display Manager v1.1\nhttp://localhost:{args.port}")
    try:
        ThreadingHTTPServer(("", args.port), Handler).serve_forever()
    except KeyboardInterrupt:
        print("\nStopped")

if __name__ == "__main__":
    main()
