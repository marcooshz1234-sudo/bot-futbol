"""
Bot de fútbol: recoge datos de API-Football y genera informes de los próximos partidos.

Competiciones: LaLiga, Premier League, Serie A, Bundesliga, Ligue 1,
Champions League, Europa League y Conference League.

Se ejecuta solo en GitHub Actions. Guarda lo descargado en datos/ para no
volver a pedir nunca un partido ya jugado, y escribe los informes en informes/.
"""

import json
import os
import re
import sys
import time
import unicodedata
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

# ---------------------------------------------------------------- ajustes

TEMPORADA = int(os.environ.get("TEMPORADA", "2026"))
DIAS_VISTA = int(os.environ.get("DIAS_VISTA", "8"))          # próximos días a analizar
MAX_PETICIONES = int(os.environ.get("MAX_PETICIONES", "3000"))  # tope por ejecución
HORAS_REFRESCO = 6                                             # cuotas y lesiones
BET365 = 8                                                     # id de Bet365 en API-Football

COMPETICIONES = {
    140: "LaLiga",
    39: "Premier League",
    135: "Serie A",
    78: "Bundesliga",
    61: "Ligue 1",
    2: "Champions League",
    3: "Europa League",
    848: "Conference League",
}

TERMINADOS = {"FT", "AET", "PEN"}
BASE = "https://v3.football.api-sports.io"
RAIZ = Path(__file__).resolve().parent
DATOS = RAIZ / "datos"
PARTIDOS = DATOS / "partidos"
EXTRA = DATOS / "proximos"
INFORMES = RAIZ / "informes"
try:
    from zoneinfo import ZoneInfo
    MADRID = ZoneInfo("Europe/Madrid")  # hora peninsular, con cambio de horario
except Exception:  # pragma: no cover
    MADRID = timezone(timedelta(hours=1))

# ---------------------------------------------------------------- API


class API:
    def __init__(self, clave):
        self.clave = clave
        self.usadas = 0
        self.restantes = None

    def get(self, ruta, **params):
        if self.usadas >= MAX_PETICIONES:
            raise LimiteAlcanzado()
        url = f"{BASE}/{ruta}?{urlencode(params)}"
        for intento in range(4):
            req = Request(url, headers={"x-apisports-key": self.clave})
            try:
                with urlopen(req, timeout=40) as r:
                    datos = json.loads(r.read().decode("utf-8"))
                    rest = r.headers.get("x-ratelimit-requests-remaining")
                    if rest is not None:
                        self.restantes = int(rest)
            except (HTTPError, URLError, TimeoutError) as e:
                print(f"  ! error de red en {ruta}: {e}; reintento")
                time.sleep(3 + intento * 5)
                continue
            self.usadas += 1
            errores = datos.get("errors")
            if errores and (isinstance(errores, dict) and errores or isinstance(errores, list) and errores):
                texto = json.dumps(errores, ensure_ascii=False)
                if "rateLimit" in texto or "Too many requests" in texto:
                    print("  ! límite por minuto, espero 60 s")
                    time.sleep(61)
                    continue
                if "requests" in texto and "limit" in texto.lower():
                    raise LimiteAlcanzado()
                print(f"  ! la API devolvió errores en {ruta} {params}: {texto}")
                return []
            time.sleep(0.25)
            return datos.get("response") or []
        print(f"  ! sin respuesta tras varios intentos: {ruta} {params}")
        return []


class LimiteAlcanzado(Exception):
    pass


# ---------------------------------------------------------------- utilidades


