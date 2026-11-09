"""
09/11 (Marcos: «¿tú sabrías lo del Jaén?» → no; «sí, mételo»): contexto de los partidos de Copa del Rey (y de
cualquier partido con un equipo que no está en nuestras ligas), sacado de API-Football:

  - categoría de cada equipo: en qué liga juega esta temporada (Primera = 1, Segunda = 2, Primera RFEF = 3…)
  - arranque: sus últimos 6 partidos de esta temporada (V/E/D)
  - estadio: si el partido no se juega en el campo habitual del local («pierde la ventaja de casa»)
  - aplazamientos: si ya vimos ese partido con otra fecha o aplazado (datos/fechas_vistas.json)

→ datos/contexto_partidos.json {id del partido: {...}}, que usa razones.py. Pocas peticiones: los equipos se guardan
(categoría y estadio, una vez por temporada; arranque, una vez al día).
"""
import json
import os
import sys
from datetime import datetime, timedelta

from bot import API, DATOS, MADRID, TEMPORADA, leer

EQUIPOS = DATOS / "equipos_info.json"
SALIDA = DATOS / "contexto_partidos.json"
FECHAS = DATOS / "fechas_vistas.json"
COPAS = (143,)
NIVEL = [   # nombre de la liga (API-Football) → categoría
    ("La Liga", 1), ("Segunda División", 2), ("Primera División RFEF", 3), ("Primera RFEF", 3),
    ("Segunda División RFEF", 4), ("Segunda RFEF", 4), ("Tercera División RFEF", 5), ("Tercera RFEF", 5),
]
NOMBRE_NIVEL = {1: "Primera", 2: "Segunda", 3: "Primera Federación", 4: "Segunda Federación", 5: "Tercera Federación"}


def nivel(nombre, pais="Spain", femenino=False):
    """09/11: con el mapa de categorías (ligas.py / datos/ligas_mapa.json)."""
    try:
        import ligas
        c = ligas.categoria(nombre, pais, femenino)
        if c:
            return c["nivel"]
    except Exception:
        pass
    return nivel_viejo(nombre)


def nivel_viejo(nombre):
    # 09/11: de más largo a más corto («Segunda División RFEF» no es «Segunda División»)
    for n, v in sorted(NIVEL, key=lambda x: -len(x[0])):
        if nombre.lower().startswith(n.lower()):
            return v
    return None


