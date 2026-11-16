"""16/11 (Marcos, viendo a un tipster en Twitch: «mira a ver si se juegan algo… la clasificación, la diferencia de
goles, si pierden y gana el de abajo, si pueden quedar primeros o descolgarse»): qué se juega cada equipo en un
partido de fase de grupos (Nations League y cualquier grupo con pocas jornadas por jugar).

Se prueban TODOS los resultados de los partidos que le quedan al grupo (marcadores 0-4) con el desempate de la UEFA
(puntos; entre los empatados: puntos, diferencia y goles del cara a cara; luego diferencia y goles generales) y se
mira en qué puesto acaba cada equipo si gana, empata o pierde.

- «nada»: acaba en el mismo puesto haga lo que haga (ya clasificado, ya primero, ya descendido…).
- «se_juega»: ganar le da un puesto mejor que perder.

Lo usa combis_dia.pool_partido: fuera los «que gane X» si X no se juega nada y su rival sí (Suiza–Escocia,
Eslovaquia en Kazajistán, Malta en Gibraltar…).
"""
import collections
import itertools
import json
from pathlib import Path

RAIZ = Path(__file__).parent
DATOS = RAIZ / "datos"
MAX_PENDIENTES = 3   # con más partidos por jugar en el grupo (ligas largas, Champions) no se calcula
TERMINADO = ("FT", "AET", "PEN", "AWD", "WO")
# Qué significa cada puesto en la Nations League 2026-27 (uefa.com, «all you need to know»; comprobado el 16/11).
# En la A, el 3.º y el 4.º dependen del ranking entre los terceros/cuartos de los 4 grupos. En la D suben todos.
SIGNIFICADO = {
    "League A": {1: "cuartos", 2: "cuartos", 3: "se queda o play-off, según ranking", 4: "play-off o desciende, según ranking"},
    "League B": {1: "sube", 2: "play-off para subir", 3: "se queda", 4: "play-off para no bajar"},
    "League C": {1: "sube", 2: "play-off para subir", 3: "se queda", 4: "se queda"},
    "League D": {1: "sube a la C", 2: "sube a la C", 3: "sube a la C", 4: "sube a la C"},
}
_cache = {}


def _cal(liga):
    if liga not in _cache:
        f = DATOS / f"calendario_{liga}.json"
        try:
            _cache[liga] = json.loads(f.read_text()) if f.exists() else []
        except Exception:
            _cache[liga] = []
    return _cache[liga]


def _tabla(ms, equipos):
    T = {t: dict(p=0, gf=0, gc=0, fuera=0, v=0) for t in equipos}
    for h, a, x, y in ms:
        if h not in T or a not in T:
            continue
        T[h]["gf"] += x; T[h]["gc"] += y; T[a]["gf"] += y; T[a]["gc"] += x; T[a]["fuera"] += y
        if x > y:
            T[h]["p"] += 3; T[h]["v"] += 1
        elif x < y:
            T[a]["p"] += 3; T[a]["v"] += 1
        else:
            T[h]["p"] += 1; T[a]["p"] += 1
    return T


def orden(ms, equipos):
    """Clasificación final con el desempate UEFA (cara a cara primero)."""
    T = _tabla(ms, equipos)
    por_puntos = collections.defaultdict(list)
    for t in equipos:
        por_puntos[T[t]["p"]].append(t)
    res = []
    for pts in sorted(por_puntos, reverse=True):
        g = por_puntos[pts]
        if len(g) > 1:
            H = _tabla(ms, g)
            g = sorted(g, key=lambda t: (-H[t]["p"], -(H[t]["gf"] - H[t]["gc"]), -H[t]["gf"],
                                         -(T[t]["gf"] - T[t]["gc"]), -T[t]["gf"], -T[t]["fuera"], -T[t]["v"]))
        res += g
    return res


def grupo_de(cal, fid):
    """(fase, equipos, jugados [(loc, vis, gl, gv)], pendientes [(fid, loc, vis)]) del grupo del partido, o None."""
    f0 = next((f for f in cal if f["fixture"]["id"] == fid), None)
    if not f0:
        return None
    fase = (f0["league"].get("round") or "").split(" - ")[0]
    if not fase or "play" in fase.lower():
        return None
    mismos = [f for f in cal if (f["league"].get("round") or "").split(" - ")[0] == fase]
    vecinos = collections.defaultdict(set)
    for f in mismos:
        h, a = f["teams"]["home"]["name"], f["teams"]["away"]["name"]
        vecinos[h].add(a); vecinos[a].add(h)
    equipos, pila = set(), [f0["teams"]["home"]["name"]]
    while pila:
        t = pila.pop()
        if t not in equipos:
            equipos.add(t)
            pila += vecinos[t]
    jugados, pend = [], []
    for f in mismos:
        h, a = f["teams"]["home"]["name"], f["teams"]["away"]["name"]
        if h not in equipos:
            continue
        if f["fixture"]["status"]["short"] in TERMINADO and f["goals"]["home"] is not None:
            jugados.append((h, a, f["goals"]["home"], f["goals"]["away"]))
        else:
            pend.append((f["fixture"]["id"], h, a))
    return fase, sorted(equipos), jugados, pend


