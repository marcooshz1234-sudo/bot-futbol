"""11/11 (Marcos: «que por cada pata mire más cosas, todo lo que pueda influir: el tiempo, el estadio… y que lo
aprenda»). El contexto de cada partido, sacado de lo que el bot ya tiene guardado (nada inventado):

  - descanso: días desde el partido anterior de cada equipo (cualquier competición) y si jugó en Europa entre semana
  - forma: puntos por partido y goles a favor/en contra de los últimos 5 partidos de cada equipo
  - árbitro: tarjetas amarillas de media en sus partidos anteriores (datos/partidos)
  - tiempo: lluvia, viento y temperatura (contexto_extra.py, desde el 10/11) → se guarda para aprender con él
  - estadio: ciudad, si el local juega fuera de su campo (contexto_partidos.json), hora (noche) y tipo de competición

Se guarda por partido en datos/contexto_patas.json (lo antiguo se calcula una vez; lo nuevo se va añadiendo) y lo usa
modelo_patas.py para aprender qué influye de verdad en cada tipo de pata.
"""
import json
from collections import defaultdict
from datetime import datetime
from zoneinfo import ZoneInfo

from bot import DATOS, leer

SALIDA = DATOS / "contexto_patas.json"
MADRID = ZoneInfo("Europe/Madrid")
EUROPA = {2, 3, 848}
_IDX = {}


def _indice():
    """Partidos por equipo (fecha, goles a favor, en contra, liga) y árbitro de cada partido, de los calendarios."""
    if _IDX:
        return _IDX
    por_equipo, info = defaultdict(list), {}
    for f in DATOS.glob("calendario_*.json"):
        for x in leer(f, []) or []:
            fx, t, g = x["fixture"], x["teams"], x.get("goals") or {}
            info[fx["id"]] = {"fecha": fx["date"], "arbitro": (fx.get("referee") or "").split(",")[0].strip() or None,
                              "ciudad": (fx.get("venue") or {}).get("city"), "liga": x["league"]["id"],
                              "liga_nombre": x["league"].get("name") or "", "local": t["home"]["id"], "visitante": t["away"]["id"]}
            terminado = fx["status"]["short"] in ("FT", "AET", "PEN") and g.get("home") is not None
            for lado, otro, gf, gc in (("home", "away", g.get("home"), g.get("away")), ("away", "home", g.get("away"), g.get("home"))):
                por_equipo[t[lado]["id"]].append((fx["date"], gf if terminado else None, gc if terminado else None,
                                                  x["league"]["id"], fx["id"]))
    for v in por_equipo.values():
        v.sort()
    _IDX.update({"equipo": por_equipo, "info": info, "arbitros": _arbitros(info)})
    return _IDX


def _arbitros(info):
    """Amarillas totales por partido de cada árbitro (de los partidos con estadísticas guardadas)."""
    out = defaultdict(list)
    for f in DATOS.glob("partidos/*.json"):
        try:
            pa = json.loads(f.read_text(encoding="utf-8"))
        except Exception:
            continue
        i = info.get(pa.get("id"))
        if not i or not i["arbitro"]:
            continue
        am = [(s or {}).get("amarillas") for s in (pa.get("stats") or {}).values()]
        if len(am) == 2 and all(a is not None for a in am):
            out[i["arbitro"]].append((pa.get("fecha") or i["fecha"], sum(am)))
    return out


def _equipo(eid, fecha):
    lista = [x for x in _indice()["equipo"].get(eid, []) if x[0] < fecha]
    previo = lista[-1] if lista else None
    jugados = [x for x in lista if x[1] is not None][-5:]
    r = {}
    if previo:
        r["descanso"] = (datetime.fromisoformat(fecha) - datetime.fromisoformat(previo[0])).days
        r["europa_antes"] = previo[3] in EUROPA and r["descanso"] <= 4
    if len(jugados) >= 3:
        pts = sum(3 if a > b else 1 if a == b else 0 for _, a, b, _, _ in jugados)
        r["forma"] = round(pts / len(jugados), 2)
        r["gf"] = round(sum(a for _, a, _, _, _ in jugados) / len(jugados), 2)
        r["gc"] = round(sum(b for _, _, b, _, _ in jugados) / len(jugados), 2)
    return r


def calcular(fid):
    idx = _indice()
    i = idx["info"].get(int(fid))
    if not i:
        return None
    c = {"local": _equipo(i["local"], i["fecha"]), "visitante": _equipo(i["visitante"], i["fecha"]),
         "ciudad": i["ciudad"], "hora": datetime.fromisoformat(i["fecha"]).astimezone(MADRID).hour,
         "competicion": ("europa" if i["liga"] in EUROPA else
                         "copa" if any(w in i["liga_nombre"].lower() for w in ("copa", "cup", "coppa", "pokal", "coupe", "trophy"))
                         else "liga")}
    previas = [a for f, a in idx["arbitros"].get(i["arbitro"], []) if f < i["fecha"]]
    if len(previas) >= 3:
        c["arbitro_amarillas"] = round(sum(previas) / len(previas), 2)
    extra = (leer(DATOS / "contexto_extra.json", {}) or {}).get(str(fid)) or {}
    if extra.get("tiempo"):
        c["tiempo"] = extra["tiempo"]
    cp = (leer(DATOS / "contexto_partidos.json", {}) or {}).get(str(fid)) or {}
    if cp:
        c["fuera_de_su_campo"] = bool(cp.get("local_fuera_de_su_campo"))
        if cp.get("local", {}).get("nivel") and cp.get("visitante", {}).get("nivel"):
            c["dif_nivel"] = cp["visitante"]["nivel"] - cp["local"]["nivel"]   # + = el local es de categoría superior
    return c


def guardar(fids):
    """Añade (o completa con el tiempo) el contexto de esos partidos en datos/contexto_patas.json."""
    todo = leer(SALIDA, {}) or {}
    nuevos = 0
    for fid in {str(f) for f in fids if f}:
        if fid in todo and ("tiempo" in todo[fid] or not (leer(DATOS / "contexto_extra.json", {}) or {}).get(fid)):
            continue
        c = calcular(fid)
        if c:
            todo[fid] = c
            nuevos += 1
    SALIDA.write_text(json.dumps(todo, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    return nuevos


def main():
    reg = leer(DATOS / "registro_aciertos.json", {}) or {}
    fids = {p.get("partido_id") for p in reg.values()}
    fids |= {f.stem for f in (DATOS / "proximos").glob("*.json")}
    print(f"Contexto de patas: {guardar(fids)} partidos nuevos")


if __name__ == "__main__":
    main()
