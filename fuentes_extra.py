"""
09/11 (Marcos: «todo»): fuentes de datos extra, gratis, que se leen desde GitHub (aquí no hay internet).

1) ClubElo (api.clubelo.com): la fuerza Elo de cada equipo europeo → datos/clubelo.json
2) Football-Data.co.uk: resultados y cuotas de temporadas pasadas (bet365 y Pinnacle de cierre) de las
   5 grandes → datos/historico/*.csv; y la prueba «¿cuánto ganan de verdad los favoritos de bet365 según su
   cuota? ¿y cuando Pinnacle los ve mejor que bet365?» → datos/historico_prueba.json
3) OddsPapi (si Marcos pone la clave en el secreto ODDSPAPI_KEY de GitHub): cuotas de Pinnacle, Betfair
   y bet365 de los partidos del día → datos/cuotas_sharp.json (plan gratis: pocas peticiones, se gastan
   como mucho 7 al día).
Cada parte va por separado: si una falla, las otras siguen.
"""
import csv
import io
import json
import os
import sys
import time
import unicodedata
from datetime import datetime, timedelta
from pathlib import Path

import urllib.request

from bot import DATOS, MADRID, leer

HIST = DATOS / "historico"
LIGAS_FD = {"SP1": "LaLiga", "E0": "Premier League", "I1": "Serie A", "D1": "Bundesliga", "F1": "Ligue 1"}
TEMPORADAS_FD = ("2223", "2324", "2425", "2526")


def bajar(url, intentos=3):
    for i in range(intentos):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "combilocas-bot"}),
                                        timeout=40) as r:
                return r.read()
        except Exception as e:
            print(f"  {url}: {e}")
            time.sleep(3 * (i + 1))
    return None


def escribir(ruta, datos):
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text(json.dumps(datos, ensure_ascii=False, indent=1), encoding="utf-8")


def norm(s):
    s = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode().lower()
    for x in (" fc", "fc ", " cf", "cf ", "afc ", " afc", "ac ", "as ", "1. ", "sc ", " sc", "ssc ", "vfb ", "vfl ",
              "rcd ", "real club ", "club "):
        s = s.replace(x, " ")
    return " ".join(s.replace(".", " ").replace("-", " ").split())


# ---------------------------------------------------------------- 1) ClubElo
def clubelo():
    hoy = datetime.now(MADRID).strftime("%Y-%m-%d")
    ruta = DATOS / "clubelo.json"
    if (leer(ruta, {}) or {}).get("dia") == hoy:
        print("ClubElo: ya está el de hoy")
        return
    b = bajar(f"http://api.clubelo.com/{hoy}")
    if not b:   # 09/11: a medianoche de Madrid ClubElo aún no tiene el día (502) → el de ayer
        b = bajar(f"http://api.clubelo.com/{(datetime.now(MADRID) - timedelta(days=1)).strftime('%Y-%m-%d')}")
        hoy = None if b else hoy
    if not b:
        return
    elo = {}
    for f in csv.DictReader(io.StringIO(b.decode("utf-8", "ignore"))):
        try:
            elo[f["Club"]] = {"elo": round(float(f["Elo"]), 1), "pais": f.get("Country"), "nivel": f.get("Level")}
        except (KeyError, ValueError):
            pass
    escribir(ruta, {"dia": hoy, "equipos": elo})
    print(f"ClubElo: {len(elo)} equipos")


def elo_de(nombre, tabla=None):
    """Elo de un equipo por su nombre de API-Football (None si no se encuentra)."""
    tabla = tabla or (leer(DATOS / "clubelo.json", {}) or {}).get("equipos") or {}
    n = norm(nombre)
    for k, v in tabla.items():
        if norm(k) == n:
            return v["elo"]
    for k, v in tabla.items():   # «Man City» / «Manchester City», «Bayern» / «Bayern Munich»…
        a, b = norm(k), n
        if len(a) >= 4 and (a in b or b in a):
            return v["elo"]
    return None


def prob_elo(elo_l, elo_v, ventaja_casa=65):
    """Probabilidad de que gane el local (sin empates) según Elo."""
    return 1 / (1 + 10 ** (-((elo_l + ventaja_casa) - elo_v) / 400))


# ---------------------------------------------------------------- 2) Football-Data.co.uk
def football_data():
    HIST.mkdir(parents=True, exist_ok=True)
    for t in TEMPORADAS_FD:
        for liga in LIGAS_FD:
            ruta = HIST / f"{liga}_{t}.csv"
            if ruta.exists() and t != TEMPORADAS_FD[-1]:
                continue   # las temporadas acabadas no cambian
            b = bajar(f"https://www.football-data.co.uk/mmz4281/{t}/{liga}.csv")
            if b:
                ruta.write_bytes(b)
    print("Football-Data:", len(list(HIST.glob("*.csv"))), "ficheros")


