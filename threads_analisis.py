"""Todos los posts de Threads con sus métricas (vistas, likes, respuestas, reposts, citas, compartidos)
y las métricas de la cuenta, para analizar qué funciona. Sale en datos/threads_analisis.json.
Solo lee: no publica ni borra nada."""
import json
import os
import time

from bot import DATOS
from redes import THREADS, llamar

tok = os.environ["THREADS_TOKEN"]
# 27/10: también se lanza desde el bucle de publicación; como mucho una vez cada 6 h
_previo = DATOS / "threads_analisis.json"
if "--ya" not in __import__("sys").argv and _previo.exists() and time.time() - _previo.stat().st_mtime < 6 * 3600:
    raise SystemExit(0)
posts, url, params = [], f"{THREADS}/me/threads", {
    "fields": "id,text,timestamp,media_type,permalink,is_quote_post,topic_tag,shortcode",
    "limit": 100, "access_token": tok}
while url and len(posts) < 2000:
    r = llamar("GET", url, params)
    posts += r.get("data", [])
    url = (r.get("paging") or {}).get("next")
    params = {}
    if url:
        url, _, q = url.partition("?")
        params = dict(x.split("=", 1) for x in q.split("&"))
        from urllib.parse import unquote
        params = {k: unquote(v) for k, v in params.items()}

for p in posts:
    try:
        r = llamar("GET", f"{THREADS}/{p['id']}/insights",
                   {"metric": "views,likes,replies,reposts,quotes,shares", "access_token": tok})
        p["metricas"] = {m["name"]: (m.get("values") or [{}])[0].get("value", (m.get("total_value") or {}).get("value"))
                         for m in r.get("data", [])}
    except Exception as e:
        p["metricas"] = {"error": str(e)[:150]}
    time.sleep(0.2)

cuenta = {}
for m in ("views", "likes", "replies", "reposts", "quotes", "followers_count", "follower_demographics"):
    try:
        extra = {"breakdown": "country"} if m == "follower_demographics" else {}
        r = llamar("GET", f"{THREADS}/me/threads_insights", dict({"metric": m, "access_token": tok}, **extra))
        cuenta[m] = r.get("data")
    except Exception as e:
        cuenta[m] = f"error: {str(e)[:150]}"
try:
    cuenta["perfil"] = llamar("GET", f"{THREADS}/me", {"fields": "username,name,threads_biography,threads_profile_picture_url",
                                                       "access_token": tok})
except Exception as e:
    cuenta["perfil"] = f"error: {str(e)[:150]}"

(DATOS / "threads_analisis.json").write_text(json.dumps({"cuenta": cuenta, "posts": posts}, ensure_ascii=False, indent=1),
                                             encoding="utf-8")
print(f"Threads: {len(posts)} posts analizados")