def leer(ruta, defecto=None):
    try:
        return json.loads(Path(ruta).read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return defecto


def escribir(ruta, datos):
    ruta = Path(ruta)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text(json.dumps(datos, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")


def ahora():
    return datetime.now(timezone.utc)


def fecha(iso):
    return datetime.fromisoformat(iso.replace("Z", "+00:00"))


def num(v):
    """Convierte valores de la API ('55%', None, '1.23') en número."""
    if v is None:
        return None
    if isinstance(v, (int, float)):
        return v
    try:
        return float(str(v).replace("%", "").strip())
    except ValueError:
        return None


def slug(texto):
    t = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", t.lower()).strip("-")


def media(valores, dec=1):
    v = [x for x in valores if x is not None]
    return round(sum(v) / len(v), dec) if v else None


def pct(cond, total):
    return f"{round(100 * cond / total)}%" if total else "–"


def f(v, dec=1):
    if v is None:
        return "–"
    if isinstance(v, float):
        return f"{v:.{dec}f}".replace(".", ",")
    return str(v)


# ---------------------------------------------------------------- recogida


STATS_CLAVE = {
    "Corner Kicks": "corners",
    "Total Shots": "tiros",
    "Shots on Goal": "a_puerta",
    "Fouls": "faltas",
    "Yellow Cards": "amarillas",
    "Red Cards": "rojas",
    "Ball Possession": "posesion",
    "Offsides": "fueras_juego",
    "expected_goals": "xg",
    "Goalkeeper Saves": "paradas",
}


def recortar_partido(p):
    """Se queda solo con lo que usan los informes, para que los datos ocupen poco."""
    fx, tm = p["fixture"], p["teams"]
    reg = {
        "id": fx["id"],
        "fecha": fx["date"],
        "estado": fx["status"]["short"],
        "liga": p["league"]["id"],
        "jornada": p["league"].get("round"),
        "local": {"id": tm["home"]["id"], "nombre": tm["home"]["name"]},
        "visitante": {"id": tm["away"]["id"], "nombre": tm["away"]["name"]},
        "goles": [p["goals"]["home"], p["goals"]["away"]],
        "descanso": [p["score"]["halftime"]["home"], p["score"]["halftime"]["away"]],
        "stats": {},
        "eventos": [],
        "jugadores": {},
    }
    for bloque in p.get("statistics") or []:
        d = {}
        for s in bloque.get("statistics") or []:
            if s.get("type") in STATS_CLAVE:
                d[STATS_CLAVE[s["type"]]] = num(s.get("value"))
        reg["stats"][str(bloque["team"]["id"])] = d
    for e in p.get("events") or []:
        if e.get("type") not in ("Goal", "Card"):
            continue
        if "shootout" in str(e.get("comments") or "").lower():
            continue
        reg["eventos"].append({
            "min": (e.get("time") or {}).get("elapsed"),
            "extra": (e.get("time") or {}).get("extra"),
            "equipo": (e.get("team") or {}).get("id"),
            "tipo": e["type"],
            "detalle": e.get("detail"),
            "jugador": (e.get("player") or {}).get("name"),
        })
    for bloque in p.get("players") or []:
        lista = []
        for j in bloque.get("players") or []:
            s = (j.get("statistics") or [{}])[0]
            g = s.get("games") or {}
            lista.append({
                "id": j["player"]["id"],
                "nombre": j["player"]["name"],
                "min": g.get("minutes") or 0,
                "pos": g.get("position"),
                "goles": (s.get("goals") or {}).get("total") or 0,
                "asist": (s.get("goals") or {}).get("assists") or 0,
                "tiros": (s.get("shots") or {}).get("total") or 0,
                "a_puerta": (s.get("shots") or {}).get("on") or 0,
                "faltas_c": (s.get("fouls") or {}).get("committed") or 0,
                "faltas_r": (s.get("fouls") or {}).get("drawn") or 0,
                "amarillas": (s.get("cards") or {}).get("yellow") or 0,
                "rojas": (s.get("cards") or {}).get("red") or 0,
                "paradas": (s.get("goals") or {}).get("saves") or 0,
            })
        reg["jugadores"][str(bloque["team"]["id"])] = lista
    return reg


def extraer_corners_por_parte(resp):
    """Lee la respuesta de fixtures/statistics?half=true y saca córners por parte.

    Se busca en cualquier lista de estadísticas que traiga la respuesta, para no
    depender del nombre exacto del campo."""
    salida = {}
    for bloque in resp or []:
        eq = str((bloque.get("team") or {}).get("id"))
        d = {}
        for clave, valor in bloque.items():
            if not isinstance(valor, list):
                continue
            for s in valor:
                if isinstance(s, dict) and s.get("type") == "Corner Kicks":
                    d[clave] = num(s.get("value"))
        salida[eq] = d
    return salida


def recoger(api):
    PARTIDOS.mkdir(parents=True, exist_ok=True)
    EXTRA.mkdir(parents=True, exist_ok=True)
    calendario = {}

    # 1) Calendario completo de cada competición (1 petición por competición)
    for liga, nombre in COMPETICIONES.items():
        lista = api.get("fixtures", league=liga, season=TEMPORADA)
        print(f"- {nombre}: {len(lista)} partidos en el calendario")
        if lista:
            escribir(DATOS / f"calendario_{liga}.json", lista)
        else:
            lista = leer(DATOS / f"calendario_{liga}.json", [])
        for p in lista:
            calendario[p["fixture"]["id"]] = p

    # 2) Partidos terminados que aún no tenemos: detalle completo en lotes de 20
    pendientes = [
        fid for fid, p in calendario.items()
        if p["fixture"]["status"]["short"] in TERMINADOS
        and not (PARTIDOS / f"{fid}.json").exists()
    ]
    pendientes.sort(key=lambda i: calendario[i]["fixture"]["date"], reverse=True)
    print(f"- Partidos terminados nuevos por descargar: {len(pendientes)}")
    nuevos = 0
    for i in range(0, len(pendientes), 20):
        lote = pendientes[i:i + 20]
        for p in api.get("fixtures", ids="-".join(map(str, lote))):
            reg = recortar_partido(p)
            # Córners por parte (1 petición por partido)
            mitades = api.get("fixtures/statistics", fixture=reg["id"], half="true")
            reg["corners_partes"] = extraer_corners_por_parte(mitades)
            if nuevos == 0:
                print("  muestra de estadísticas por parte:",
                      json.dumps(mitades, ensure_ascii=False)[:600])
            escribir(PARTIDOS / f"{reg['id']}.json", reg)
            nuevos += 1
    print(f"- Guardados {nuevos} partidos nuevos")

    # 3) Próximos partidos: lesiones, cuotas Bet365 y enfrentamientos directos
    limite = ahora() + timedelta(days=DIAS_VISTA)
    proximos = [
        p for p in calendario.values()
        if p["fixture"]["status"]["short"] in ("NS", "TBD")
        and ahora() - timedelta(hours=3) < fecha(p["fixture"]["date"]) < limite
    ]
    proximos.sort(key=lambda p: p["fixture"]["date"])
    print(f"- Próximos partidos en {DIAS_VISTA} días: {len(proximos)}")
    for p in proximos:
        fid = p["fixture"]["id"]
        ruta = EXTRA / f"{fid}.json"
        ex = leer(ruta, {})
        reciente = ex.get("actualizado") and ahora() - fecha(ex["actualizado"]) < timedelta(hours=HORAS_REFRESCO)
        if not reciente:
            ex["lesiones"] = [
                {"equipo": l["team"]["id"], "jugador": l["player"]["name"],
                 "tipo": l["player"].get("type"), "motivo": l["player"].get("reason")}
                for l in api.get("injuries", fixture=fid)
            ]
            cuotas = api.get("odds", fixture=fid, bookmaker=BET365)
            if cuotas:
                ex["cuotas"] = recortar_cuotas(cuotas)
                ex["cuotas_hora"] = ahora().isoformat()
            ex["actualizado"] = ahora().isoformat()
        if "h2h" not in ex:
            a, b = p["teams"]["home"]["id"], p["teams"]["away"]["id"]
            ex["h2h"] = [
                {"fecha": h["fixture"]["date"][:10], "liga": h["league"]["name"],
                 "local": h["teams"]["home"]["name"], "visitante": h["teams"]["away"]["name"],
                 "goles": [h["goals"]["home"], h["goals"]["away"]]}
                for h in api.get("fixtures/headtohead", h2h=f"{a}-{b}", last=6)
                if h["fixture"]["status"]["short"] in TERMINADOS
            ]
        ex["partido"] = p
        escribir(ruta, ex)

    # Limpia datos de partidos que ya pasaron
    for ruta in EXTRA.glob("*.json"):
        ex = leer(ruta, {})
        try:
            if fecha(ex["partido"]["fixture"]["date"]) < ahora() - timedelta(hours=6):
                ruta.unlink()
        except (KeyError, TypeError):
            ruta.unlink()
    return proximos


MERCADOS = [
    "Match Winner", "Double Chance", "Both Teams Score", "Goals Over/Under",
    "Goals Over/Under First Half", "Total - Home", "Total - Away",
    "Corners Over Under", "Corners 1x2", "Total Corners", "Cards Over/Under",
    "Home Team Score a Goal", "Away Team Score a Goal", "First Half Winner",
]


def recortar_cuotas(resp):
    bets = {}
    for item in resp:
        for casa in item.get("bookmakers") or []:
            for b in casa.get("bets") or []:
                if b.get("name") in MERCADOS:
                    bets[b["name"]] = [[v.get("value"), v.get("odd")] for v in b.get("values") or []]
    return bets


# ---------------------------------------------------------------- análisis


def partidos_guardados():
    return [leer(r) for r in PARTIDOS.glob("*.json")]


def por_equipo(todos):
    idx = defaultdict(list)
    for p in todos:
        if not p:
            continue
        idx[p["local"]["id"]].append(p)
        idx[p["visitante"]["id"]].append(p)
    for lista in idx.values():
        lista.sort(key=lambda p: p["fecha"], reverse=True)
    return idx


TRAMOS = [(1, 15), (16, 30), (31, 45), (46, 60), (61, 75), (76, 90)]


def tramo(minuto):
    m = minuto or 0
    for a, b in TRAMOS:
        if m <= b:
            return f"{a}-{b}"
    return "76-90"


def goles_por_equipo(p):
    """Devuelve lista de (minuto, id_equipo_que_marca), comprobando el marcador final."""
    goles = [e for e in p["eventos"] if e["tipo"] == "Goal" and e["detalle"] != "Missed Penalty"]
    loc, vis = p["local"]["id"], p["visitante"]["id"]
    otro = {loc: vis, vis: loc}

    def asignar(propio_al_rival):
        res = []
        for e in goles:
            eq = e["equipo"]
            if e["detalle"] == "Own Goal" and propio_al_rival:
                eq = otro.get(eq, eq)
            res.append((e["min"], eq))
        return res

    for opcion in (True, False):
        res = asignar(opcion)
        if [sum(1 for _, q in res if q == loc), sum(1 for _, q in res if q == vis)] == p["goles"]:
            return res
    return asignar(True)


def corners_parte(p, eq):
    d = (p.get("corners_partes") or {}).get(str(eq)) or {}
    p1 = p2 = None
    for clave, v in d.items():
        k = clave.lower()
        if "1" in k or "first" in k:
            p1 = v
        elif "2" in k or "second" in k:
            p2 = v
    if not d:
        return None, None
    return p1 or 0, p2 or 0


def resumen_equipo(eq, partidos):
    n = len(partidos)
    r = defaultdict(list)
    res = []
    goles_tramo_f = defaultdict(int)
    goles_tramo_c = defaultdict(int)
    tarj_tramo = defaultdict(int)
    gf1 = gf2 = gc1 = gc2 = 0
    for p in partidos:
        local = p["local"]["id"] == eq
        rival = p["visitante"] if local else p["local"]
        gf, gc = (p["goles"] if local else p["goles"][::-1])
        hf, hc = (p["descanso"] if local else p["descanso"][::-1])
        res.append("V" if gf > gc else "E" if gf == gc else "D")
        r["gf"].append(gf)
        r["gc"].append(gc)
        r["total"].append(gf + gc)
        r["ambos"].append(gf > 0 and gc > 0)
        if hf is not None and hc is not None:
            gf1 += hf
            gc1 += hc
            gf2 += gf - hf
            gc2 += gc - hc
        mio = p["stats"].get(str(eq)) or {}
        suyo = p["stats"].get(str(rival["id"])) or {}
        for k in ("corners", "tiros", "a_puerta", "faltas", "amarillas", "rojas", "posesion", "xg"):
            a, b = mio.get(k), suyo.get(k)
            # La API deja vacías las tarjetas y córners cuando son 0
            if k in ("amarillas", "rojas", "corners"):
                a = (a or 0) if mio else None
                b = (b or 0) if suyo else None
            r[k].append(a)
            r[k + "_c"].append(b)
        if mio and suyo:
            r["corners_total"].append((mio.get("corners") or 0) + (suyo.get("corners") or 0))
        c1, c2 = corners_parte(p, eq)
        r1, r2 = corners_parte(p, rival["id"])
        r["corners_1p"].append(c1)
        r["corners_2p"].append(c2)
        if c1 is not None and r1 is not None:
            r["corners_total_1p"].append(c1 + r1)
        if c2 is not None and r2 is not None:
            r["corners_total_2p"].append(c2 + r2)
        tarjetas = 0
        for e in p["eventos"]:
            if e["tipo"] == "Card" and e["equipo"] == eq:
                tarj_tramo[tramo(e["min"])] += 1
                tarjetas += 1
        r["tarjetas_eventos"].append(tarjetas)
        for m, q in goles_por_equipo(p):
            (goles_tramo_f if q == eq else goles_tramo_c)[tramo(m)] += 1
    tot = r["total"]
    ct = r["corners_total"]
    return {
        "n": n,
        "forma": "".join(res[:5]),
        "balance": f"{res.count('V')}V {res.count('E')}E {res.count('D')}D",
        "gf": media(r["gf"], 2), "gc": media(r["gc"], 2),
        "gf_1p": round(gf1 / n, 2) if n else None, "gf_2p": round(gf2 / n, 2) if n else None,
        "gc_1p": round(gc1 / n, 2) if n else None, "gc_2p": round(gc2 / n, 2) if n else None,
        "o15": pct(sum(t > 1 for t in tot), n), "o25": pct(sum(t > 2 for t in tot), n),
        "o35": pct(sum(t > 3 for t in tot), n), "btts": pct(sum(r["ambos"]), n),
        "porteria_cero": pct(sum(g == 0 for g in r["gc"]), n),
        "sin_marcar": pct(sum(g == 0 for g in r["gf"]), n),
        "corners": media(r["corners"]), "corners_c": media(r["corners_c"]),
        "corners_total": media(ct),
        "corners_1p": media(r["corners_1p"]), "corners_2p": media(r["corners_2p"]),
        "corners_total_1p": media(r["corners_total_1p"]), "corners_total_2p": media(r["corners_total_2p"]),
        "c_o85": pct(sum(c > 8 for c in ct), len(ct)), "c_o95": pct(sum(c > 9 for c in ct), len(ct)),
        "c_o105": pct(sum(c > 10 for c in ct), len(ct)),
        "tiros": media(r["tiros"]), "tiros_c": media(r["tiros_c"]),
        "a_puerta": media(r["a_puerta"]), "a_puerta_c": media(r["a_puerta_c"]),
        "xg": media(r["xg"], 2), "xg_c": media(r["xg_c"], 2),
        "faltas": media(r["faltas"]), "faltas_c": media(r["faltas_c"]),
        "amarillas": media(r["amarillas"]), "amarillas_c": media(r["amarillas_c"]),
        "rojas": media(r["rojas"], 2),
        "posesion": media(r["posesion"], 0),
        "goles_tramo_f": dict(goles_tramo_f), "goles_tramo_c": dict(goles_tramo_c),
        "tarjetas_tramo": dict(tarj_tramo),
    }


def jugadores_equipo(eq, partidos):
    acc = {}
    for p in partidos:
        for j in p["jugadores"].get(str(eq)) or []:
            if not j["min"]:
                continue
            a = acc.setdefault(j["id"], {"nombre": j["nombre"], "pos": j["pos"], "pj": 0, "min": 0,
                                         "goles": 0, "asist": 0, "tiros": 0, "a_puerta": 0,
                                         "faltas_c": 0, "faltas_r": 0, "amarillas": 0, "rojas": 0})
            a["pj"] += 1
            for k in ("min", "goles", "asist", "tiros", "a_puerta", "faltas_c", "faltas_r", "amarillas", "rojas"):
                a[k] += j[k] or 0
    return sorted(acc.values(), key=lambda a: a["min"], reverse=True)


# ---------------------------------------------------------------- informes


def tabla_equipos(nl, nv, rl, rv, rl_casa, rv_fuera):
    filas = [
        ("Partidos analizados", "n", 0),
        ("Forma (últimos 5)", "forma", 0),
        ("Balance", "balance", 0),
        ("Goles a favor / partido", "gf", 2),
        ("Goles en contra / partido", "gc", 2),
        ("Goles a favor 1ª parte", "gf_1p", 2),
        ("Goles a favor 2ª parte", "gf_2p", 2),
        ("Goles en contra 1ª parte", "gc_1p", 2),
        ("Goles en contra 2ª parte", "gc_2p", 2),
        ("Más de 1,5 goles", "o15", 0),
        ("Más de 2,5 goles", "o25", 0),
        ("Más de 3,5 goles", "o35", 0),
        ("Ambos marcan", "btts", 0),
        ("Portería a cero", "porteria_cero", 0),
        ("Se queda sin marcar", "sin_marcar", 0),
        ("xG a favor", "xg", 2),
        ("xG en contra", "xg_c", 2),
        ("Tiros / partido", "tiros", 1),
        ("Tiros a puerta / partido", "a_puerta", 1),
        ("Tiros recibidos", "tiros_c", 1),
        ("Tiros a puerta recibidos", "a_puerta_c", 1),
        ("Posesión media %", "posesion", 0),
        ("Córners a favor", "corners", 1),
        ("Córners en contra", "corners_c", 1),
        ("Córners a favor 1ª parte", "corners_1p", 1),
        ("Córners a favor 2ª parte", "corners_2p", 1),
        ("Córners totales del partido", "corners_total", 1),
        ("Córners totales 1ª parte", "corners_total_1p", 1),
        ("Córners totales 2ª parte", "corners_total_2p", 1),
        ("Más de 8,5 córners", "c_o85", 0),
        ("Más de 9,5 córners", "c_o95", 0),
        ("Más de 10,5 córners", "c_o105", 0),
        ("Faltas cometidas", "faltas", 1),
        ("Faltas recibidas", "faltas_c", 1),
        ("Amarillas propias", "amarillas", 1),
        ("Amarillas del rival", "amarillas_c", 1),
        ("Rojas / partido", "rojas", 2),
    ]
    out = [f"| | {nl} (total) | {nl} en casa | {nv} (total) | {nv} fuera |",
           "|---|---|---|---|---|"]
    for etiqueta, k, dec in filas:
        out.append(f"| {etiqueta} | " + " | ".join(f(r.get(k), dec) for r in (rl, rl_casa, rv, rv_fuera)) + " |")
    return "\n".join(out)


def tabla_tramos(nl, nv, rl, rv):
    cab = "| Tramo | " + " | ".join([f"Goles {nl}", f"Recibe {nl}", f"Tarjetas {nl}",
                                     f"Goles {nv}", f"Recibe {nv}", f"Tarjetas {nv}"]) + " |"
    out = [cab, "|---|---|---|---|---|---|---|"]
    for a, b in TRAMOS:
        t = f"{a}-{b}"
        vals = [rl["goles_tramo_f"].get(t, 0), rl["goles_tramo_c"].get(t, 0), rl["tarjetas_tramo"].get(t, 0),
                rv["goles_tramo_f"].get(t, 0), rv["goles_tramo_c"].get(t, 0), rv["tarjetas_tramo"].get(t, 0)]
        out.append(f"| {t}' | " + " | ".join(map(str, vals)) + " |")
    out.append("\n_Totales de la temporada (el tramo 76-90 incluye el descuento)._")
    return "\n".join(out)


def tabla_jugadores(lista, maximo=20):
    out = ["| Jugador | Pos | PJ | Min | Goles | Asist | Tiros | Tiros/PJ | A puerta | A puerta/PJ "
           "| Faltas com. | Faltas rec. | Faltas rec./PJ | Amarillas | Rojas |",
           "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for j in lista[:maximo]:
        pj = j["pj"] or 1
        out.append(
            f"| {j['nombre']} | {j['pos'] or ''} | {j['pj']} | {j['min']} | {j['goles']} | {j['asist']} "
            f"| {j['tiros']} | {f(j['tiros'] / pj)} | {j['a_puerta']} | {f(j['a_puerta'] / pj)} "
            f"| {j['faltas_c']} | {j['faltas_r']} | {f(j['faltas_r'] / pj)} | {j['amarillas']} | {j['rojas']} |")
    return "\n".join(out)


def tabla_ultimos(eq, partidos, n=6):
    out = ["| Fecha | Comp. | Partido | Res. | Córners | Tiros (a puerta) | Amarillas |",
           "|---|---|---|---|---|---|---|"]
    for p in partidos[:n]:
        local = p["local"]["id"] == eq
        rival = p["visitante"] if local else p["local"]
        mio = p["stats"].get(str(eq)) or {}
        suyo = p["stats"].get(str(rival["id"])) or {}
        out.append(
            f"| {p['fecha'][:10]} | {COMPETICIONES.get(p['liga'], p['liga'])} "
            f"| {p['local']['nombre']} {p['goles'][0]}-{p['goles'][1]} {p['visitante']['nombre']} "
            f"| {'casa' if local else 'fuera'} "
            f"| {f(mio.get('corners'), 0)}-{f(suyo.get('corners'), 0)} "
            f"| {f(mio.get('tiros'), 0)} ({f(mio.get('a_puerta'), 0)}) - {f(suyo.get('tiros'), 0)} ({f(suyo.get('a_puerta'), 0)}) "
            f"| {f(mio.get('amarillas'), 0)}-{f(suyo.get('amarillas'), 0)} |")
    return "\n".join(out)


TRADUCCION_CUOTAS = {
    "Match Winner": "1X2", "Double Chance": "Doble oportunidad", "Both Teams Score": "Ambos marcan",
    "Goals Over/Under": "Goles más/menos", "Goals Over/Under First Half": "Goles 1ª parte más/menos",
    "Total - Home": "Goles del local", "Total - Away": "Goles del visitante",
    "Corners Over Under": "Córners más/menos", "Corners 1x2": "Córners 1X2", "Total Corners": "Córners totales",
    "Cards Over/Under": "Tarjetas más/menos", "Home Team Score a Goal": "Marca el local",
    "Away Team Score a Goal": "Marca el visitante", "First Half Winner": "1X2 descanso",
}


def traducir_opcion(v):
    t = str(v)
    for en, es in (("Home/Draw", "1X"), ("Home/Away", "12"), ("Draw/Away", "X2"),
                   ("Home", "1"), ("Draw", "X"), ("Away", "2"),
                   ("Over", "Más de"), ("Under", "Menos de"), ("Yes", "Sí"), ("No", "No"),
                   ("Exactly", "Exactamente")):
        if t == en or t.startswith(en + " "):
            return es + t[len(en):]
    return t


def bloque_cuotas(ex):
    cuotas = ex.get("cuotas")
    if not cuotas:
        return "_Bet365 aún no ha publicado cuotas para este partido (suelen salir unos días antes)._"
    out = [f"_Actualizadas: {fecha(ex['cuotas_hora']).astimezone(MADRID).strftime('%d/%m %H:%M')}_\n"]
    for mercado in MERCADOS:
        if mercado not in cuotas:
            continue
        nombre = TRADUCCION_CUOTAS.get(mercado, mercado)
        opciones = cuotas[mercado]
        lineas = agrupar_mas_menos(opciones)
        if lineas:
            out.append(f"- **{nombre}:**")
            for linea, mas, menos in lineas:
                out.append(f"    - {linea}: más **{mas or '–'}** · menos **{menos or '–'}**")
        else:
            vals = "  ·  ".join(f"{traducir_opcion(v)} **{o}**" for v, o in opciones)
            out.append(f"- **{nombre}:** {vals}")
    return "\n".join(out)


def agrupar_mas_menos(opciones):
    """Convierte opciones 'Over 2.5'/'Under 2.5' en filas ordenadas por línea.

    Se omiten las líneas sin interés (cuota de 1.03 o menos en un lado)."""
    filas = {}
    for v, o in opciones:
        m = re.match(r"^(Over|Under)\s+([\d.]+)$", str(v))
        if not m:
            return None
        lado, linea = m.group(1), float(m.group(2))
        filas.setdefault(linea, [None, None])[0 if lado == "Over" else 1] = o
    salida = []
    for linea in sorted(filas):
        mas, menos = filas[linea]
        if any(num(x) is not None and num(x) <= 1.03 for x in (mas, menos)):
            continue
        salida.append((f"{linea:g}".replace(".", ","), mas, menos))
    return salida


def informe(p, ex, idx):
    loc, vis = p["teams"]["home"], p["teams"]["away"]
    pl, pv = idx.get(loc["id"], []), idx.get(vis["id"], [])
    rl, rv = resumen_equipo(loc["id"], pl), resumen_equipo(vis["id"], pv)
    rl_casa = resumen_equipo(loc["id"], [x for x in pl if x["local"]["id"] == loc["id"]])
    rv_fuera = resumen_equipo(vis["id"], [x for x in pv if x["visitante"]["id"] == vis["id"]])
    hora = fecha(p["fixture"]["date"]).astimezone(MADRID)
    lineas = [
        f"# {loc['name']} – {vis['name']}",
        f"**{COMPETICIONES.get(p['league']['id'], p['league']['name'])}** · {p['league'].get('round', '')} · "
        f"{hora.strftime('%d/%m/%Y %H:%M')} (hora España)"
        + (f" · {p['fixture']['venue']['name']}" if (p['fixture'].get('venue') or {}).get('name') else ""),
        "",
        f"_Datos de esta temporada en todas las competiciones analizadas. Generado el "
        f"{ahora().astimezone(MADRID).strftime('%d/%m %H:%M')}._",
        "",
        "## Cuotas Bet365",
        bloque_cuotas(ex),
        "",
        "## Estadísticas de equipo",
        tabla_equipos(loc["name"], vis["name"], rl, rv, rl_casa, rv_fuera),
        "",
        "## Goles y tarjetas por tramos de minutos",
        tabla_tramos(loc["name"], vis["name"], rl, rv),
        "",
        "## Bajas y dudas",
    ]
    lesiones = ex.get("lesiones") or []
    if lesiones:
        for eq in (loc, vis):
            l = [x for x in lesiones if x["equipo"] == eq["id"]]
            if l:
                lineas.append(f"**{eq['name']}:** " + "; ".join(
                    f"{x['jugador']} ({'duda' if x['tipo'] == 'Questionable' else 'baja'}"
                    f"{', ' + x['motivo'] if x.get('motivo') else ''})" for x in l))
    else:
        lineas.append("_Sin bajas comunicadas por ahora._")
    lineas += ["", "## Enfrentamientos directos recientes"]
    if ex.get("h2h"):
        for h in ex["h2h"]:
            lineas.append(f"- {h['fecha']} · {h['liga']}: {h['local']} {h['goles'][0]}-{h['goles'][1]} {h['visitante']}")
    else:
        lineas.append("_Sin precedentes recientes._")
    for eq, partidos in ((loc, pl), (vis, pv)):
        lineas += ["", f"## Últimos partidos de {eq['name']}", tabla_ultimos(eq["id"], partidos),
                   "", f"## Jugadores de {eq['name']}", tabla_jugadores(jugadores_equipo(eq["id"], partidos))]
    return "\n".join(lineas) + "\n"


def generar_informes(proximos):
    idx = por_equipo(partidos_guardados())
    if INFORMES.exists():
        for viejo in INFORMES.glob("*.md"):
            viejo.unlink()
    INFORMES.mkdir(parents=True, exist_ok=True)
    resumen_json = []
    indice = ["# Próximos partidos", "",
              f"_Actualizado el {ahora().astimezone(MADRID).strftime('%d/%m/%Y %H:%M')} (hora España). "
              f"Partidos guardados en la base de datos: {sum(1 for _ in PARTIDOS.glob('*.json'))}._", ""]
    dia_actual = None
    for p in proximos:
        ex = leer(EXTRA / f"{p['fixture']['id']}.json", {})
        hora = fecha(p["fixture"]["date"]).astimezone(MADRID)
        nombre = f"{hora.strftime('%Y-%m-%d')}_{slug(p['teams']['home']['name'])}-vs-{slug(p['teams']['away']['name'])}.md"
        (INFORMES / nombre).write_text(informe(p, ex, idx), encoding="utf-8")
        dia = hora.strftime("%A %d/%m")
        if dia != dia_actual:
            indice += ["", f"## {traducir_dia(dia)}"]
            dia_actual = dia
        cuota = (ex.get("cuotas") or {}).get("Match Winner")
        txt_cuota = " · 1X2: " + " / ".join(o for _, o in cuota) if cuota else ""
        indice.append(f"- {hora.strftime('%H:%M')} · {COMPETICIONES.get(p['league']['id'], '')} · "
                      f"[{p['teams']['home']['name']} – {p['teams']['away']['name']}](informes/{nombre}){txt_cuota}")
        loc, vis = p["teams"]["home"]["id"], p["teams"]["away"]["id"]
        resumen_json.append({
            "id": p["fixture"]["id"], "fecha": p["fixture"]["date"],
            "competicion": COMPETICIONES.get(p["league"]["id"]),
            "local": p["teams"]["home"]["name"], "visitante": p["teams"]["away"]["name"],
            "stats_local": resumen_equipo(loc, idx.get(loc, [])),
            "stats_local_casa": resumen_equipo(loc, [x for x in idx.get(loc, []) if x["local"]["id"] == loc]),
            "stats_visitante": resumen_equipo(vis, idx.get(vis, [])),
            "stats_visitante_fuera": resumen_equipo(vis, [x for x in idx.get(vis, []) if x["visitante"]["id"] == vis]),
            "cuotas_bet365": ex.get("cuotas"), "lesiones": ex.get("lesiones"), "h2h": ex.get("h2h"),
            "informe": f"informes/{nombre}",
        })
    if not proximos:
        indice.append("_No hay partidos en los próximos días._")
    (RAIZ / "PROXIMOS_PARTIDOS.md").write_text("\n".join(indice) + "\n", encoding="utf-8")
    escribir(DATOS / "resumen_proximos.json", resumen_json)
    print(f"- Informes generados: {len(proximos)}")


DIAS = {"Monday": "Lunes", "Tuesday": "Martes", "Wednesday": "Miércoles", "Thursday": "Jueves",
        "Friday": "Viernes", "Saturday": "Sábado", "Sunday": "Domingo"}


def traducir_dia(texto):
    for en, es in DIAS.items():
        texto = texto.replace(en, es)
    return texto


# ---------------------------------------------------------------- inicio


def main():
    clave = os.environ.get("API_FOOTBALL_KEY")
    if not clave:
        sys.exit("Falta la variable API_FOOTBALL_KEY")
    api = API(clave)
    print(f"Temporada {TEMPORADA} · {len(COMPETICIONES)} competiciones")
    try:
        proximos = recoger(api)
    except LimiteAlcanzado:
        print("! Se alcanzó el tope de peticiones; se continúa en la próxima ejecución")
        proximos = []
        limite = ahora() + timedelta(days=DIAS_VISTA)
        for liga in COMPETICIONES:
            for p in leer(DATOS / f"calendario_{liga}.json", []):
                if p["fixture"]["status"]["short"] in ("NS", "TBD") and ahora() < fecha(p["fixture"]["date"]) < limite:
                    proximos.append(p)
        proximos.sort(key=lambda p: p["fixture"]["date"])
    generar_informes(proximos)
    print(f"Peticiones usadas en esta ejecución: {api.usadas}"
          + (f" · restantes hoy: {api.restantes}" if api.restantes is not None else ""))


if __name__ == "__main__":
    main()
