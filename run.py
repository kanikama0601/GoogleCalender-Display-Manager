#!/usr/bin/env python3
"""
Hiroba News Smart Monitor - run.py
Usage: python run.py [--city CITY] [--lat LAT] [--lon LON] [--port PORT] [--rss URL ...]
"""

import argparse, json, urllib.request, urllib.parse
import xml.etree.ElementTree as ET
from http.server import HTTPServer, BaseHTTPRequestHandler, ThreadingHTTPServer
from datetime import datetime, timedelta
import threading, time, os, re

# Google Calendar API imports
try:
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build
    GOOGLE_API_AVAILABLE = True
    print("DEBUG: Google API libraries loaded successfully.")
except ImportError as e:
    GOOGLE_API_AVAILABLE = False
    print(f"DEBUG: Google API libraries failed to load: {e}")

SCOPES = ['https://www.googleapis.com/auth/calendar.readonly']

DEFAULT_RSS_FEEDS = [
    {"name": "NHK 主要",        "url": "https://www3.nhk.or.jp/rss/news/cat0.xml"},
    {"name": "BBC 日本語",      "url": "https://feeds.bbci.co.uk/japanese/rss.xml"},
    {"name": "CNN Japan",       "url": "https://feeds.cnn.co.jp/rss/cnn/cnn.rdf"},
    {"name": "Google News JP",  "url": "https://news.google.com/rss?hl=ja&gl=JP&ceid=JP:ja"},
    {"name": "GIGAZINE",        "url": "https://gigazine.net/news/rss_2.0/"},
    {"name": "ITmedia",         "url": "https://rss.itmedia.co.jp/rss/2.0/itmediatopstory.xml"},
]

_cache = {}
_lock  = threading.Lock()
CACHE_TTL = 300

def cache_get(k):
    with _lock:
        e = _cache.get(k)
        if e and time.time() - e["ts"] < CACHE_TTL:
            return e["data"]
    return None

def cache_set(k, v):
    with _lock:
        _cache[k] = {"ts": time.time(), "data": v}

def get_calendar_service():
    if not GOOGLE_API_AVAILABLE:
        print("DEBUG: GOOGLE_API_AVAILABLE is False.")
        return None
    creds = None
    if os.path.exists('token.json'):
        print("DEBUG: Loading credentials from token.json")
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            print("DEBUG: Refreshing expired credentials")
            creds.refresh(Request())
        else:
            if not os.path.exists('credentials.json'):
                print("DEBUG: credentials.json not found.")
                return None
            print("DEBUG: Starting local server for authentication...")
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        with open('token.json', 'w') as token:
            token.write(creds.to_json())
    return build('calendar', 'v3', credentials=creds)

def fetch_calendar_events(days=1):
    key = f"calendar_{days}"
    if c := cache_get(key): return c
    
    service = get_calendar_service()
    if not service:
        return {"error": "Google Calendar credentials not found or API not initialized."}

    try:
        from datetime import timezone as tz
        jst = tz(timedelta(hours=9))
        now_jst = datetime.now(jst)
        
        if days == 1:
            # Strictly today (JST)
            start = now_jst.replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
            end = now_jst.replace(hour=23, minute=59, second=59, microsecond=999999).isoformat()
        else:
            start = now_jst.isoformat()
            end = (now_jst + timedelta(days=days)).isoformat()
        
        events_result = service.events().list(calendarId='primary', timeMin=start,
                                              timeMax=end, singleEvents=True,
                                              orderBy='startTime').execute()
        events = events_result.get('items', [])
        
        result = []
        for event in events:
            start = event['start'].get('dateTime', event['start'].get('date'))
            end_ev = event['end'].get('dateTime', event['end'].get('date'))
            result.append({
                "summary": event.get('summary', '(No title)'),
                "start": start,
                "end": end_ev,
                "location": event.get('location', ''),
                "description": event.get('description', '')
            })
        
        cache_set(key, result)
        return result
    except Exception as e:
        print(f"DEBUG: Error fetching calendar events: {e}")
        return {"error": str(e)}

