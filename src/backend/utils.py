import threading
import time

_cache = {}
_lock = threading.Lock()
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
