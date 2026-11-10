"""
09/11 (Marcos: «mételas todas»): más cosas que el bot sabe de cada partido de hoy y mañana, aparte de la API:

  - calendario y cansancio: días desde su último partido y días hasta el siguiente (y si es de Champions/Europa)
  - el tiempo en el estadio a la hora del partido (Open-Meteo, gratis y sin clave): lluvia y viento
  - árbitro: tarjetas por partido (de nuestro histórico)
  - movimiento de la cuota de bet365 (1X2) desde que la vimos por primera vez
  - lo que se juega cada uno: líder, colista, zona de descenso (tabla de la liga)
→ datos/contexto_extra.json {id del partido: {...}} y razones(fid, pick) para razones.py.
"""
import json
import urllib.parse
import urllib.request
from datetime import datetime, timedelta

from bot import DATOS, EXTRA, MADRID, leer

SALIDA = DATOS / "contexto_extra.json"
CIUDADES = DATOS / "ciudades.json"
EUROPA = {2: "Champions", 3: "Europa League", 848: "Conference League", 525: "Champions femenina"}


def bajar_json(url):
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "combilocas-bot"}), timeout=25) as r:
            return json.loads(r.read())
    except Exception as e:
        print("  ", url.split("?")[0], e)
        return None


PAIS_ISO = {"Spain": "ES", "England": "GB", "Scotland": "GB", "Italy": "IT", "Germany": "DE", "France": "FR",
            "Portugal": "PT", "Netherlands": "NL", "Belgium": "BE", "Turkey": "TR", "Denmark": "DK", "Romania": "RO",
            "Sweden": "SE", "Norway": "NO", "Switzerland": "CH", "Austria": "AT", "Greece": "GR", "Poland": "PL",
            "Czech-Republic": "CZ", "Croatia": "HR", "Serbia": "RS", "Ukraine": "UA", "Cyprus": "CY", "Israel": "IL"}


def coords(ciudad, cache, pais=None):
    """10/11: la ciudad buscada dentro del país del partido (no la de otro país con el mismo nombre)."""
    if not ciudad:
        return None
    clave = f"{ciudad}|{pais or ''}"
    if clave in cache:
        return cache[clave]
    r = bajar_json("https://geocoding-api.open-meteo.com/v1/search?" + urllib.parse.urlencode(
        {"name": ciudad.split(",")[0], "count": 10, "language": "es"}))
    lista = (r or {}).get("results") or []
    iso = PAIS_ISO.get(pais or "")
    res = next((x for x in lista if iso and x.get("country_code") == iso), None) or (lista[0] if lista and not iso else None)
    cache[clave] = [res["latitude"], res["longitude"]] if res else None
    return cache[clave]


def _viejo(ciudad, cache):
    if ciudad in cache:
        return cache[ciudad]
    r = bajar_json("https://geocoding-api.open-meteo.com/v1/search?" + urllib.parse.urlencode(
        {"name": ciudad.split(",")[0], "count": 1, "language": "es"}))
    res = ((r or {}).get("results") or [None])[0]
    cache[ciudad] = [res["latitude"], res["longitude"]] if res else None
    return cache[ciudad]


def tiempo(lat, lon, inicio):
    r = bajar_json("https://api.open-meteo.com/v1/forecast?" + urllib.parse.urlencode(
        {"latitude": lat, "longitude": lon, "hourly": "precipitation,wind_speed_10m,temperature_2m",
         "timezone": "Europe/Madrid", "forecast_days": 3}))
    h = (r or {}).get("hourly") or {}
    horas = h.get("time") or []
    clave = inicio.strftime("%Y-%m-%dT%H:00")
    if clave not in horas:
        return None
    i = horas.index(clave)
    lluvia = sum((h["precipitation"][i:i + 2]) or [0])
    return {"lluvia_mm": round(lluvia, 1), "viento_kmh": h["wind_speed_10m"][i], "temperatura": h["temperature_2m"][i]}


def calendario_equipos():
    """{team_id: [(fecha, liga_id, fixture_id)]} con todas las competiciones que seguimos."""
    out = {}
    for f in DATOS.glob("calendario_*.json"):
        for p in leer(f, []) or []:
            for t in (p["teams"]["home"]["id"], p["teams"]["away"]["id"]):
                out.setdefault(t, []).append((p["fixture"]["date"], p["league"]["id"], p["fixture"]["id"]))
    for v in out.values():
        v.sort()
    return out


def descanso(cal, tid, fid, fecha):
    lista = list(cal.get(tid, []))
    try:   # 10/11: los de categoría baja no tienen su liga en nuestros calendarios: sus fechas de copa_contexto
        info = (leer(DATOS / "equipos_info.json", {}) or {}).get(str(tid)) or {}
        lista += [(f, 0, None) for f in info.get("fechas") or [] if not any(x[0][:10] == f[:10] for x in lista)]
        lista.sort()
    except Exception:
        pass
    antes = [x for x in lista if x[0] < fecha and x[2] != fid]
    despues = [x for x in lista if x[0] > fecha and x[2] != fid]
    d0 = datetime.fromisoformat(fecha)
    ult = antes[-1] if antes else None
    sig = despues[0] if despues else None
    return {"dias_desde": (d0 - datetime.fromisoformat(ult[0])).days if ult else None,
            "ultimo_europa": EUROPA.get(ult[1]) if ult else None,
            "dias_hasta": (datetime.fromisoformat(sig[0]) - d0).days if sig else None,
            "siguiente_europa": EUROPA.get(sig[1]) if sig else None}


