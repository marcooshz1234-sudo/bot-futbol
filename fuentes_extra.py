"""
09/11 (Marcos: «todo»): fuentes de datos extra, gratis, que se leen desde GitHub (aquí no hay internet).

(13/11: quitados ClubElo y la prueba con Football-Data.co.uk, que no usaba nadie.)
OddsPapi (si Marcos pone la clave en el secreto ODDSPAPI_KEY de GitHub): cuotas de Pinnacle, Betfair
   y bet365 de los partidos del día → datos/cuotas_sharp.json (plan gratis: pocas peticiones, se gastan
   como mucho 7 al día).
"""
import json
import os
import re
import sys
import time
import unicodedata
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import urllib.request

from bot import DATOS, MADRID, leer



def bajar(url, intentos=3):
    for i in range(intentos):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "combilocas-bot"}),
                                        timeout=40) as r:
                return r.read()
        except Exception as e:
            cuerpo = ""
            try:
                cuerpo = e.read().decode("utf-8", "ignore")[:300]   # el motivo del error (HTTP 4xx)
            except Exception:
                pass
            # 09/11: NUNCA la clave en los logs (repo público): se tapa el apiKey
            print(f"  {re.sub(r'apiKey=[^&]+', 'apiKey=***', url)}: {e} {cuerpo}")
            codigo = getattr(e, "code", None)
            if codigo == 429:            # 09/11: OddsPapi pide esperar un poco
                time.sleep(1.5)
                continue
            if codigo and 400 <= codigo < 500:
                return None              # 403/404: reintentar solo gasta peticiones del plan gratis
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
# ---------------------------------------------------------------- 2) Football-Data.co.uk
# ---------------------------------------------------------------- 3) OddsPapi (con clave)
API_OP = "https://api.oddspapi.io/v4"


def _op(ruta, clave, **kw):
    b = bajar(f"{API_OP}/{ruta}?" + "&".join(f"{k}={v}" for k, v in dict(kw, apiKey=clave).items()))
    return json.loads(b) if b else None


def _lista(x):
    return x if isinstance(x, list) else (x or {}).get("data") or (x or {}).get("fixtures") or []


def oddspapi():
    """Plan gratis (250 peticiones/mes): equipos (1 vez por semana), partidos de hoy (1) y cuotas de Pinnacle,
    bet365 y Betfair de hasta 5 partidos nuestros (5) → ≈7 al día. Se casa por nombre de equipo."""
    clave = os.environ.get("ODDSPAPI_KEY")
    if not clave:
        print("OddsPapi: sin clave (secreto ODDSPAPI_KEY), no se usa")
        return
    hoy = datetime.now(MADRID)
    ruta = DATOS / "cuotas_sharp.json"
    if (leer(ruta, {}) or {}).get("dia") == hoy.strftime("%Y-%m-%d"):
        print("OddsPapi: ya está el de hoy")
        return
    usadas = 0
    eq_ruta = DATOS / "oddspapi_equipos.json"
    eq = leer(eq_ruta, {}) or {}
    if not eq.get("equipos") or eq.get("dia", "") < (hoy - timedelta(days=7)).strftime("%Y-%m-%d"):
        r = _op("participants", clave, sportId=10)
        usadas += 1
        lst = r if isinstance(r, list) else (r or {}).get("data") if isinstance((r or {}).get("data"), list) else None
        if isinstance(r, dict) and not lst:   # {id: nombre}
            eq = {"dia": hoy.strftime("%Y-%m-%d"), "equipos": {str(k): v if isinstance(v, str) else
                                                                (v or {}).get("name") for k, v in r.items()}}
        elif lst:
            eq = {"dia": hoy.strftime("%Y-%m-%d"),
                  "equipos": {str(x.get("participantId") or x.get("id")): x.get("participantName") or x.get("name")
                              for x in lst}}
        else:
            print("OddsPapi participants:", str(r)[:300])
        escribir(eq_ruta, eq)
    nombres = eq.get("equipos") or {}
    print("OddsPapi: equipos", len(nombres))
    fx = _op("fixtures", clave, sportId=10, **{"from": hoy.strftime("%Y-%m-%d"),
                                                "to": (hoy + timedelta(days=1)).strftime("%Y-%m-%d")})
    usadas += 1
    fixtures = _lista(fx)
    # 09/11: solo partidos que no han empezado (≥30 min) y con cuotas (los de en directo dan 403 en el plan gratis)
    limite = (datetime.now(MADRID) + timedelta(minutes=30)).astimezone(ZoneInfo("UTC")).strftime("%Y-%m-%dT%H:%M")
    fixtures = [x for x in fixtures if x.get("hasOdds") is not False and not x.get("trueStartTime")
                and (x.get("startTime") or "") >= limite]
    print("OddsPapi: partidos", len(fixtures), (json.dumps(fixtures[0])[:300] if fixtures else str(fx)[:300]))
    import combis_dia as C
    nuestros = []
    for f in C.EXTRA.glob("*.json"):
        pa = (leer(f) or {}).get("partido")
        if pa and pa["fixture"]["date"][:10] == hoy.strftime("%Y-%m-%d") and pa["fixture"]["status"]["short"] == "NS" \
                and datetime.fromisoformat(pa["fixture"]["date"]) > datetime.now(MADRID) + timedelta(minutes=30):
            nuestros.append(pa)
    nuestros.sort(key=lambda pa: pa["league"]["id"] not in (2, 3, 848, 140, 39, 135, 78, 61, 5, 141))
    salida = {"dia": hoy.strftime("%Y-%m-%d"), "partidos": {}}
    for pa in nuestros:
        if usadas >= 7:
            break
        l, v = norm(pa["teams"]["home"]["name"]), norm(pa["teams"]["away"]["name"])

        def nom(x, k):
            return norm(x.get(f"participant{k}Name") or nombres.get(str(x.get(f"participant{k}Id"))) or "")
        m = next((x for x in fixtures if (l[:5] in nom(x, 1) or nom(x, 1)[:5] in l)
                  and (v[:5] in nom(x, 2) or nom(x, 2)[:5] in v) and nom(x, 1) and nom(x, 2)), None)
        if not m:
            continue
        fid = m.get("fixtureId") or m.get("id")
        r = _op("odds", clave, fixtureId=fid, bookmakers="pinnacle,bet365,betfair-ex")
        usadas += 1
        time.sleep(1.2)   # sin pasarse del límite por segundo
        if r:
            salida["partidos"][str(pa["fixture"]["id"])] = {"oddspapi": fid, "cuotas": r}
            if len(salida["partidos"]) == 1:
                print("OddsPapi: ejemplo de cuotas", json.dumps(r)[:400])
    escribir(ruta, salida)
    print(f"OddsPapi: {len(salida['partidos'])} partidos con cuotas, {usadas} peticiones")


if __name__ == "__main__":
    try:
        oddspapi()
    except Exception as e:
        print(f"oddspapi falló: {e}", file=sys.stderr)
