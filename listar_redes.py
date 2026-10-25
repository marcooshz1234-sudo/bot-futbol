"""Lista las últimas publicaciones de Threads, Instagram y Facebook (primera línea y hora) en datos/ultimas_redes.json."""
import json, os
from redes import FACEBOOK, INSTAGRAM, THREADS, llamar, pagina_facebook
from bot import DATOS
out = {}
try:
    r = llamar("GET", f"{THREADS}/me/threads", {"fields": "id,text,timestamp", "limit": 30, "access_token": os.environ["THREADS_TOKEN"]})
    out["threads"] = [[x.get("timestamp"), (x.get("text") or "").split("\n")[0][:50]] for x in r.get("data", [])]
except Exception as e:
    out["threads"] = str(e)
try:
    r = llamar("GET", f"{INSTAGRAM}/me/media", {"fields": "id,caption,timestamp,media_type", "limit": 30, "access_token": os.environ["INSTAGRAM_TOKEN"]})
    out["instagram"] = [[x.get("timestamp"), x.get("media_type"), (x.get("caption") or "").split("\n")[0][:50]] for x in r.get("data", [])]
except Exception as e:
    out["instagram"] = str(e)
try:
    pag, tok = pagina_facebook(os.environ["FACEBOOK_TOKEN"], os.environ.get("FACEBOOK_PAGINA"))
    r = llamar("GET", f"{FACEBOOK}/{pag}/posts", {"fields": "id,message,created_time", "limit": 30, "access_token": tok})
    out["facebook"] = [[x.get("created_time"), (x.get("message") or "").split("\n")[0][:50]] for x in r.get("data", [])]
except Exception as e:
    out["facebook"] = str(e)
(DATOS / "ultimas_redes.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
print(json.dumps(out, ensure_ascii=False)[:500])