def escribir(ruta, datos):
    ruta.write_text(json.dumps(datos, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")


def info_equipo(api, tid, eq, hoy):
    e = eq.setdefault(str(tid), {})
    if e.get("temporada") != TEMPORADA or e.get("v") != 2:   # v2: niveles bien (09/11)
        ligas = api.get("leagues", team=tid, season=TEMPORADA)
        cands = [(nivel(l["league"]["name"]), l["league"]["name"]) for l in ligas
                 if l["league"].get("type") == "League" and (l.get("country") or {}).get("name") == "Spain"]
        cands = [c for c in cands if c[0]]
        e["nivel"], e["liga"] = (min(cands) if cands else (None, None))
        t = api.get("teams", id=tid)
        v = (t[0].get("venue") or {}) if t else {}
        e["estadio"], e["estadio_id"] = v.get("name"), v.get("id")
        e["temporada"], e["v"] = TEMPORADA, 2
    if e.get("dia") != hoy:
        fx = api.get("fixtures", team=tid, season=TEMPORADA, last=6)
        res = []
        for f in fx:
            g = f.get("goals") or {}
            if g.get("home") is None:
                continue
            casa = f["teams"]["home"]["id"] == tid
            gf, gc = (g["home"], g["away"]) if casa else (g["away"], g["home"])
            res.append("V" if gf > gc else "E" if gf == gc else "D")
        e["ultimos"], e["dia"] = res, hoy
    return e


def main():
    clave = os.environ.get("API_FOOTBALL_KEY")
    if not clave:
        sys.exit("Falta API_FOOTBALL_KEY")
    api = API(clave)
    hoy = datetime.now(MADRID).strftime("%Y-%m-%d")
    limite = (datetime.now(MADRID) + timedelta(days=3)).strftime("%Y-%m-%d")
    eq = leer(EQUIPOS, {}) or {}
    fechas = leer(FECHAS, {}) or {}
    salida = {}
    for liga in COPAS:
        for f in leer(DATOS / f"calendario_{liga}.json", []) or []:
            fid = str(f["fixture"]["id"])
            st = f["fixture"]["status"]["short"]
            visto = fechas.setdefault(fid, {"fechas": [], "aplazado": False})
            if f["fixture"]["date"][:16] not in visto["fechas"]:
                visto["fechas"].append(f["fixture"]["date"][:16])
            if st in ("PST", "CANC", "SUSP"):
                visto["aplazado"] = True
            if st not in ("NS", "TBD") or not (hoy <= f["fixture"]["date"][:10] <= limite):
                continue
            l, v = f["teams"]["home"], f["teams"]["away"]
            try:
                el, ev = info_equipo(api, l["id"], eq, hoy), info_equipo(api, v["id"], eq, hoy)
            except Exception as e:
                print("contexto:", e)
                continue
            sede = (f["fixture"].get("venue") or {})
            fuera_de_casa = bool(el.get("estadio_id") and sede.get("id") and sede["id"] != el["estadio_id"])
            en_campo_visitante = bool(ev.get("estadio_id") and sede.get("id") == ev["estadio_id"])
            salida[fid] = {
                "local": {"nombre": l["name"], "nivel": el.get("nivel"), "liga": el.get("liga"), "ultimos": el.get("ultimos")},
                "visitante": {"nombre": v["name"], "nivel": ev.get("nivel"), "liga": ev.get("liga"), "ultimos": ev.get("ultimos")},
                "sede": sede.get("name"), "estadio_local": el.get("estadio"), "local_fuera_de_su_campo": fuera_de_casa, "en_campo_visitante": en_campo_visitante,
                "aplazamientos": max(len(visto["fechas"]) - 1, 1 if visto["aplazado"] else 0),
            }
    escribir(EQUIPOS, eq)
    escribir(FECHAS, fechas)
    escribir(SALIDA, salida)
    print(f"Contexto de copa: {len(salida)} partidos · {api.usadas} peticiones")


def razones(fid):
    """Frases (hechos) para razones.py: categoría, arranque, campo y aplazamientos."""
    c = (leer(SALIDA, {}) or {}).get(str(fid))
    if not c:
        return []
    out = []
    L, V = c["local"], c["visitante"]
    if L.get("nivel") and V.get("nivel") and L["nivel"] != V["nivel"]:
        d = abs(L["nivel"] - V["nivel"])
        arriba, abajo = (L, V) if L["nivel"] < V["nivel"] else (V, L)
        out.append((5, f"{'Una categoría' if d == 1 else f'{d} categorías'} de diferencia: el {arriba['nombre']} juega en "
                       f"{NOMBRE_NIVEL.get(arriba['nivel'], arriba['liga'])} y el {abajo['nombre']} en "
                       f"{NOMBRE_NIVEL.get(abajo['nivel'], abajo['liga'])}"))
    for e in (L, V):
        u = e.get("ultimos") or []
        if len(u) >= 5:
            v, d = u.count("V"), u.count("D")
            if v >= 4:
                out.append((3, f"El {e['nombre']} llega lanzado: {v} victorias en sus últimos {len(u)}"))
            elif v == 0 and d >= 3:
                out.append((3, f"El {e['nombre']} no gana en sus últimos {len(u)}"))
    if c.get("en_campo_visitante") and c.get("sede"):
        out.append((5, f"Se juega en el campo del {V['nombre']} ({c['sede']}): el {L['nombre']} pierde la ventaja de casa"))
    elif c.get("local_fuera_de_su_campo") and c.get("sede"):
        out.append((4, f"El {L['nombre']} no juega en su campo ({c['sede']}): pierde la ventaja de casa"))
    if c.get("aplazamientos"):
        n = c["aplazamientos"]
        out.append((2, f"El partido ya se ha aplazado {'una vez' if n == 1 else f'{n} veces'}"))
    return out


if __name__ == "__main__":
    main()