def fetch_weather(lat, lon, city):
    key = f"wx_{lat}_{lon}"
    if c := cache_get(key): return c
    try:
        url = (f"https://api.open-meteo.com/v1/forecast"
               f"?latitude={lat}&longitude={lon}"
               f"&current=temperature_2m,apparent_temperature,weather_code,"
               f"wind_speed_10m,relative_humidity_2m,precipitation"
               f"&hourly=temperature_2m,weather_code"
               f"&daily=weather_code,temperature_2m_max,temperature_2m_min,precipitation_sum"
               f"&timezone=Asia%2FTokyo&forecast_days=7")
        with urllib.request.urlopen(url, timeout=8) as r:
            data = json.loads(r.read())

        WMO = {0:"快晴", 1:"晴れ", 2:"時々曇り", 3:"曇り",
               45:"霧", 48:"霧氷", 51:"霧雨(弱)", 53:"霧雨", 55:"霧雨(強)",
               56:"氷雨(弱)", 57:"氷雨", 61:"小雨", 63:"雨", 65:"大雨",
               66:"凍雨(小)", 67:"凍雨", 71:"小雪", 73:"雪", 75:"大雪",
               77:"ひょう", 80:"にわか雨", 81:"雨", 82:"激しい雨",
               85:"雪(弱)", 86:"雪(強)", 95:"雷雨", 96:"雷雨(雹)", 99:"猛烈な雷雨"}
        ICO = {0:"☀️", 1:"🌤", 2:"⛅", 3:"☁️", 45:"🌫", 48:"🌫",
               51:"🌦", 53:"🌦", 55:"🌧", 56:"🌨", 57:"🌨",
               61:"🌧", 63:"🌧", 65:"🌧", 66:"🌨", 67:"🌨",
               71:"🌨", 73:"❄️", 75:"❄️", 77:"🌨",
               80:"🌦", 81:"🌧", 82:"⛈", 85:"🌨", 86:"❄️",
               95:"⛈", 96:"⛈", 99:"⛈"}

        cur    = data["current"]
        code   = cur["weather_code"]
        daily  = data["daily"]
        hourly = data["hourly"]

        forecast = []
        for i in range(min(7, len(daily["time"]))):
            dc = daily["weather_code"][i]
            forecast.append({"date":daily["time"][i],"code":dc,
                              "icon":ICO.get(dc,"🌡"),"desc":WMO.get(dc,"不明"),
                              "max":round(daily["temperature_2m_max"][i],1),
                              "min":round(daily["temperature_2m_min"][i],1),
                              "precip":round(daily["precipitation_sum"][i],1)})

        hourly_data = []
        # Force JST for date matching
        from datetime import timezone as tz
        jst = tz(timedelta(hours=9))
        today_str = datetime.now(jst).strftime("%Y-%m-%d")

        for i in range(len(hourly["time"])):
            t_str = hourly["time"][i]
            # Only today
            if not t_str.startswith(today_str): continue
            
            h = int(t_str[11:13])
            # Only 8:00 to 20:00 AND every 2 hours
            if 8 <= h <= 20 and h % 2 == 0:
                hc = hourly["weather_code"][i]
                hourly_data.append({
                    "time": t_str[11:16],
                    "temp": round(hourly["temperature_2m"][i], 1),
                    "icon": ICO.get(hc, "🌡")
                })
        
        # Only take the 7 slots for today (8,10,12,14,16,18,20)
        hourly_data = hourly_data[:7]

        result = {"city":city,"temp":round(cur["temperature_2m"],1),
                  "feels":round(cur["apparent_temperature"],1),"code":code,
                  "icon":ICO.get(code,"🌡"),"desc":WMO.get(code,"不明"),
                  "wind":round(cur["wind_speed_10m"],1),
                  "humidity":cur["relative_humidity_2m"],
                  "precip":cur.get("precipitation",0),
                  "forecast":forecast,"hourly":hourly_data}
        cache_set(key, result)
        return result
    except Exception as e:
        return {"error":str(e),"city":city}

