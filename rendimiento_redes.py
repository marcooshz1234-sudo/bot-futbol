"""16/11 (Marcos: «ten en cuenta cómo ha funcionado cada publicación: los likes y la gente que me ha seguido a partir de
cada publicación. Eso me importa mucho; las visualizaciones también, pero sobre todo que me siga la gente»).

Solo lee (no publica ni borra nada). Lo lanza GitHub (.github/workflows/rendimiento.yml y el bucle de publicación).

- Threads: vistas, likes, respuestas, reposts y compartidos de CADA post (la API de Threads no da seguidores por post),
  y una foto de los seguidores de la cuenta en cada pasada (datos/seguidores_redes.json). Los seguidores que entran
  entre una foto y la siguiente se reparten entre los posts de ese rato según sus vistas → «seguidores estimados».
- Instagram: vistas, alcance, likes, comentarios, guardados, compartidos y «follows» (gente que te siguió desde ese
  post: este sí lo da Instagram) de cada post.
- Junta cada post con su TIPO (escalera, combi del día, escudos, pick suelto, GANADORES, lista…) y su FORMATO
  (texto, escudos, tarjeta, foto) → datos/rendimiento_redes.json con la mediana de cada cosa por tipo.
"""
import json
import os
import re
import statistics as st
import sys
import time
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

RAIZ = Path(__file__).parent
DATOS = RAIZ / "datos"
PUB = RAIZ / "publicaciones"
SALIDA = DATOS / "rendimiento_redes.json"
SEGUIDORES = DATOS / "seguidores_redes.json"
DIAS = 45
CADA_HORAS = 3   # en el bucle, como mucho cada 3 h (la fecha va DENTRO del archivo: el mtime de git no sirve)


def leer(f, defecto=None):
    try:
        return json.loads(Path(f).read_text(encoding="utf-8"))
    except Exception:
        return defecto


def tipo(pid):
    s = pid[11:]
    for k, n in (("verde", "verde"), ("rojo", "rojo"), ("balance", "balance"), ("resumen", "balance"),
                 ("resultado", "balance"), ("ganadores", "GANADORES"), ("escalera", "escalera"),
                 ("pick-seguro", "pick suelto"), ("combi-partido", "combi de 1 partido"), ("boleto", "boleto"),
                 ("estrella", "estrella"), ("lista", "lista"), ("combi-tres", "combi del día"),
                 ("personal", "combi larga"), ("larga", "combi larga"), ("loca", "loca"), ("multi", "multi"),
                 ("marcadores", "marcadores"), ("info-top", "info top"), ("porque", "porqué")):
        if k in s:
            return n
    if re.search(r"-(e|t)\d*$", s) or "tip" in s or "copia" in s:
        return "copia de canal"
    return "otros"


def formato(p):
    if not p:
        return "?"
    if p.get("sin_foto"):
        return "texto"
    if p.get("ganadores_img") or "ganadores" in p["id"]:
        return "tarjeta"
    if p.get("tarjeta") or p.get("foto_en_threads"):
        return "escudos"
    if "-pick-seguro" in p["id"]:
        return "foto"
    return "texto"


def _llamar(metodo, url, params):
    from redes import llamar
    return llamar(metodo, url, params)