def _viejo(liga, pend, horas=3):
    from datetime import datetime, timedelta, timezone
    ahora = datetime.now(timezone.utc)
    fechas = {f["fixture"]["id"]: f["fixture"]["date"] for f in _cal(liga)}
    try:
        return any(datetime.fromisoformat(fechas[p[0]]) < ahora - timedelta(hours=horas) for p in pend)
    except Exception:
        return False


def puestos(liga, fid):
    """{equipo: {"G": {puestos}, "E": {...}, "P": {...}}} de los dos equipos del partido, o None si no se puede."""
    g = grupo_de(_cal(liga), fid)
    if not g:
        return None
    fase, equipos, jugados, pend = g
    if not pend or len(pend) > MAX_PENDIENTES or len(equipos) > 6 or fid not in {p[0] for p in pend}:
        return None
    if _viejo(liga, pend):   # un partido del grupo ya jugado sin su resultado en el calendario: no se adivina
        return None
    marc = [(x, y) for x in range(5 if len(pend) <= 2 else 4) for y in range(5 if len(pend) <= 2 else 4)]
    _, loc, vis = next(p for p in pend if p[0] == fid)
    out = {loc: collections.defaultdict(set), vis: collections.defaultdict(set)}
    for combo in itertools.product(marc, repeat=len(pend)):
        ms = jugados + [(h, a, x, y) for (_, h, a), (x, y) in zip(pend, combo)]
        o = orden(ms, equipos)
        x, y = next(c for p, c in zip(pend, combo) if p[0] == fid)
        out[loc]["G" if x > y else "E" if x == y else "P"].add(o.index(loc) + 1)
        out[vis]["G" if y > x else "E" if x == y else "P"].add(o.index(vis) + 1)
    return {"fase": fase, "equipos": {t: {k: sorted(v) for k, v in d.items()} for t, d in out.items()}}


def estado(pos, fase=None):
    """«nada» / «se_juega» / «poco» a partir de {"G": [..], "E": [..], "P": [..]}. Con la fase, lo que cuenta es
    lo que SIGNIFICA el puesto (16/11: en la Liga C el 3.º y el 4.º se quedan igual; en la D suben todos)."""
    todos = set().union(*map(set, pos.values()))
    sig = SIGNIFICADO.get(fase or "", {})
    if len(todos) == 1 or len({sig.get(x, x) for x in todos}) == 1:
        return "nada"
    g, p = pos.get("G") or [9], pos.get("P") or [9]
    return "se_juega" if min(g) < min(p) or max(g) < max(p) else "poco"


def _rango(v):
    return f"{v[0]}.º" if len(v) == 1 else f"{v[0]}.º-{v[-1]}.º"


def texto(fase, pos):
    """«Ya es 1.º (sube) pase lo que pase» / «gana: 2.º · empata: 2.º · pierde: 2.º-3.º»."""
    sig = SIGNIFICADO.get(fase, {})
    todos = sorted(set().union(*map(set, pos.values())))
    if len(todos) == 1:
        s = sig.get(todos[0])
        return f"ya es {todos[0]}.º{f' ({s})' if s else ''} pase lo que pase"
    if len({sig.get(x, x) for x in todos}) == 1:
        return f"{_rango(todos)}: {sig[todos[0]]} pase lo que pase"
    def con_sig(v):
        ss = {sig.get(x) for x in v}
        return _rango(v) + (f" ({ss.pop()})" if len(ss) == 1 and None not in ss else "")
    return " · ".join(f"{n}: {con_sig(pos[k])}" for k, n in (("G", "gana"), ("E", "empata"), ("P", "pierde")) if pos.get(k))


# 16/11 (Marcos: «igual en la Champions, en las ligas…»): en competiciones largas no se prueban todos los
# resultados; se mira si al equipo aún le cambia la ZONA (título, Champions, Europa, descenso / top 8, play-off…)
# con los puntos que quedan en juego. Al principio de temporada todo está abierto: casi siempre «se_juega».
ZONAS = {2: (8, 24), 3: (8, 24), 848: (8, 24),                      # fase liga: top 8 · 9-24 play-off · fuera
         140: (1, 4, 6, 7, 17), 39: (1, 4, 6, 7, 17), 135: (1, 4, 6, 7, 17),
         78: (1, 4, 6, 7, 15, 16), 61: (1, 3, 4, 5, 6, 15, 16), 94: (1, 2, 3, 5, 15, 16), 88: (1, 2, 3, 7, 15, 16),
         141: (1, 2, 6, 18), 40: (1, 2, 6, 21)}
