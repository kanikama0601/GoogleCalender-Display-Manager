import os
import json
import re
import threading
import time
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone as tz
from .utils import cache_get, cache_set

# Google Calendar API imports
try:
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build
    GOOGLE_API_AVAILABLE = True
except ImportError:
    GOOGLE_API_AVAILABLE = False

SCOPES = ['https://www.googleapis.com/auth/calendar.readonly']

DEFAULT_RSS_FEEDS = [
    {"name": "NHK 主要",        "url": "https://www3.nhk.or.jp/rss/news/cat0.xml"},
    {"name": "BBC 日本語",      "url": "https://feeds.bbci.co.uk/japanese/rss.xml"},
    {"name": "CNN Japan",       "url": "https://feeds.cnn.co.jp/rss/cnn/cnn.rdf"},
    {"name": "Google News JP",  "url": "https://news.google.com/rss?hl=ja&gl=JP&ceid=JP:ja"},
    {"name": "GIGAZINE",        "url": "https://gigazine.net/news/rss_2.0/"},
    {"name": "ITmedia",         "url": "https://rss.itmedia.co.jp/rss/2.0/itmediatopstory.xml"},
]

def get_calendar_service():
    if not GOOGLE_API_AVAILABLE:
        return None
    creds = None
    # Assuming data directory is at the root
    data_dir = os.path.join(os.getcwd(), 'data')
    token_path = os.path.join(data_dir, 'token.json')
    creds_path = os.path.join(data_dir, 'credentials.json')
    
    if os.path.exists(token_path):
        creds = Credentials.from_authorized_user_file(token_path, SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists(creds_path):
                return None
            flow = InstalledAppFlow.from_client_secrets_file(creds_path, SCOPES)
            creds = flow.run_local_server(port=0)
        os.makedirs(data_dir, exist_ok=True)
        with open(token_path, 'w') as token:
            token.write(creds.to_json())
    return build('calendar', 'v3', credentials=creds)

def fetch_calendar_events(days=1, start_offset=0):
    key = f"calendar_{days}_{start_offset}"
    if c := cache_get(key): return c
    
    service = get_calendar_service()
    if not service:
        return {"error": "Google Calendar credentials not found or API not initialized."}

    try:
        jst = tz(timedelta(hours=9))
        now_jst = datetime.now(jst)
        
        if days == 1 and start_offset == 0:
            start = now_jst.replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
            end = now_jst.replace(hour=23, minute=59, second=59, microsecond=999999).isoformat()
        else:
            start = (now_jst + timedelta(days=start_offset)).isoformat()
            end = (now_jst + timedelta(days=start_offset + days)).isoformat()
        
        events_result = service.events().list(calendarId='primary', timeMin=start,
                                              timeMax=end, singleEvents=True,
                                              orderBy='startTime').execute()
        events = events_result.get('items', [])
        
        result = []
        for event in events:
            start_ev = event['start'].get('dateTime', event['start'].get('date'))
            end_ev = event['end'].get('dateTime', event['end'].get('date'))
            result.append({
                "summary": event.get('summary', '(No title)'),
                "start": start_ev,
                "end": end_ev,
                "location": event.get('location', ''),
                "description": event.get('description', '')
            })
        
        cache_set(key, result)
        return result
    except Exception as e:
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
        jst = tz(timedelta(hours=9))
        today_str = datetime.now(jst).strftime("%Y-%m-%d")

        for i in range(len(hourly["time"])):
            t_str = hourly["time"][i]
            if not t_str.startswith(today_str): continue
            
            h = int(t_str[11:13])
            if 8 <= h <= 20 and h % 2 == 0:
                hc = hourly["weather_code"][i]
                hourly_data.append({
                    "time": t_str[11:16],
                    "temp": round(hourly["temperature_2m"][i], 1),
                    "icon": ICO.get(hc, "🌡")
                })
        
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

def load_commands():
    fp = os.path.join(os.getcwd(), "data", "commands.json")
    if not os.path.isfile(fp):
        return []
    try:
        with open(fp, encoding="utf-8") as f:
            data = json.load(f)
        for item in data:
            if isinstance(item.get("cmd"), list):
                item["cmd"] = "\n".join(item["cmd"])
        return data
    except Exception as e:
        return [{"name": f"⚠ commands.json 読み込みエラー: {e}", "cmd": ""}]

def music_tree():
    music_dir = os.path.join(os.getcwd(), "data", "music")
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

def images_list():
    d = os.path.join(os.getcwd(), "data", "images")
    if not os.path.isdir(d): return []
    ext = {".png",".jpg",".jpeg",".webp",".gif"}
    return ["/images/"+f for f in sorted(os.listdir(d)) if os.path.splitext(f)[1].lower() in ext]