def threads(tok, previo):
    from redes import THREADS
    desde = (datetime.now(timezone.utc) - timedelta(days=DIAS)).strftime("%Y-%m-%d")
    posts, url, params = [], f"{THREADS}/me/threads", {"fields": "id,timestamp,media_type,permalink", "limit": 100,
                                                       "since": desde, "access_token": tok}
    while url and len(posts) < 800:
        r = _llamar("GET", url, params)
        posts += r.get("data", [])
        url = (r.get("paging") or {}).get("next")
        params = {}
        if url:
            from urllib.parse import unquote
            url, _, q = url.partition("?")
            params = {k: unquote(v) for k, v in (x.split("=", 1) for x in q.split("&"))}
    out = {}
    t0 = time.time()
    for p in posts:
        viejo = previo.get(p["id"])
        # los de hace más de 4 días ya casi no cambian: se reaprovecha lo medido (para no pasarse de tiempo)
        if viejo and p["timestamp"] < (datetime.now(timezone.utc) - timedelta(days=4)).strftime("%Y-%m-%dT%H"):
            out[p["id"]] = viejo
            continue
        if time.time() - t0 > 200:
            if viejo:
                out[p["id"]] = viejo
            continue
        try:
            r = _llamar("GET", f"{THREADS}/{p['id']}/insights",
                        {"metric": "views,likes,replies,reposts,quotes,shares", "access_token": tok})
            m = {x["name"]: (x.get("values") or [{}])[0].get("value", (x.get("total_value") or {}).get("value"))
                 for x in r.get("data", [])}
        except Exception as e:
            print("Threads insights:", str(e)[:120])
            m = (viejo or {}).get("m") or {}
        out[p["id"]] = {"ts": p["timestamp"], "m": m}
    try:
        r = _llamar("GET", f"{THREADS}/me/threads_insights", {"metric": "followers_count", "access_token": tok})
        seg = (r["data"][0].get("total_value") or {}).get("value")
    except Exception as e:
        print("Threads seguidores:", str(e)[:120])
        seg = None
    return out, seg


INSTA_METRICAS = ("views", "reach", "likes", "comments", "saved", "shares", "follows", "profile_visits")


def instagram(tok, previo):
    from redes import INSTAGRAM
    posts, url, params = [], f"{INSTAGRAM}/me/media", {"fields": "id,timestamp,media_type,media_product_type,permalink",
                                                       "limit": 100, "access_token": tok}
    limite = (datetime.now(timezone.utc) - timedelta(days=DIAS)).strftime("%Y-%m-%d")
    while url and len(posts) < 600:
        r = _llamar("GET", url, params)
        nuevos = r.get("data", [])
        posts += [x for x in nuevos if x["timestamp"] >= limite]
        if not nuevos or nuevos[-1]["timestamp"] < limite:
            break
        url = (r.get("paging") or {}).get("next")
        params = {}
        if url:
            from urllib.parse import unquote
            url, _, q = url.partition("?")
            params = {k: unquote(v) for k, v in (x.split("=", 1) for x in q.split("&"))}
    out = {}
    t0 = time.time()
    for p in posts:
        viejo = previo.get(p["id"])
        if viejo and (p["timestamp"] < (datetime.now(timezone.utc) - timedelta(days=4)).strftime("%Y-%m-%dT%H")
                      or time.time() - t0 > 150):
            out[p["id"]] = viejo
            continue
        m = {}
        for met in INSTA_METRICAS:   # una a una: si una no vale para ese tipo de post, las demás sí
            try:
                r = _llamar("GET", f"{INSTAGRAM}/{p['id']}/insights", {"metric": met, "access_token": tok})
                x = (r.get("data") or [{}])[0]
                m[met] = (x.get("values") or [{}])[0].get("value", (x.get("total_value") or {}).get("value"))
            except Exception:
                pass
        out[p["id"]] = {"ts": p["timestamp"], "m": m, "tipo_media": p.get("media_product_type")}
    try:
        seg = _llamar("GET", f"{INSTAGRAM}/me", {"fields": "followers_count", "access_token": tok}).get("followers_count")
    except Exception as e:
        print("Instagram seguidores:", str(e)[:120])
        seg = None
    return out, seg


def repartir_seguidores(medidos, fotos):
    """Seguidores estimados por post de Threads: lo que sube la cuenta entre dos fotos se reparte entre los posts
    publicados en las 24 h anteriores a ese tramo, según sus vistas."""
    est = defaultdict(float)
    fotos = sorted((datetime.fromisoformat(k), v) for k, v in fotos.items() if v is not None)
    for (t1, s1), (t2, s2) in zip(fotos, fotos[1:]):
        gana = s2 - s1
        if gana <= 0 or (t2 - t1) > timedelta(hours=12):
            continue
        vivos = [(pid, (d.get("m") or {}).get("views") or 0) for pid, d in medidos.items()
                 if t1 - timedelta(hours=24) <= datetime.fromisoformat(d["ts"].replace("+0000", "+00:00")) <= t2]
        tot = sum(v for _, v in vivos)
        for pid, v in vivos:
            if tot:
                est[pid] += gana * v / tot
    return {k: round(v, 2) for k, v in est.items()}


