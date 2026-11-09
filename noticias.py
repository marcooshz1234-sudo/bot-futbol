"""
09/11 (Marcos): noticias de los periódicos para el bot (no para publicar). Gratis y sin clave:
Google Noticias (búsqueda por equipo, recoge Marca, AS, Mundo Deportivo, Relevo, prensa local…) en RSS.

Cada vez que corre:
  1) Para cada partido de hoy y mañana, busca las noticias de las últimas 36 h de cada equipo.
  2) Las clasifica por palabras clave (TIPOS) → datos/noticias.json {id del partido: [noticias]}.
  3) Si un jugador que va en un post aún no publicado sale de baja o duda, avisa a Marcos por privado (una vez).
  4) combis_dia.py no mete en combis nuevas a jugadores con noticia de baja o duda (jugador_tocado).
  5) razones.py usa los hechos objetivos (cambio de campo, aplazamiento, entrenador nuevo, huelga…).
No se publica nada de esto ni se copian textos: solo titulares para el bot y la app (con su enlace).
"""
import html
import json
import os
import re
import time
import unicodedata
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from email.utils import parsedate_to_datetime

from bot import DATOS, MADRID, RAIZ, leer

SALIDA = DATOS / "noticias.json"
AVISADAS = DATOS / "noticias_avisadas.json"
TIPOS = {   # tipo → palabras (en minúsculas y sin tildes)
    "baja": r"lesion|lesionad|baja|no viaja|descartad|sancionad|fuera de la convocatoria|no convocad|se pierde|roja directa|operad|rotura",
    "duda": r"\bduda\b|en duda|entre algodones|no esta al 100|molestias|tocado|ultima hora",
    "vuelve": r"vuelve|recupera|alta medica|reaparece|ya entrena",
    "rotaciones": r"rotacion|suplentes|descanso a|reservar|once alternativo|juveniles|canteranos|filial",
    "campo": r"se jugara en|estadio alternativo|cesped|cambio de estadio|fuera de su campo|campo neutral|puerta cerrada|sin publico",
    "aplazado": r"aplaza|suspend|nueva fecha",
    "entrenador": r"destitu|cesad|nuevo entrenador|nuevo tecnico|interino|debut en el banquillo|ultimatum",
    "crisis": r"huelga|impago|sin cobrar|crisis|concurso de acreedores|venta del club|protesta",
    "arbitro": r"arbitro|colegiado|designad|var\b",
    "motivacion": r"derbi|final|clasificad|descendid|se juega la|asciende|liderato|lider",
    "clima": r"lluvia|temporal|nieve|viento|alerta|calor extremo",
    "cansancio": r"seleccion|internacional|viaje|vuelo|jet lag|tres partidos en|entre semana",
}
HACE = timedelta(hours=36)


def norm(s):
    return unicodedata.normalize("NFKD", str(s or "")).encode("ascii", "ignore").decode().lower()


def buscar(q):
    url = "https://news.google.com/rss/search?" + urllib.parse.urlencode(
        {"q": f'"{q}" fútbol when:2d', "hl": "es", "gl": "ES", "ceid": "ES:es"})
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "combilocas-bot"}), timeout=30) as r:
            raiz = ET.fromstring(r.read())
    except Exception as e:
        print(f"  noticias {q}: {e}")
        return []
    out = []
    for it in raiz.iter("item"):
        titulo = html.unescape(it.findtext("title") or "")
        fuente = it.findtext("source") or ""
        try:
            f = parsedate_to_datetime(it.findtext("pubDate")).astimezone(MADRID)
        except Exception:
            continue
        if datetime.now(MADRID) - f > HACE:
            continue
        titulo = re.sub(rf"\s+-\s+{re.escape(fuente)}$", "", titulo) if fuente else titulo
        out.append({"titulo": titulo, "fuente": fuente, "link": it.findtext("link"), "fecha": f.strftime("%Y-%m-%dT%H:%M")})
    return out


def tipos(titulo):
    t = norm(titulo)
    return [k for k, rx in TIPOS.items() if re.search(rx, t)]


def partidos_proximos():
    hoy = datetime.now(MADRID)
    hasta = (hoy + timedelta(days=1)).strftime("%Y-%m-%d")
    out = []
    for f in (DATOS / "proximos").glob("*.json"):
        pa = (leer(f, {}) or {}).get("partido")
        if pa and pa["fixture"]["status"]["short"] in ("NS", "TBD") and hoy.strftime("%Y-%m-%d") <= pa["fixture"]["date"][:10] <= hasta:
            out.append(pa)
    return out


