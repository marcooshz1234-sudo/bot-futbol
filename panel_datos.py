"""
30/10 (Marcos): datos del PANEL DE CONTROL (mini app dentro del bot del móvil, docs/panel/index.html).
Lo llama app_datos.py en cada vuelta. Sale en docs/panel/datos.json.

  cola         lo que va a salir en las próximas 48 h (texto como saldrá, imagen, si está cancelado)
  redes        lo de las últimas 30 h: en qué red ha salido cada post, qué ha fallado y si se puede reintentar
  comentarios  comentarios de Threads sin contestar (los trae redes.py) con respuestas propuestas
  ajustes      interruptores del bot (control.json → "ajustes") con sus valores por defecto
  rendimiento  seguidores, mejores posts de la semana en Threads y qué tipo de post / hora funciona mejor
Las acciones las manda la mini app al bot del móvil (asistente.py, panel_acciones.py). Aquí solo se lee.
"""
import json
from collections import defaultdict
from datetime import datetime, timedelta

from bot import DATOS, MADRID, RAIZ, leer
from incidencias import identificador, motivo_bloqueo, publicaciones

SALIDA = RAIZ / "docs" / "panel" / "datos.json"
MEDIA = "https://raw.githubusercontent.com/marcooshz1234-sudo/bot-futbol/main/publicaciones/media/"
REDES_POST = ("telegram", "threads", "instagram")

# valores por defecto de los interruptores (lo que hace el bot si Marcos no ha tocado nada)
AJUSTES = {
    "gifs": {"t": "GIFs de relleno", "d": "2-3 al día en Telegram", "tipo": "si_no", "v": True},
    "noche": {"t": "Combis de madrugada", "d": "00:30 y 01:30, partidos grandes", "tipo": "si_no", "v": True},
    "enlace_threads": {"t": "Enlace a Telegram en Threads", "d": "Primer comentario de cada combi", "tipo": "si_no", "v": True},
    "cuota_min": {"t": "Cuota mínima combi de partido", "tipo": "num", "v": 7.0, "paso": 0.5, "min": 2, "max": 30},
    "cuota_max": {"t": "Cuota máxima combi de partido", "tipo": "num", "v": 10.0, "paso": 0.5, "min": 3, "max": 50},
    "patas": {"t": "Cosas por combi de partido", "tipo": "num", "v": 6, "paso": 1, "min": 3, "max": 6},
    "hora_escalera": {"t": "Hora de la escalera", "tipo": "hora", "v": "11:00"},
    "hora_x3": {"t": "Hora de la combi x3", "tipo": "hora", "v": "13:30"},
    "hora_loca": {"t": "Hora de la loca", "tipo": "hora", "v": "16:00"},
    "hora_picks": {"t": "Hora de picks para mañana", "tipo": "hora", "v": "23:00"},
}


def ajustes(control=None):
    """Valores actuales: los de control.json["ajustes"] o, si no están, los de por defecto."""
    control = control if control is not None else (leer(RAIZ / "publicaciones" / "control.json", {}) or {})
    puestos = control.get("ajustes") or {}
    return {k: puestos.get(k, a["v"]) for k, a in AJUSTES.items()}


def tipo_post(pid):
    for k, n in (("combi-partido", "Combi con escudos"), ("escalera", "Escalera"), ("picks-manana", "Picks para mañana"),
                 ("combi-tres", "Combi x3"), ("combi-loca", "La loca"), ("ganadores", "Quién gana"),
                 ("balance", "Balance"), ("verde", "Verde"), ("boleto", "Boleto"), ("personal", "Combi personal")):
        if k in pid:
            return n
    return "Otros"


def titulo(texto):
    """Primera línea; en las combis con escudos, el partido (la 1ª línea es igual en todas)."""
    l = [x for x in texto.strip().splitlines() if x.strip()]
    if l and "COMBI LOCAS" in l[0].upper() and len(l) > 1:
        return l[1].strip()
    return (l[0] if l else "")[:70]


def imagen(p):
    """La foto con la que sale (tarjeta de escudos para Telegram/Threads, si no la imagen de Instagram)."""
    media = RAIZ / "publicaciones" / "media"
    for ext in ("tarjeta.jpg", "jpg"):
        if (media / f"{p['id']}.{ext}").exists():
            return MEDIA + f"{p['id']}.{ext}"
    return None