def resumen(redes_posts, mapa, posts):
    """Por tipo y formato: nº de posts y mediana de cada métrica."""
    filas = []
    for red, medidos in redes_posts.items():
        for mid, d in medidos.items():
            pid = mapa[red].get(mid)
            if not pid:
                continue
            p = posts.get(pid)
            filas.append({"red": red, "id": pid, "tipo": tipo(pid), "formato": formato(p), **(d.get("m") or {}),
                          **({"seguidores_est": d["seguidores_est"]} if "seguidores_est" in d else {})})
    out = {}
    for red in redes_posts:
        g = defaultdict(list)
        for f in filas:
            if f["red"] == red:
                g[(f["tipo"], f["formato"])].append(f)
        tabla = []
        for (t, fo), l in g.items():
            fila = {"tipo": t, "formato": fo, "n": len(l)}
            for met in ("views", "likes", "replies", "shares", "reposts", "follows", "profile_visits", "saved",
                        "seguidores_est"):
                vals = [x[met] for x in l if isinstance(x.get(met), (int, float))]
                if vals:
                    fila[met] = round(st.median(vals), 2)
                    fila[met + "_total"] = round(sum(vals), 2)
            tabla.append(fila)
        out[red] = sorted(tabla, key=lambda f: -(f.get("follows_total") or f.get("seguidores_est_total") or 0))
    return out, filas


def main():
    previo = leer(SALIDA, {}) or {}
    if "--ya" not in sys.argv and previo.get("generado"):
        if datetime.now(timezone.utc) - datetime.fromisoformat(previo["generado"]) < timedelta(hours=CADA_HORAS):
            print("rendimiento_redes: hecho hace menos de", CADA_HORAS, "h")
            return
    tokens = {"threads": os.environ.get("THREADS_TOKEN"), "instagram": os.environ.get("INSTAGRAM_TOKEN")}
    medidos, fotos = {}, leer(SEGUIDORES, {}) or {}
    ahora = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    for red, fn in (("threads", threads), ("instagram", instagram)):
        if not tokens[red]:
            medidos[red] = (previo.get("posts") or {}).get(red) or {}
            continue
        try:
            medidos[red], seg = fn(tokens[red], (previo.get("posts") or {}).get(red) or {})
            fotos.setdefault(red, {})[ahora] = seg
        except Exception as e:
            print(red, "error:", str(e)[:200])
            medidos[red] = (previo.get("posts") or {}).get(red) or {}
    est = repartir_seguidores(medidos.get("threads") or {}, fotos.get("threads") or {})
    for mid, v in est.items():
        medidos["threads"][mid]["seguidores_est"] = v
    env = leer(PUB / "enviados_redes.json", {}) or {}
    mapa = {"threads": {}, "instagram": {}}
    for pid, d in env.items():
        for red, k in (("threads", "threads"), ("instagram", "instagram"), ("instagram", "instagram_reel")):
            mid = (d.get("redes") or {}).get(k)
            if mid:
                mapa[red][str(mid)] = pid
    posts = {}
    for f in ("cola.json", "auto.json"):
        for p in leer(PUB / f, []) or []:
            posts[p["id"]] = p
    tablas, filas = resumen(medidos, mapa, posts)
    SALIDA.write_text(json.dumps({"generado": ahora, "posts": medidos, "por_tipo": tablas,
                                  "top": sorted(filas, key=lambda f: -((f.get("follows") or 0) * 50 + (f.get("seguidores_est") or 0) * 50
                                                                        + (f.get("likes") or 0) * 3 + (f.get("views") or 0) / 100))[:30]},
                                 ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    SEGUIDORES.write_text(json.dumps(fotos, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print("rendimiento_redes:", {r: len(v) for r, v in medidos.items()}, "seguidores:",
          {r: list(v.values())[-1] if v else None for r, v in fotos.items()})


if __name__ == "__main__":
    main()