def tabla(liga_id):
    try:
        import razones
        return razones.tabla(liga_id)
    except Exception:
        return {}, 0


def main():
    ahora = datetime.now(MADRID)
    hasta = (ahora + timedelta(days=1)).strftime("%Y-%m-%d")
    cache = leer(CIUDADES, {}) or {}
    cal = calendario_equipos()
    try:
        from picks import indice_arbitros, nombre_arbitro
        arbs = indice_arbitros()
    except Exception:
        arbs, nombre_arbitro = {}, None
    salida = {}
    for f in EXTRA.glob("*.json"):
        ex = leer(f, {}) or {}
        pa = ex.get("partido")
        if not pa or pa["fixture"]["status"]["short"] not in ("NS", "TBD"):
            continue
        if not ahora.strftime("%Y-%m-%d") <= pa["fixture"]["date"][:10] <= hasta \
                or datetime.fromisoformat(pa["fixture"]["date"]) < ahora:
            continue
        fid, fecha = pa["fixture"]["id"], pa["fixture"]["date"]
        inicio = datetime.fromisoformat(fecha).astimezone(MADRID)
        l, v = pa["teams"]["home"], pa["teams"]["away"]
        c = {"local": {"nombre": l["name"], **descanso(cal, l["id"], fid, fecha)},
             "visitante": {"nombre": v["name"], **descanso(cal, v["id"], fid, fecha)}}
        sede = pa["fixture"].get("venue") or {}
        ll = coords(sede.get("city"), cache, pa["league"].get("country"))
        if ll:
            c["tiempo"] = tiempo(ll[0], ll[1], inicio)
        if nombre_arbitro:
            a = nombre_arbitro(pa["fixture"].get("referee"))
            t = arbs.get(a, []) if a else []
            if a and len(t) >= 4:
                c["arbitro"] = {"nombre": a, "partidos": len(t), "tarjetas": round(sum(t) / len(t), 1)}
        hist = ex.get("cuotas_hist") or {}
        mov = {}
        for k in ("Home", "Draw", "Away"):
            s = hist.get(f"Match Winner|{k}") or []
            if len(s) >= 2:
                a0, a1 = float(s[0][1]), float(s[-1][1])
                if a0 and abs(a1 - a0) / a0 >= 0.08 and a1 <= 3.0:   # solo favoritos / partidos igualados
                    mov[k] = [a0, a1]
        if mov:
            c["cuotas"] = mov
        tb, n = tabla(pa["league"]["id"])
        if n >= 10:
            for lado, eq in (("local", l), ("visitante", v)):
                if eq["id"] in tb:
                    pos = tb[eq["id"]][0]
                    c[lado]["puesto"], c[lado]["de"] = pos, n
        salida[str(fid)] = c
    CIUDADES.write_text(json.dumps(cache, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    SALIDA.write_text(json.dumps(salida, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"Contexto extra: {len(salida)} partidos · {sum(1 for x in salida.values() if x.get('tiempo'))} con el tiempo")


def razones(fid, pick=None):
    """[(peso, frase)] con hechos de cansancio, tiempo, árbitro, cuota y tabla."""
    c = (leer(SALIDA, {}) or {}).get(str(fid))
    if not c:
        return []
    out = []
    texto = ((pick or {}).get("texto") or "").lower()
    for lado in ("local", "visitante"):
        e = c[lado]
        if e.get("dias_desde") is not None and e["dias_desde"] <= 2:   # menos de 72 h
            out.append((3, f"El {e['nombre']} jugó hace {e['dias_desde']} días"
                           + (f" ({e['ultimo_europa']})" if e.get("ultimo_europa") else "") + ": puede llegar cansado"))
        if e.get("siguiente_europa") and e.get("dias_hasta") is not None and e["dias_hasta"] <= 3:
            out.append((3, f"El {e['nombre']} juega {e['siguiente_europa']} en {e['dias_hasta']} días: puede rotar"))
        if e.get("puesto") == 1:
            out.append((2, f"El {e['nombre']} es líder"))
        elif e.get("puesto") and e.get("de") and e["puesto"] >= e["de"] - 2:
            out.append((2, f"El {e['nombre']} está en descenso ({e['puesto']}º): se juega mucho"))
    t = c.get("tiempo") or {}
    if t.get("lluvia_mm", 0) >= 3 or t.get("viento_kmh", 0) >= 35:
        out.append((3 if "gol" in texto or "marca" in texto else 2,
                    "Se espera " + " y ".join(x for x in (f"lluvia ({str(t['lluvia_mm']).replace('.', ',')} mm)" if t.get("lluvia_mm", 0) >= 3 else "",
                                                         f"viento fuerte ({round(t['viento_kmh'])} km/h)" if t.get("viento_kmh", 0) >= 35 else "") if x)
                    + ": suele haber menos goles"))
    a = c.get("arbitro")
    if a and "tarjeta" in texto:
        out.append((4, f"El árbitro ({a['nombre']}) saca {str(a['tarjetas']).replace('.', ',')} tarjetas por partido"))
    for k, (a0, a1) in (c.get("cuotas") or {}).items():
        quien = c["local"]["nombre"] if k == "Home" else c["visitante"]["nombre"] if k == "Away" else "el empate"
        if a1 < a0:
            out.append((3, f"La cuota de {'que gane el ' + quien if k != 'Draw' else quien} ha bajado de "
                           f"{str(a0).replace('.', ',')} a {str(a1).replace('.', ',')}: el mercado lo ve más claro"))
    return out


if __name__ == "__main__":
    main()