def fetch_rss(url, name, limit=20):
    key = f"rss_{url}"
    if c := cache_get(key): return c
    try:
        req = urllib.request.Request(url, headers={"User-Agent":"NewsMonitor/2.0"})
        with urllib.request.urlopen(req, timeout=8) as r:
            raw = r.read()
        root = ET.fromstring(raw)
        items = []

        for item in root.findall(".//item")[:limit]:
            title = item.findtext("title","").strip()
            link  = item.findtext("link","").strip()
            desc  = re.sub(r"<[^>]+>","",item.findtext("description",""))[:140].strip()
            pub   = item.findtext("pubDate","").strip()
            if title: items.append({"title":title,"link":link,"desc":desc,"pub":pub})

        if not items:
            ns = "http://www.w3.org/2005/Atom"
            for e in root.findall(f"{{{ns}}}entry")[:limit]:
                title = e.findtext(f"{{{ns}}}title","").strip()
                lel   = e.find(f"{{{ns}}}link")
                link  = lel.get("href","") if lel is not None else ""
                summ  = re.sub(r"<[^>]+>","",e.findtext(f"{{{ns}}}summary",""))[:140].strip()
                upd   = e.findtext(f"{{{ns}}}updated","")
                if title: items.append({"title":title,"link":link,"desc":summ,"pub":upd})

        res = {"name":name,"url":url,"items":items}
        cache_set(key, res)
        return res
    except Exception as e:
        return {"name":name,"url":url,"items":[],"error":str(e)}

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
            self._json(fetch_calendar_events(days))
        elif p == "/api/images":     self._json(self._imgs())
        elif p == "/api/music":      self._json(self._music_tree())
        elif p == "/api/commands":   self._json(self._load_commands())
        elif p.startswith("/images/"): self._img(p)
        elif p.startswith("/music/"):  self._stream_music(p)
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
                # 別プロセスで起動（非同期・stdout/stderrは捨てる）
                import subprocess
                subprocess.Popen(
                    cmd, shell=True,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    cwd=os.path.dirname(__file__),
                )
                self._json({"ok": True})
            except Exception as e:
                self._json({"ok": False, "error": str(e)})
        else:
            self.send_error(404)

    def _load_commands(self):
        """commands.json を読み込んで返す。なければ空リスト。"""
        fp = os.path.join(os.path.dirname(__file__), "commands.json")
        if not os.path.isfile(fp):
            return []
        try:
            with open(fp, encoding="utf-8") as f:
                data = json.load(f)
            # cmd が配列なら改行結合して文字列に統一
            for item in data:
                if isinstance(item.get("cmd"), list):
                    item["cmd"] = "\n".join(item["cmd"])
            return data
        except Exception as e:
            return [{"name": f"⚠ commands.json 読み込みエラー: {e}", "cmd": ""}]

    def _music_tree(self):
        """musicフォルダを再帰的に走査してツリー構造を返す"""
        music_dir = os.path.join(os.path.dirname(__file__), "music")
        if not os.path.isdir(music_dir):
            return []
        AUDIO_EXT = {".mp3", ".flac", ".wav", ".ogg", ".m4a", ".aac", ".opus"}

        def scan(path, rel=""):
            entries = []
            try:
                items = sorted(os.listdir(path))
            except PermissionError:
                return entries
            for name in items:
                full = os.path.join(path, name)
                rel_path = (rel + "/" + name).lstrip("/")
                if os.path.isdir(full):
                    children = scan(full, rel_path)
                    if children:
                        entries.append({"type": "dir", "name": name, "path": rel_path, "children": children})
                elif os.path.isfile(full):
                    ext = os.path.splitext(name)[1].lower()
                    if ext in AUDIO_EXT:
                        entries.append({"type": "file", "name": name, "path": rel_path, "url": "/music/" + rel_path})
            return entries

        return scan(music_dir)

    def _stream_music(self, url_path):
        """音楽ファイルをRange対応でストリーミング配信"""
        # URLデコード
        rel = urllib.parse.unquote(url_path[len("/music/"):])
        # パストラバーサル防止
        music_dir = os.path.realpath(os.path.join(os.path.dirname(__file__), "music"))
        fp = os.path.realpath(os.path.join(music_dir, rel))
        if not fp.startswith(music_dir) or not os.path.isfile(fp):
            self.send_error(404)
            return
        ext = os.path.splitext(fp)[1].lower()
        mime = {".mp3":"audio/mpeg", ".flac":"audio/flac", ".wav":"audio/wav",
                ".ogg":"audio/ogg", ".m4a":"audio/mp4", ".aac":"audio/aac",
                ".opus":"audio/ogg"}.get(ext, "application/octet-stream")
        fsize = os.path.getsize(fp)
        # Range リクエスト対応
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

    def _imgs(self):
        d = os.path.join(os.path.dirname(__file__),"images")
        if not os.path.isdir(d): return []
        ext = {".png",".jpg",".jpeg",".webp",".gif"}
        return ["/images/"+f for f in sorted(os.listdir(d)) if os.path.splitext(f)[1].lower() in ext]

    def _img(self, p):
        d = os.path.join(os.path.dirname(__file__),"images")
        fn = os.path.basename(p)
        fp = os.path.join(d, fn)
        if not os.path.isfile(fp): self.send_error(404); return
        mime = {".png":"image/png",".jpg":"image/jpeg",".jpeg":"image/jpeg",
                ".webp":"image/webp",".gif":"image/gif"}.get(os.path.splitext(fn)[1].lower(),"application/octet-stream")
        body = open(fp,"rb").read()
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
        fp = os.path.join(os.path.dirname(__file__),"index.html")
        html = open(fp, encoding="utf-8").read()
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