def corto(nombre):
    """«Real Jaén» → «Jaén», «Atletico Madrid W» → «Atlético Madrid femenino» (lo que escribe la prensa)."""
    n = re.sub(r"\s+W$", " femenino", nombre)
    n = re.sub(r"^(Real|CD|UD|SD|CF|FC|RCD|Club|Deportivo)\s+", "", n) if len(n.split()) > 1 and not n.startswith("Real Madrid") \
        and not n.startswith("Real Sociedad") and not n.startswith("Real Betis") else n
    return n


def jugadores_pendientes():
    """{(id del partido, jugador): [ids de posts aún no publicados]}."""
    from incidencias import publicaciones
    ahora = datetime.now(MADRID).strftime("%Y-%m-%dT%H:%M")
    out = {}
    for p in publicaciones(RAIZ):
        if p.get("enviado") or p.get("mensaje_id") or p.get("caducada") or p["fecha"] < ahora:
            continue
        for s in p.get("sel") or []:
            fid, mercado, opcion = (s.split("|") + ["", ""])[:3]
            if "Player" in mercado or " - " in opcion:
                j = opcion.rsplit(" - ", 1)[0]
                out.setdefault((fid, j), []).append(p["id"])
    return out


def avisar(lineas):
    token, canal = os.environ.get("TELEGRAM_TOKEN"), os.environ.get("TELEGRAM_CANAL")
    if not (token and canal and lineas):
        return
    from publicar_telegram import api
    admins = api(token, "getChatAdministrators", {"chat_id": canal})["result"]
    duenio = next(a["user"]["id"] for a in admins if a["status"] == "creator")
    api(token, "sendMessage", {"chat_id": duenio, "text": "📰 Noticias que tocan posts preparados:\n\n" + "\n\n".join(lineas)[:3900],
                               "link_preview_options": {"is_disabled": True}})


def main(forzar=False):
    # cada hora como mucho (el bucle lo llama cada pocos minutos)
    marca = DATOS / "noticias.visto"
    try:
        if not forzar and marca.exists() and datetime.now(MADRID) - datetime.fromisoformat(marca.read_text().strip()) < timedelta(minutes=55):
            return
    except ValueError:
        pass
    marca.write_text(datetime.now(MADRID).isoformat())
    datos = {}
    for pa in partidos_proximos():
        fid = str(pa["fixture"]["id"])
        lista = []
        for eq in (pa["teams"]["home"]["name"], pa["teams"]["away"]["name"]):
            for n in buscar(corto(eq)):
                n["equipo"], n["tipos"] = eq, tipos(n["titulo"])
                if not any(x["titulo"] == n["titulo"] for x in lista):
                    lista.append(n)
            time.sleep(1)
        lista.sort(key=lambda n: n["fecha"], reverse=True)
        datos[fid] = lista[:15]
    SALIDA.write_text(json.dumps(datos, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"Noticias: {sum(len(v) for v in datos.values())} de {len(datos)} partidos")
    # avisos: jugadores de posts preparados con noticia de baja o duda
    ya = set(leer(AVISADAS, []) or [])
    lineas = []
    for (fid, j), posts in jugadores_pendientes().items():
        ap = norm(j.split()[-1]) if j else ""
        for n in datos.get(fid, []):
            if ap and len(ap) > 3 and ap in norm(n["titulo"]) and {"baja", "duda"} & set(n["tipos"]):
                clave = f"{fid}|{j}|{n['titulo'][:60]}"
                if clave in ya:
                    continue
                ya.add(clave)
                lineas.append(f"⚠️ {n['fuente']}: «{n['titulo']}»\n→ {j} va en: {', '.join(p[11:] for p in posts)}\n"
                              f"Dime «quita a {j}» y lo rehago (o di «déjalo»).")
                break
    if lineas:
        try:
            avisar(lineas)
        except Exception as e:
            print("avisar:", e)
    AVISADAS.write_text(json.dumps(sorted(ya)[-500:], ensure_ascii=False) + "\n", encoding="utf-8")


def jugador_tocado(fid, jugador):
    """True si hay noticia de baja o duda del jugador en ese partido (para no meterlo en combis nuevas)."""
    ap = norm((jugador or "").split()[-1]) if jugador else ""
    if len(ap) <= 3:
        return False
    return any(ap in norm(n["titulo"]) and {"baja", "duda"} & set(n.get("tipos") or [])
               and "vuelve" not in (n.get("tipos") or [])
               for n in (leer(SALIDA, {}) or {}).get(str(fid), []))


def razones(fid):
    """Hechos para el pick del día (campo, aplazamiento, entrenador, crisis), con el periódico."""
    out = []
    for n in (leer(SALIDA, {}) or {}).get(str(fid), []):
        for t, peso in (("campo", 4), ("aplazado", 3), ("entrenador", 3), ("crisis", 4)):
            if t in n.get("tipos", []):
                out.append((peso, f"{n['titulo']} ({n['fuente']})"))
                break
    return out[:2]


if __name__ == "__main__":
    import sys
    main(forzar="--ya" in sys.argv)