def main():
    ahora = datetime.now(MADRID)
    control = leer(RAIZ / "publicaciones" / "control.json", {}) or {}
    textos = control.get("textos") or {}
    cancelados = set(control.get("cancelados") or [])
    posts = publicaciones(RAIZ)

    cola = []
    hasta = (ahora + timedelta(hours=48)).strftime("%Y-%m-%dT%H:%M")
    desde = (ahora - timedelta(minutes=45)).strftime("%Y-%m-%dT%H:%M")
    for p in sorted(posts, key=lambda x: x["fecha"]):
        if p.get("enviado") or p.get("mensaje_id") or p.get("borrar") or p.get("caducada") not in (None, False):
            continue
        if not (desde <= p["fecha"] <= hasta):
            continue
        cola.append({"id": p["id"], "fecha": p["fecha"], "tipo": tipo_post(p["id"]),
                     "texto": textos.get(p["id"], p["texto"]), "editado": p["id"] in textos,
                     "imagen": imagen(p), "cancelado": p["id"] in cancelados})

    redes = []
    desde30 = (ahora - timedelta(hours=30)).strftime("%Y-%m-%dT%H:%M")
    for p in sorted(posts, key=lambda x: x["fecha"], reverse=True):
        if p["fecha"] < desde30 or p["fecha"] > ahora.strftime("%Y-%m-%dT%H:%M") or p["id"] in cancelados:
            continue
        r, err = p.get("redes") or {}, p.get("errores_redes") or {}
        estado = {}
        for red in REDES_POST:
            hecho = bool(p.get("enviado") or p.get("mensaje_id")) if red == "telegram" else bool(r.get(red))
            fallo = p.get("error") if red == "telegram" else err.get(red)
            if not hecho and red != "telegram" and p.get("solo_redes") is None and "solo_en" in p and red not in p["solo_en"]:
                continue
            estado[red] = {"ok": hecho, "error": (str(fallo)[:140] if fallo and not hecho else None),
                           "clave": identificador(p["id"], red) if fallo and not hecho else None,
                           "bloqueo": motivo_bloqueo(p, red, control, ahora) if fallo and not hecho else None}
        redes.append({"id": p["id"], "fecha": p["fecha"], "tipo": tipo_post(p["id"]),
                      "titulo": titulo(textos.get(p["id"], p["texto"])), "redes": estado})

    com = [c for c in (leer(DATOS / "comentarios_threads.json", []) or []) if not c.get("hecho")]

    # rendimiento
    est = leer(RAIZ / "publicaciones" / "estadisticas.json", {}) or {}
    vistas = leer(DATOS / "threads_vistas.json", {}) or {}
    semana = (ahora - timedelta(days=7)).strftime("%Y-%m-%dT%H:%M")
    top, por_tipo, por_hora = [], defaultdict(list), defaultdict(list)
    for p in posts:
        tid = str((p.get("redes") or {}).get("threads") or "")
        if tid in vistas and p["fecha"] >= (ahora - timedelta(days=14)).strftime("%Y-%m-%dT%H:%M"):
            v = vistas[tid]
            por_tipo[tipo_post(p["id"])].append(v)
            h = int(p["fecha"][11:13])
            por_hora["00-03" if h < 3 else "03-11" if h < 11 else "11-15" if h < 15 else "15-19" if h < 19 else "19-24"].append(v)
            if p["fecha"] >= semana:
                top.append({"titulo": titulo(p["texto"]), "fecha": p["fecha"], "vistas": v,
                            "tipo": tipo_post(p["id"])})
    media = lambda l: round(sum(l) / len(l)) if l else 0
    rendimiento = {
        "seguidores": {k: v for k, v in (est.get("redes") or {}).items() if k != "facebook"},
        "top": sorted(top, key=lambda x: -x["vistas"])[:5],
        "por_tipo": sorted(({"tipo": k, "media": media(v), "n": len(v)} for k, v in por_tipo.items()), key=lambda x: -x["media"]),
        "por_hora": [{"franja": k, "media": media(por_hora[k]), "n": len(por_hora[k])} for k in ("00-03", "03-11", "11-15", "15-19", "19-24") if por_hora[k]],
    }

    datos = {"generado": ahora.strftime("%Y-%m-%d %H:%M"), "pausa": bool(control.get("pausa")),
             "cola": cola, "redes": redes, "comentarios": com[-30:],
             "ajustes": {k: dict(a, v=ajustes(control)[k]) for k, a in AJUSTES.items()}, "rendimiento": rendimiento}
    SALIDA.parent.mkdir(parents=True, exist_ok=True)
    SALIDA.write_text(json.dumps(datos, ensure_ascii=False) + "\n", encoding="utf-8")
    return datos


if __name__ == "__main__":
    d = main()
    print(f"Panel: {len(d['cola'])} en cola · {len(d['redes'])} recientes · {len(d['comentarios'])} comentarios")
