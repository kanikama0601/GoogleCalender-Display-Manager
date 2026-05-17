import os
import json
import urllib.parse
import subprocess
from http.server import BaseHTTPRequestHandler
from .services import (
    fetch_weather, fetch_rss, fetch_calendar_events,
    images_list, music_tree, load_commands
)

class Handler(BaseHTTPRequestHandler):
    config = {}
    
    def log_message(self, *a): pass

    def do_GET(self):
        p = self.path.split("?")[0]
        if   p == "/":               self._html()
        elif p == "/api/weather":    self._json(fetch_weather(self.config["lat"],self.config["lon"],self.config["city"]))
        elif p == "/api/news":       self._json([fetch_rss(f["url"],f["name"]) for f in self.config["feeds"]])
        elif p == "/api/calendar":
            query = urllib.parse.parse_qs(self.path.split("?")[1]) if "?" in self.path else {}
            days = int(query.get("days", [1])[0])
            start_offset = int(query.get("start_offset", [0])[0])
            self._json(fetch_calendar_events(days, start_offset))
        elif p == "/api/images":     self._json(images_list())
        elif p == "/api/music":      self._json(music_tree())
        elif p == "/api/commands":   self._json(load_commands())
        elif p.startswith("/images/"): self._img(p)
        elif p.startswith("/music/"):  self._stream_music(p)
        elif p.startswith("/css/") or p.startswith("/js/"):
            self._static(p)
        else: self.send_error(404)

    def do_POST(self):
        p = self.path.split("?")[0]
        if p == "/api/run":
            length = int(self.headers.get("Content-Length", 0))
            body   = self.rfile.read(length)
            try:
                data = json.loads(body)
                cmd  = data.get("cmd", "").strip()
                if not cmd:
                    self._json({"ok": False, "error": "empty command"})
                    return
                subprocess.Popen(
                    cmd, shell=True,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    cwd=os.getcwd(),
                )
                self._json({"ok": True})
            except Exception as e:
                self._json({"ok": False, "error": str(e)})
        else:
            self.send_error(404)

    def _static(self, p):
        """Serve static files from src/frontend"""
        safe_path = p.lstrip("/")
        fp = os.path.join(os.getcwd(), "src", "frontend", safe_path)
        if not os.path.isfile(fp):
            self.send_error(404)
            return
        
        ext = os.path.splitext(fp)[1].lower()
        mime = {
            ".css": "text/css",
            ".js": "application/javascript",
            ".png": "image/png",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
        }.get(ext, "application/octet-stream")
        
        with open(fp, "rb") as f:
            body = f.read()
        
        self.send_response(200)
        self.send_header("Content-Type", mime)
        self.send_header("Content-Length", len(body))
        self.end_headers()
        self.wfile.write(body)

    def _stream_music(self, url_path):
        rel = urllib.parse.unquote(url_path[len("/music/"):])
        music_dir = os.path.realpath(os.path.join(os.getcwd(), "data", "music"))
        fp = os.path.realpath(os.path.join(music_dir, rel))
        if not fp.startswith(music_dir) or not os.path.isfile(fp):
            self.send_error(404)
            return
        ext = os.path.splitext(fp)[1].lower()
        mime = {".mp3":"audio/mpeg", ".flac":"audio/flac", ".wav":"audio/wav",
                ".ogg":"audio/ogg", ".m4a":"audio/mp4", ".aac":"audio/aac",
                ".opus":"audio/ogg"}.get(ext, "application/octet-stream")
        fsize = os.path.getsize(fp)
        range_hdr = self.headers.get("Range", "")
        start, end = 0, fsize - 1
        if range_hdr.startswith("bytes="):
            parts = range_hdr[6:].split("-")
            try:
                start = int(parts[0]) if parts[0] else 0
                end   = int(parts[1]) if len(parts) > 1 and parts[1] else fsize - 1
            except ValueError:
                pass
        length = end - start + 1
        with open(fp, "rb") as f:
            f.seek(start)
            body = f.read(length)
        code = 206 if range_hdr else 200
        self.send_response(code)
        self.send_header("Content-Type", mime)
        self.send_header("Content-Length", str(length))
        self.send_header("Content-Range", f"bytes {start}-{end}/{fsize}")
        self.send_header("Accept-Ranges", "bytes")
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        self.wfile.write(body)

    def _img(self, p):
        d = os.path.join(os.getcwd(), "data", "images")
        fn = os.path.basename(p)
        fp = os.path.join(d, fn)
        if not os.path.isfile(fp): self.send_error(404); return
        mime = {".png":"image/png",".jpg":"image/jpeg",".jpeg":"image/jpeg",
                ".webp":"image/webp",".gif":"image/gif"}.get(os.path.splitext(fn)[1].lower(),"application/octet-stream")
        with open(fp, "rb") as f:
            body = f.read()
        self.send_response(200)
        self.send_header("Content-Type", mime)
        self.send_header("Content-Length", len(body))
        self.send_header("Cache-Control","max-age=3600")
        self.end_headers(); self.wfile.write(body)

    def _json(self, data):
        body = json.dumps(data, ensure_ascii=False).encode()
        self.send_response(200)
        self.send_header("Content-Type","application/json; charset=utf-8")
        self.send_header("Content-Length", len(body))
        self.send_header("Access-Control-Allow-Origin","*")
        self.end_headers(); self.wfile.write(body)

    def _html(self):
        fp = os.path.join(os.getcwd(), "src", "frontend", "index.html")
        if not os.path.isfile(fp):
            self.send_error(404)
            return
        with open(fp, encoding="utf-8") as f:
            html = f.read()
        inject = (
            f'<script>window.MONITOR_CONFIG='
            f'{{"compactClock":{str(self.config.get("compact_clock",False)).lower()},'
            f'"compactNews":{str(self.config.get("compact_news",False)).lower()},'
            f'"mouseHide":{str(self.config.get("mouse_hide",False)).lower()},'
            f'"wakeLock":{str(self.config.get("wake_lock",False)).lower()}}};</script>'
        )
        html = html.replace("</head>", inject + "</head>", 1)
        body = html.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type","text/html; charset=utf-8")
        self.send_header("Content-Length", len(body))
        self.end_headers(); self.wfile.write(body)