def prueba_historico():
    """¿Cuánto ganan los favoritos de bet365 según su cuota? ¿Y si Pinnacle (cierre) los ve mejor?"""
    tramos = [(1.0, 1.3), (1.3, 1.5), (1.5, 1.8), (1.8, 2.1), (2.1, 2.5)]
    res = {f"{a:.1f}-{b:.1f}": {"n": 0, "gana": 0, "beneficio": 0.0} for a, b in tramos}
    valor = {"n": 0, "gana": 0, "beneficio": 0.0}      # Pinnacle le da más probabilidad que bet365 (+3 puntos)
    sin_valor = {"n": 0, "gana": 0, "beneficio": 0.0}
    for ruta in sorted(HIST.glob("*.csv")):
        for f in csv.DictReader(io.StringIO(ruta.read_text("latin-1"))):
            try:
                b = {k: float(f[f"B365{k}"]) for k in "HDA"}
                ftr = f["FTR"]
            except (KeyError, ValueError):
                continue
            try:
                p = {k: float(f.get(f"PSC{k}") or f.get(f"PS{k}")) for k in "HDA"}
            except (TypeError, ValueError):
                p = None
            fav = min(("H", "A"), key=lambda k: b[k])
            c = b[fav]
            gano = ftr == fav
            for (a, bb), k in zip(tramos, res):
                if a <= c < bb:
                    r = res[k]
                    r["n"] += 1
                    r["gana"] += gano
                    r["beneficio"] += (c - 1) if gano else -1
            if p and 1.6 <= c <= 2.5:
                prob_p = (1 / p[fav]) / sum(1 / v for v in p.values())
                prob_b = (1 / c) / sum(1 / v for v in b.values())
                d = valor if prob_p - prob_b >= 0.03 else sin_valor
                d["n"] += 1
                d["gana"] += gano
                d["beneficio"] += (c - 1) if gano else -1
    for d in list(res.values()) + [valor, sin_valor]:
        if d["n"]:
            d["acierto"] = round(d["gana"] / d["n"], 3)
            d["rentabilidad"] = round(d["beneficio"] / d["n"], 3)
            d["beneficio"] = round(d["beneficio"], 1)
    salida = {"generado": datetime.now(MADRID).strftime("%Y-%m-%d %H:%M"), "favoritos_bet365_por_cuota": res,
              "favorito_1.6-2.5_pinnacle_lo_ve_mejor": valor, "favorito_1.6-2.5_resto": sin_valor}
    escribir(DATOS / "historico_prueba.json", salida)
    print(json.dumps(salida, ensure_ascii=False, indent=1))


# ---------------------------------------------------------------- 3) OddsPapi (con clave)
def oddspapi():
    clave = os.environ.get("ODDSPAPI_KEY")
    if not clave:
        print("OddsPapi: sin clave (secreto ODDSPAPI_KEY), no se usa")
        return
    hoy = datetime.now(MADRID)
    ruta = DATOS / "cuotas_sharp.json"
    viejo = leer(ruta, {}) or {}
    if viejo.get("dia") == hoy.strftime("%Y-%m-%d"):
        print("OddsPapi: ya está el de hoy")
        return
    base = "https://api.oddspapi.io/v4"
    q = lambda ruta_, **kw: bajar(f"{base}/{ruta_}?" + "&".join(f"{k}={v}" for k, v in dict(kw, apiKey=clave).items()))
    b = q("fixtures", sportId=10, **{"from": hoy.strftime("%Y-%m-%d"), "to": (hoy + timedelta(days=1)).strftime("%Y-%m-%d")})
    if not b:
        return
    fixtures = json.loads(b)
    fixtures = fixtures if isinstance(fixtures, list) else fixtures.get("data") or []
    # los partidos del día que tenemos (de las grandes primero): se casan por nombre
    import combis_dia as C
    nuestros = []
    for f in C.EXTRA.glob("*.json"):
        pa = (leer(f) or {}).get("partido")
        if pa and pa["fixture"]["date"][:10] == hoy.strftime("%Y-%m-%d") and pa["fixture"]["status"]["short"] == "NS":
            nuestros.append(pa)
    nuestros.sort(key=lambda pa: pa["league"]["id"] not in (2, 3, 848, 140, 39, 135, 78, 61, 5))
    salida = {"dia": hoy.strftime("%Y-%m-%d"), "partidos": {}}
    usadas = 1
    for pa in nuestros:
        if usadas >= 7:
            break
        l, v = norm(pa["teams"]["home"]["name"]), norm(pa["teams"]["away"]["name"])
        m = next((x for x in fixtures if l[:5] in norm(x.get("participant1Name") or x.get("homeName") or "")
                  and v[:5] in norm(x.get("participant2Name") or x.get("awayName") or "")), None)
        if not m:
            continue
        fid = m.get("fixtureId") or m.get("id")
        b = q("odds", fixtureId=fid, bookmakers="pinnacle,bet365,betfair-ex")
        usadas += 1
        if b:
            salida["partidos"][str(pa["fixture"]["id"])] = {"oddspapi": fid, "cuotas": json.loads(b)}
    escribir(ruta, salida)
    print(f"OddsPapi: {len(salida['partidos'])} partidos, {usadas} peticiones")


if __name__ == "__main__":
    for paso in (clubelo, football_data, prueba_historico, oddspapi):
        try:
            paso()
        except Exception as e:
            print(f"{paso.__name__} falló: {e}", file=sys.stderr)
