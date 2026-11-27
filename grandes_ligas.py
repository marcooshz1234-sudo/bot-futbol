"""
21/11 (Marcos: «en Telegram se están subiendo cosas de la Eredivisie; los días que jueguen las 5 grandes ligas solo
quiero contenido de ellas, mayormente de la Española»).
Un día «de grandes» = juegan partidos de LaLiga, Premier, Serie A, Bundesliga o Ligue 1 (datos/calendario_<liga>.json).
Ese día, en Telegram solo picks de esas 5 ligas (y de Champions/Europa/Conference si coinciden). Verdes, resúmenes,
buenos días… (sin «sel» de partidos) no se tocan. LaLiga va por delante (ESPANA_EXTRA en combis_dia).
"""
import json
from datetime import datetime
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
GRANDES5 = (140, 39, 135, 78, 61)
EUROPA = (2, 3, 848)
MIN_PARTIDOS = 8           # 27/11: con 8 o más partidos de las 5 grandes, el día es «de grandes». Antes con 2: los
                           # viernes y lunes (3-5 partidos) se quedaban en 3 picks («hoy muy poco contenido», 23 y 27/11)
_CACHE = {}


def _calendario(datos=None):
    datos = Path(datos or RAIZ / "datos")
    clave = str(datos)
    if clave not in _CACHE:
        ids, dias = {}, {}
        for liga in GRANDES5 + EUROPA:
            try:
                fx = json.loads((datos / f"calendario_{liga}.json").read_text(encoding="utf-8"))
            except Exception:
                continue
            for f in fx:
                try:
                    fid = f["fixture"]["id"]
                    from zoneinfo import ZoneInfo
                    dia = datetime.fromisoformat(f["fixture"]["date"]).astimezone(ZoneInfo("Europe/Madrid")).strftime("%Y-%m-%d")
                except Exception:
                    continue
                ids[fid] = liga
                if liga in GRANDES5:
                    dias[dia] = dias.get(dia, 0) + 1
        _CACHE[clave] = (ids, dias)
    return _CACHE[clave]


def dia_de_grandes(dia, datos=None):
    return _calendario(datos)[1].get(dia, 0) >= MIN_PARTIDOS


def liga_de(fid, datos=None):
    """23/11: si no está en los calendarios (p. ej. aún no se habían bajado), la liga de datos/proximos/<fid>.json:
    el Monza–Fiorentina (Serie A) se quedó fuera como «no de las 5 grandes»."""
    try:
        liga = _calendario(datos)[0].get(int(fid))
    except (TypeError, ValueError):
        return None
    if liga is None:
        try:
            ex = json.loads((Path(datos or RAIZ / "datos") / "proximos" / f"{int(fid)}.json").read_text(encoding="utf-8"))
            lid = ex["partido"]["league"]["id"]
            liga = lid if lid in GRANDES5 + EUROPA else None
        except Exception:
            pass
    return liga


def fuera_de_grandes(p, dia, datos=None):
    """True si el post lleva algún pick de fuera de las 5 grandes (o Europa) en un día de grandes."""
    sel = [s for s in (p.get("sel") or []) if s]
    if p.get("fuera_ok"):   # 23/11: Marcos lo ha pedido aunque sea de otra liga (p. ej. Ceuta–Almería, Segunda)
        return False
    if not sel or not dia_de_grandes(dia, datos):
        return False
    return any(liga_de(s.split("|")[0], datos) is None for s in sel)


def liga_permitida(liga_id, dia, datos=None):
    """Para los generadores: en un día de grandes, solo las 5 grandes y Europa."""
    return not dia_de_grandes(dia, datos) or liga_id in GRANDES5 + EUROPA
