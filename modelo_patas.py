"""11/11 (Marcos: «no está aprendiendo de la forma correcta: enséñale mejor cómo aprender y de qué»).

El aprendizaje de antes (aprender.py) partía de 1/cuota de bet365 como si fuera la probabilidad real y le sumaba
correcciones pequeñas. Pero 1/cuota lleva dentro el margen de la casa (en jugadores y «equipo marca» un 6-12 %),
así que el bot creía que sus patas salían el 70 % y salían el 62 %.

Este modelo aprende de golpe, con todas las patas ya corregidas (datos/registro_aciertos.json), cuánto acierta de
verdad una pata según:
  - lo que dice la cuota (y así aprende solo el margen de bet365 en cada tipo de mercado),
  - lo que dice nuestra racha/frecuencia frente a la cuota (¿nuestra estadística aporta o no?),
  - el tipo de mercado (goles, resultado, jugador remates, faltas, córners, tarjetas…),
  - el lado: local, visitante, el partido entero o un jugador,
  - si bet365 paga más, igual o menos que las otras casas,
  - si la cuota es muy baja (≤1,35),
  - la liga (las grandes frente al resto).
Es una regresión logística con freno (para que con pocos datos no se crea patrones de casualidad). Se comprueba
con validación cruzada por partidos: solo se usa si predice MEJOR que el método de antes con partidos que no ha
visto. Sale en datos/modelo_patas.json; aprender.prob_aprendida lo usa si está activo.
"""
import json
import math
from collections import defaultdict
from datetime import datetime

from bot import DATOS, MADRID, leer

REGISTRO = DATOS / "registro_aciertos.json"
SALIDA = DATOS / "modelo_patas.json"
L2 = 15.0   # 11/11: con más freno predice mejor (validación cruzada: 0,6586 frente a 0,6607)
GRANDES = {"LaLiga", "Premier League", "Serie A", "Bundesliga", "Ligue 1", "Champions League", "Europa League",
           "Conference League"}


def logit(p):
    p = min(0.99, max(0.01, p))
    return math.log(p / (1 - p))


def familia(p):
    if p.get("tipo") == "jugador":
        return f"jugador:{p.get('campo') or '?'}"
    return p.get("tipo") or "otro"


def lado(p):
    m, o = str(p.get("mercado") or ""), str(p.get("opcion") or "")
    if p.get("tipo") == "jugador":
        return "jugador"
    if m.startswith("Home") or m == "Total - Home" or o in ("Home", "Home/Draw") or o.startswith("Home"):
        return "local"
    if m.startswith("Away") or m == "Total - Away" or o in ("Away", "Draw/Away") or o.startswith("Away"):
        return "visitante"
    return "partido"


def senal(p):
    vm = p.get("valor_mercado")
    if vm is None:
        return "sin_otras"
    return "b365_mas" if vm > 0.02 else "b365_menos" if vm < -0.02 else "igual"


_CTX = {}


def contexto(fid):
    if "c" not in _CTX:
        _CTX["c"] = leer(DATOS / "contexto_patas.json", {}) or {}
    c = _CTX["c"].get(str(fid))
    if c is None and fid:
        try:   # partido nuevo (de hoy o mañana): se calcula al momento
            import contexto_pata
            c = contexto_pata.calcular(fid)
        except Exception:
            c = None
        _CTX["c"][str(fid)] = c
    return c


