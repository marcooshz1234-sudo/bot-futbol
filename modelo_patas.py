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
L2 = 3.0
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


def rasgos(p, frec=None):
    """Diccionario de rasgos de una pata (los mismos al aprender y al usarlo)."""
    c = float(p["cuota"])
    imp = 1 / c
    f = float(frec if frec is not None else p.get("frecuencia") or imp)
    r = {"cuota": logit(imp), "ventaja_racha": logit(f) - logit(imp),
         f"fam={familia(p)}": 1.0, f"lado={lado(p)}": 1.0, f"senal={senal(p)}": 1.0,
         "baja_1_35": 1.0 if c <= 1.35 else 0.0,
         "liga_grande": 1.0 if p.get("competicion") in GRANDES else 0.0}
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


def evaluar(patas, pliegues=5):
    """Validación cruzada por partidos: el modelo nuevo frente a la cuota sola y frente a lo de antes."""
    por_partido = defaultdict(list)
    for p in patas:
        por_partido[p.get("partido_id")].append(p)
    ids = sorted(por_partido, key=lambda x: str(x))
    nuevo, antes, cuota = [], [], []
    for k in range(pliegues):
        test_ids = set(ids[k::pliegues])
        train = [p for i in ids if i not in test_ids for p in por_partido[i]]
        filas = [(rasgos(p), float(bool(p["acierto"]))) for p in train]
        nombres = sorted({n for f, _ in filas for n in f})
        w = _entrenar(filas, nombres)
        for i in test_ids:
            for p in por_partido[i]:
                y = float(bool(p["acierto"]))
                nuevo.append((_predecir(w, nombres, rasgos(p)), y))
                cuota.append((1 / float(p["cuota"]), y))
                if p.get("prob_aprendida") is not None:
                    antes.append((float(p["prob_aprendida"]), y, _predecir(w, nombres, rasgos(p))))
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
    ev = evaluar(patas)
    filas = [(rasgos(p), float(bool(p["acierto"]))) for p in patas]
    nombres = sorted({n for f, _ in filas for n in f})
    w = _entrenar(filas, nombres)
    mejor = ev["antes_mismas_patas"] is None or ev["nuevo_mismas_patas"]["logloss"] < ev["antes_mismas_patas"]["logloss"]
    salida = {"generado": datetime.now(MADRID).strftime("%Y-%m-%d %H:%M"), "activo": bool(mejor),
              "patas": len(patas), "evaluacion": ev, "constante": round(float(w[0]), 4),
              "pesos": {n: round(float(w[i + 1]), 4) for i, n in enumerate(nombres)}}
    SALIDA.write_text(json.dumps(salida, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print("Modelo de patas:", "ACTIVO" if mejor else "no mejora, no se usa", json.dumps(ev, ensure_ascii=False))


_M = {}


def prob(p, frec=None):
    """Probabilidad real estimada de una pata con el modelo nuevo, o None si no está activo."""
    if "m" not in _M:
        _M["m"] = leer(SALIDA, {}) or {}
    m = _M["m"]
    if not m.get("activo") or not p.get("cuota"):
        return None
    try:
        f = rasgos(p, frec)
    except (TypeError, ValueError, ZeroDivisionError):
        return None
    z = m["constante"] + sum(v * f.get(n, 0.0) for n, v in m["pesos"].items())
    return 1 / (1 + math.exp(-z))


if __name__ == "__main__":
    main()