NOMBRE_ZONA = {2: ("top 8", "play-off", "fuera"), 3: ("top 8", "play-off", "fuera"), 848: ("top 8", "play-off", "fuera")}


def por_zonas(liga, fid):
    """{"fase", "equipos": {nombre: (mejor_puesto, peor_puesto, zona_mejor, zona_peor)}} con los puntos que quedan."""
    if liga not in ZONAS:
        return None
    cal = _cal(liga)
    f0 = next((f for f in cal if f["fixture"]["id"] == fid), None)
    if not f0:
        return None
    fase = (f0["league"].get("round") or "").split(" - ")[0]
    mismos = [f for f in cal if (f["league"].get("round") or "").split(" - ")[0] == fase]
    pts, quedan = collections.Counter(), collections.Counter()
    for f in mismos:
        h, a = f["teams"]["home"]["name"], f["teams"]["away"]["name"]
        pts[h] += 0; pts[a] += 0
        if f["fixture"]["status"]["short"] in TERMINADO and f["goals"]["home"] is not None:
            x, y = f["goals"]["home"], f["goals"]["away"]
            pts[h] += 3 if x > y else 1 if x == y else 0
            pts[a] += 3 if y > x else 1 if x == y else 0
        else:
            quedan[h] += 1; quedan[a] += 1
    cortes = ZONAS[liga]
    zona = lambda pos: sum(1 for c in cortes if pos > c)
    out = {}
    for t in (f0["teams"]["home"]["name"], f0["teams"]["away"]["name"]):
        tope = pts[t] + 3 * quedan[t]
        mejor = 1 + sum(1 for o in pts if o != t and pts[o] > tope)
        peor = 1 + sum(1 for o in pts if o != t and pts[o] + 3 * quedan[o] >= pts[t])
        out[t] = (mejor, peor, zona(mejor), zona(peor))
    return {"fase": fase, "equipos": out}


def contexto(liga, fid):
    """{"local": {...}, "visitante": {...}} con estado y texto de cada uno, o None."""
    r = puestos(liga, fid)
    if not r:
        z = por_zonas(liga, fid)
        if not z:
            return None
        cal = _cal(liga)
        f = next(x for x in cal if x["fixture"]["id"] == fid)
        out = {}
        for lado, k in (("local", "home"), ("visitante", "away")):
            nom = f["teams"][k]["name"]
            mejor, peor, zm, zp = z["equipos"][nom]
            nz = NOMBRE_ZONA.get(liga)
            fija = (nz[zm] if nz and zm < len(nz) else f"zona {zm + 1}")
            out[lado] = {"equipo": nom, "estado": "nada" if zm == zp else "se_juega",
                         "texto": (f"ya tiene asegurado «{fija}» (entre {mejor}.º y {peor}.º)" if zm == zp
                                   else f"puede acabar entre {mejor}.º y {peor}.º")}
        return out
    cal = _cal(liga)
    f = next(x for x in cal if x["fixture"]["id"] == fid)
    out = {}
    for lado, k in (("local", "home"), ("visitante", "away")):
        nom = f["teams"][k]["name"]
        pos = r["equipos"][nom]
        out[lado] = {"equipo": nom, "estado": estado(pos, r["fase"]), "texto": texto(r["fase"], pos), "puestos": pos}
    return out


def de_partido(fid):
    """contexto() buscando el partido en todos los calendarios (para la app, que no sabe el id de la liga)."""
    for f in DATOS.glob("calendario_*.json"):
        try:
            liga = int(f.stem.split("_")[1])
        except ValueError:
            continue
        if any(x["fixture"]["id"] == fid for x in _cal(liga)):
            return contexto(liga, fid)
    return None


def sin_motivo(liga, fid, lado):
    """True si el equipo de ese lado («local»/«visitante») no se juega nada y el rival sí: no se le da ganador."""
    try:
        c = contexto(liga, fid)
    except Exception as e:
        print("que_se_juegan:", str(e)[:120])
        return False
    if not c:
        return False
    otro = "visitante" if lado == "local" else "local"
    return c[lado]["estado"] == "nada" and c[otro]["estado"] == "se_juega"


if __name__ == "__main__":
    import sys
    liga = int(sys.argv[1]) if len(sys.argv) > 1 else 5
    for f in _cal(liga):
        if f["fixture"]["status"]["short"] in TERMINADO:
            continue
        c = contexto(liga, f["fixture"]["id"])
        if c:
            print(f"{f['fixture']['date'][:16]} {c['local']['equipo']} – {c['visitante']['equipo']}")
            for lado in ("local", "visitante"):
                print(f"   {c[lado]['equipo']}: [{c[lado]['estado']}] {c[lado]['texto']}")