def main():
    ap = argparse.ArgumentParser(description="News Smart Monitor")
    ap.add_argument("--city",         default="東京都")
    ap.add_argument("--lat",          default=35.6895, type=float)
    ap.add_argument("--lon",          default=139.6917, type=float)
    ap.add_argument("--port",         default=8765, type=int)
    ap.add_argument("--rss",          nargs="*")
    ap.add_argument("--no-default-rss", action="store_true")
    ap.add_argument("--compact-clock", action="store_true",
                    help="Reduce clock font size (useful on small/Linux displays)")
    ap.add_argument("--compact-news",  action="store_true",
                    help="Show only news titles; click to expand detail + link")
    ap.add_argument("--mouse-hide",    action="store_true",
                    help="Hide mouse cursor (for touch-only displays)")
    ap.add_argument("--wake-lock",     action="store_true",
                    help="Use WakeLock API to prevent screen from sleeping (Chrome/Edge/Safari)")
    args = ap.parse_args()

    feeds = [] if args.no_default_rss else list(DEFAULT_RSS_FEEDS)
    if args.rss:
        for u in args.rss:
            feeds.append({"name": urllib.parse.urlparse(u).netloc, "url": u})

    Handler.config = {"city":args.city,"lat":args.lat,"lon":args.lon,"feeds":feeds,
                      "compact_clock": args.compact_clock,
                      "compact_news":  args.compact_news,
                      "mouse_hide":    args.mouse_hide,
                      "wake_lock":     args.wake_lock}

    # Pre-auth Google Calendar to ensure browser opens immediately
    if GOOGLE_API_AVAILABLE:
        print("DEBUG: Pre-authenticating Google Calendar...")
        get_calendar_service()

    print(f"Hiroba News Smart Monitor v1.1\nhttp://localhost:{args.port}")
    try:
        ThreadingHTTPServer(("", args.port), Handler).serve_forever()
    except KeyboardInterrupt:
        print("\nStopped")

if __name__ == "__main__":
    main()