def rasgos_contexto(p):
    """11/11 (Marcos: «que mire todo lo que pueda influir»): descanso, forma, goles, árbitro, tiempo, estadio, hora,
    competición. Cada rasgo va del lado de la pata (si es del local, «mi forma − la del rival»)."""
    c = contexto(p.get("partido_id"))
    if not c:
        return {"sin_contexto": 1.0}
    lo, vi = c.get("local") or {}, c.get("visitante") or {}
    ld = lado(p)
    yo, el = (lo, vi) if ld == "local" else (vi, lo) if ld == "visitante" else (None, None)
    fam = familia(p)
    menos = str(p.get("opcion") or "").startswith(("Under", "No"))
    r = {}
    if yo is not None:
        if "forma" in yo and "forma" in el:
            r["dif_forma"] = (yo["forma"] - el["forma"]) / 3
        if "descanso" in yo and "descanso" in el:
            r["dif_descanso"] = max(-4, min(4, yo["descanso"] - el["descanso"])) / 4
        r["europa_antes"] = 1.0 if yo.get("europa_antes") else 0.0
        r["rival_europa_antes"] = 1.0 if el.get("europa_antes") else 0.0
    if fam in ("goles", "corners") and all(k in x for x in (lo, vi) for k in ("gf", "gc")):
        g = (lo["gf"] + vi["gc"] + vi["gf"] + lo["gc"]) / 2 - 2.6   # goles esperados del partido frente a lo normal
        r["goles_esperados"] = (-g if menos else g) / 2
    t = c.get("tiempo") or {}
    if t:
        r["lluvia"] = 1.0 if (t.get("lluvia_mm") or 0) >= 1 else 0.0
        r["viento"] = 1.0 if (t.get("viento_kmh") or 0) >= 25 else 0.0
        r["frio"] = 1.0 if (t.get("temperatura") if t.get("temperatura") is not None else 15) <= 5 else 0.0
    if fam == "tarjetas" and c.get("arbitro_amarillas") is not None:
        r["arbitro_tarjetero"] = (c["arbitro_amarillas"] - 4.2) / 2
    r["noche"] = 1.0 if (c.get("hora") or 0) >= 21 else 0.0
    r[f"comp={c.get('competicion') or 'liga'}"] = 1.0
    if c.get("fuera_de_su_campo"):
        r["local_fuera_de_su_campo"] = 1.0 if ld == "local" else -1.0 if ld == "visitante" else 0.0
    if c.get("dif_nivel") and yo is not None:
        r["dif_categoria"] = (c["dif_nivel"] if ld == "local" else -c["dif_nivel"]) / 2
    return r


def rasgos(p, frec=None, con_contexto=None):
    """Diccionario de rasgos de una pata (los mismos al aprender y al usarlo)."""
    c = float(p["cuota"])
    imp = 1 / c
    f = float(frec if frec is not None else p.get("frecuencia") or imp)
    r = {"cuota": logit(imp), "ventaja_racha": logit(f) - logit(imp),
         f"fam={familia(p)}": 1.0, f"lado={lado(p)}": 1.0, f"senal={senal(p)}": 1.0,
         "baja_1_35": 1.0 if c <= 1.35 else 0.0,
         "liga_grande": 1.0 if p.get("competicion") in GRANDES else 0.0}
    if con_contexto if con_contexto is not None else _M.get("m", {}).get("con_contexto"):
        r.update(rasgos_contexto(p))
    return r


def _entrenar(filas, nombres, iters=300):
    """Logística con L2 (sin freno en la constante ni en la cuota), por Newton."""
    import numpy as np
    X = np.array([[1.0] + [f.get(n, 0.0) for n in nombres] for f, _ in filas])
    y = np.array([v for _, v in filas], dtype=float)
    w = np.zeros(X.shape[1])
    w[1] = 1.0   # de partida: fiarse de la cuota
    pen = np.full(X.shape[1], L2)
    pen[0] = 1e-6
    pen[1] = 1e-6
    for _ in range(iters):
        z = X @ w
        pr = 1 / (1 + np.exp(-z))
        g = X.T @ (pr - y) + pen * w
        H = (X.T * (pr * (1 - pr))) @ X + np.diag(pen)
        paso = np.linalg.solve(H, g)
        w -= paso
        if np.abs(paso).max() < 1e-7:
            break
    return w


def _predecir(w, nombres, f):
    z = w[0] + sum(w[i + 1] * f.get(n, 0.0) for i, n in enumerate(nombres))
    return 1 / (1 + math.exp(-z))


def datos():
    reg = leer(REGISTRO, {}) or {}
    out = []
    for p in reg.values():
        if p.get("acierto") is None or not p.get("cuota") or float(p["cuota"]) <= 1.0:
            continue
        out.append(p)
    return out


def _metricas(pares):
    n = len(pares)
    ll = -sum(y * math.log(max(1e-6, q)) + (1 - y) * math.log(max(1e-6, 1 - q)) for q, y in pares) / n
    br = sum((q - y) ** 2 for q, y in pares) / n
    return {"n": n, "logloss": round(ll, 4), "brier": round(br, 4),
            "prometido": round(sum(q for q, _ in pares) / n, 3), "real": round(sum(y for _, y in pares) / n, 3)}


def evaluar(patas, pliegues=5, con_contexto=False):
    """Validación cruzada por partidos: el modelo nuevo frente a la cuota sola y frente a lo de antes."""
    por_partido = defaultdict(list)
    for p in patas:
        por_partido[p.get("partido_id")].append(p)
    ids = sorted(por_partido, key=lambda x: str(x))
    nuevo, antes, cuota = [], [], []
    for k in range(pliegues):
        test_ids = set(ids[k::pliegues])
        train = [p for i in ids if i not in test_ids for p in por_partido[i]]
        filas = [(rasgos(p, con_contexto=con_contexto), float(bool(p["acierto"]))) for p in train]
        nombres = sorted({n for f, _ in filas for n in f})
        w = _entrenar(filas, nombres)
        for i in test_ids:
            for p in por_partido[i]:
                y = float(bool(p["acierto"]))
                q = _predecir(w, nombres, rasgos(p, con_contexto=con_contexto))
                nuevo.append((q, y))
                cuota.append((1 / float(p["cuota"]), y))
                if p.get("prob_aprendida") is not None:
                    antes.append((float(p["prob_aprendida"]), y, q))
    comun_antes = [(a, y) for a, y, _ in antes]
    comun_nuevo = [(nv, y) for _, y, nv in antes]
    return {"nuevo": _metricas(nuevo), "solo_cuota": _metricas(cuota),
            "antes_mismas_patas": _metricas(comun_antes) if antes else None,
            "nuevo_mismas_patas": _metricas(comun_nuevo) if antes else None}


def main():
    patas = datos()
    if len(patas) < 150:
        print(f"Modelo de patas: solo {len(patas)} patas, aún no")
        return
    try:
        import contexto_pata
        contexto_pata.guardar({p.get("partido_id") for p in patas})
    except Exception as e:
        print("contexto de patas:", e)
    _CTX.clear()
    ev_base = evaluar(patas, con_contexto=False)
    ev_ctx = evaluar(patas, con_contexto=True)
    # 11/11: el contexto solo se usa si de verdad predice mejor con partidos que no ha visto
    con = ev_ctx["nuevo"]["logloss"] < ev_base["nuevo"]["logloss"]
    ev = ev_ctx if con else ev_base
    filas = [(rasgos(p, con_contexto=con), float(bool(p["acierto"]))) for p in patas]
    nombres = sorted({n for f, _ in filas for n in f})
    w = _entrenar(filas, nombres)
    mejor = ev["antes_mismas_patas"] is None or ev["nuevo_mismas_patas"]["logloss"] < ev["antes_mismas_patas"]["logloss"]
    salida = {"generado": datetime.now(MADRID).strftime("%Y-%m-%d %H:%M"), "activo": bool(mejor), "con_contexto": con,
              "patas": len(patas), "evaluacion": ev, "sin_contexto_logloss": ev_base["nuevo"]["logloss"],
              "con_contexto_logloss": ev_ctx["nuevo"]["logloss"], "constante": round(float(w[0]), 4),
              "pesos": {n: round(float(w[i + 1]), 4) for i, n in enumerate(nombres)}}
    SALIDA.write_text(json.dumps(salida, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print("Modelo de patas:", "ACTIVO" if mejor else "no mejora, no se usa", "· con contexto" if con else "· sin contexto",
          f"(logloss sin {ev_base['nuevo']['logloss']} / con {ev_ctx['nuevo']['logloss']})", json.dumps(ev["nuevo"]))


_M = {}


def prob(p, frec=None):
    """Probabilidad real estimada de una pata con el modelo nuevo, o None si no está activo."""
    if "m" not in _M:
        _M["m"] = leer(SALIDA, {}) or {}
    m = _M["m"]
    if not m.get("activo") or not p.get("cuota"):
        return None
    try:
        f = rasgos(p, frec, con_contexto=bool(m.get("con_contexto")))
    except (TypeError, ValueError, ZeroDivisionError):
        return None
    z = m["constante"] + sum(v * f.get(n, 0.0) for n, v in m["pesos"].items())
    return 1 / (1 + math.exp(-z))


if __name__ == "__main__":
    main()
