"""13/11 (Marcos: «no me des estimaciones, quiero que aprendas a calcularlo»).

Calculadora del «Crear apuesta» de bet365 para combis de UN partido.

bet365 paga según la probabilidad de que salga TODO A LA VEZ. Multiplicar solo vale si las patas no tienen nada que
ver; si van ligadas (gana Alemania + Alemania marca 2 + Wirtz marca), paga mucho menos (3,14 → 1,95).

Cómo lo calcula:
  1. Con las cuotas de bet365 del propio partido (quién gana, goles de cada equipo) saca cuántos goles se esperan de
     cada equipo (modelo de Poisson) → la probabilidad de cada marcador, con 1ª y 2ª parte.
  2. Cada pata se mira en cada marcador: «gana Alemania», «Alemania marca 2», «ambos marcan», «gana una parte»…
     Las de jugador van ligadas a los goles de su equipo: «Wirtz marca o asiste» es más fácil si Alemania mete 4
     que si mete 1; sus remates también suben un poco con los goles (RHO_TIROS).
  3. Córners, tarjetas, faltas y lo que no sabe modelar: como si fueran sueltas (con su probabilidad).
  4. R = probabilidad de todo junto / producto de las probabilidades sueltas (R > 1: van juntas, paga menos).
     Cuota = multiplicando × a^patas / R^k, con a y k aprendidos de las cuotas reales que da Marcos
     (datos/crear_medidas.json). 13/11 Escocia–Macedonia: bet365 quita parte del margen de cada pata (a ≈ 1,02).

Uso:  python3 crear_apuesta.py <post_id>            (o desde código: cuota(sel, cuotas))
      python3 crear_apuesta.py --medidas            (error medio contra las cuotas reales guardadas)
"""
import json
import math
import sys

import numpy as np

from bot import DATOS, leer

MEDIDAS = DATOS / "crear_medidas.json"
MAXG = 9
PARTE1 = 0.45            # parte de los goles que cae en la 1ª parte
RHO_TIROS = 0.35         # cuánto suben los remates de un jugador con los goles de su equipo
FRENO = 0.5             # con pocas medidas, a y k casi no se mueven de (1, 1)
MARGEN_SUELTA = 1.06     # margen de bet365 en un mercado de una sola cara (goleador, remates de jugador…)
_G = np.arange(MAXG + 1)


def _pois(l):
    from math import exp, factorial
    return np.array([exp(-l) * l ** k / factorial(k) for k in _G])


def _par(c, m, a, b):
    d = dict(c.get(m) or [])
    if a in d and b in d:
        pa, pb = 1 / float(d[a]), 1 / float(d[b])
        return pa / (pa + pb)
    return None


def lambdas(c):
    """Goles esperados de cada equipo que mejor cuadran con las cuotas de bet365 del partido."""
    mw = dict(c.get("Match Winner") or [])
    objetivo = []
    if {"Home", "Draw", "Away"} <= set(mw):
        s = sum(1 / float(mw[k]) for k in ("Home", "Draw", "Away"))
        objetivo.append(("1x2", [1 / float(mw[k]) / s for k in ("Home", "Draw", "Away")]))
    for lado, m in (("h", "Total - Home"), ("a", "Total - Away")):
        for k in (0.5, 1.5, 2.5, 3.5):
            p = _par(c, m, f"Over {k}", f"Under {k}")
            if p is not None:
                objetivo.append((lado, (int(k + 0.5), p)))
    for k in (1.5, 2.5, 3.5):
        p = _par(c, "Goals Over/Under", f"Over {k}", f"Under {k}")
        if p is not None:
            objetivo.append(("t", (int(k + 0.5), p)))
    if not objetivo:
        return None
    mejor = None
    for lh in np.arange(0.1, 4.01, 0.05):
        ph = _pois(lh)
        for la in np.arange(0.1, 4.01, 0.05):
            M = np.outer(ph, _pois(la))
            e = 0.0
            for tipo, v in objetivo:
                if tipo == "1x2":
                    q = (np.tril(M, -1).sum(), np.trace(M), np.triu(M, 1).sum())
                    e += sum((x - y) ** 2 for x, y in zip(q, v))
                elif tipo == "h":
                    e += (M[v[0]:, :].sum() - v[1]) ** 2
                elif tipo == "a":
                    e += (M[:, v[0]:].sum() - v[1]) ** 2
                else:
                    t = np.add.outer(_G, _G)
                    e += (M[t >= v[0]].sum() - v[1]) ** 2
            if mejor is None or e < mejor[0]:
                mejor = (e, lh, la)
    return mejor[1], mejor[2]


class Rejilla:
    """Probabilidad de cada (goles local 1ª, visitante 1ª, local 2ª, visitante 2ª)."""
    def __init__(self, lh, la):
        n = MAXG // 2 + 2
        g = np.arange(n)
        pe = lambda l: np.array([math.exp(-l) * l ** k / math.factorial(k) for k in g])
        self.P = np.einsum("a,b,c,d->abcd", pe(lh * PARTE1), pe(la * PARTE1), pe(lh * (1 - PARTE1)), pe(la * (1 - PARTE1)))
        h1, a1, h2, a2 = np.meshgrid(g, g, g, g, indexing="ij")
        self.h1, self.a1, self.h2, self.a2 = h1, a1, h2, a2
        self.h, self.a = h1 + h2, a1 + a2
        self.lh, self.la = lh, la


def _biseccion(f, a, b, n=60):
    """Raíz de f en [a, b] (f(a) y f(b) de distinto signo). Sin scipy: en GitHub no está instalado."""
    fa = f(a)
    for _ in range(n):
        m = (a + b) / 2
        fm = f(m)
        if (fm > 0) == (fa > 0):
            a, fa = m, fm
        else:
            b = m
    return (a + b) / 2


def _al_menos(k, mu):
    """P(Poisson(mu) >= k) para un array de medias mu."""
    mu = np.asarray(mu, float)
    term = np.exp(-mu)
    cdf = term.copy()
    for i in range(1, k):
        term = term * mu / i
        cdf = cdf + term
    return 1 - cdf if k > 0 else np.ones_like(mu)


def _over(o):
    return float(o.split()[1])


def indicador(R, mercado, opcion):
    """1/0 en cada marcador si la pata de goles/resultado sale; None si no es de este tipo."""
    h, a = R.h, R.a
    if mercado == "Match Winner":
        return {"Home": h > a, "Draw": h == a, "Away": a > h}.get(opcion)
    if mercado == "Double Chance":
        return {"Home/Draw": h >= a, "Draw/Away": a >= h, "Home/Away": h != a}.get(opcion)
    if mercado == "Both Teams Score":
        return (h > 0) & (a > 0) if opcion == "Yes" else (h == 0) | (a == 0)
    if mercado in ("Total - Home", "Total - Away", "Goals Over/Under"):
        x = h if mercado.endswith("Home") else a if mercado.endswith("Away") else h + a
        k = _over(opcion)
        return x > k if opcion.startswith("Over") else x < k
    if mercado == "To Win Either Half":
        return ((R.h1 > R.a1) | (R.h2 > R.a2)) if opcion == "Home" else ((R.a1 > R.h1) | (R.a2 > R.h2))
    if mercado == "Win Both Halves":
        return ((R.h1 > R.a1) & (R.h2 > R.a2)) if opcion == "Home" else ((R.a1 > R.h1) & (R.a2 > R.h2))
    if mercado == "Results/Both Teams Score":
        res, btts = opcion.split("/")
        r = {"Home": h > a, "Draw": h == a, "Away": a > h}[res]
        b = (h > 0) & (a > 0)
        return r & (b if btts == "Yes" else ~b)
    if mercado == "To Score In Both Halves By Teams":
        return ((R.h1 > 0) & (R.h2 > 0)) if opcion == "Home" else ((R.a1 > 0) & (R.a2 > 0))
    return None


def _lado_jugador(c, mercado, jugador):
    if mercado.startswith("Home"):
        return "h"
    if mercado.startswith("Away"):
        return "a"
    for m, lado in (("Home Player Shots", "h"), ("Away Player Shots", "a"), ("Home Player Shots On Target Total", "h"),
                    ("Away Player Shots On Target Total", "a")):
        if any(o.rsplit(" - ", 1)[0] == jugador for o, _ in (c.get(m) or [])):
            return lado
    return None


def condicional_jugador(R, c, mercado, opcion, cuota):
    """Probabilidad de la pata de jugador en cada marcador (va ligada a los goles de su equipo)."""
    jugador = opcion.rsplit(" - ", 1)[0] if " - " in opcion else opcion
    lado = _lado_jugador(c, mercado, jugador)
    if not lado:
        return None
    G = R.h if lado == "h" else R.a
    lam = R.lh if lado == "h" else R.la
    p = 1 / cuota / MARGEN_SUELTA
    if mercado in ("Player to Score or Assist", "Anytime Goal Scorer"):
        # cada gol de su equipo es suyo (o de su asistencia) con probabilidad s
        f = lambda s: 1 - (R.P * (1 - s) ** G).sum() - p
        if f(1e-6) > 0 or f(0.999) < 0:
            return None
        s = _biseccion(f, 1e-6, 0.999)
        return 1 - (1 - s) ** G
    if "Shots" in mercado:
        k = int(opcion.rsplit(" - ", 1)[1])
        escala = 1 + RHO_TIROS * (G - lam) / max(lam, 0.5)
        escala = np.clip(escala, 0.3, 3)
        f = lambda mu: (R.P * _al_menos(k, mu * escala)).sum() - p
        if f(0.01) > 0 or f(15) < 0:
            return None
        mu = _biseccion(f, 0.01, 15)
        return _al_menos(k, mu * escala)
    return None


def calcular(sel, cuotas, c):
    """{'mult', 'R', 'cuota_modelo', 'sueltas'} para una combi de un partido con las cuotas del partido c."""
    l = lambdas(c)
    mult = math.prod(cuotas)
    if not l:
        return {"mult": round(mult, 3), "R": 1.0, "cuota_modelo": round(mult, 2), "sueltas": len(sel)}
    R = Rejilla(*l)
    conj = np.ones_like(R.P)
    prod = 1.0
    sueltas = 0
    for s, cu in zip(sel, cuotas):
        _, m, o = s.split("|", 2)
        ind = indicador(R, m, o)
        if ind is not None:
            q = ind.astype(float)
        else:
            q = condicional_jugador(R, c, m, o, cu)
        if q is None:   # córners, tarjetas, faltas…: suelta
            sueltas += 1
            continue
        conj = conj * q
        prod *= (R.P * q).sum()
    junta = (R.P * conj).sum()
    r = junta / prod if prod > 0 and junta > 0 else 1.0
    return {"mult": round(mult, 3), "R": round(float(r), 4), "cuota_modelo": round(float(mult / r), 2), "sueltas": sueltas,
            "lambdas": [round(float(x), 2) for x in l]}


def sesgo():
    """Lo aprendido de las cuotas reales (media del log real/modelo, con freno si hay pocas)."""
    ms = [m for m in (leer(MEDIDAS, []) or []) if m.get("cuota_modelo") and m.get("real")]
    if not ms:
        return 0.0
    logs = [math.log(m["real"] / m["cuota_modelo"]) for m in ms]
    return sum(logs) / (len(logs) + 2)   # con 2 «medidas fantasma» en 0: con pocas, casi no corrige


def parametros(ms=None):
    """Lo aprendido de las cuotas reales de bet365: (a, k).

    a: bet365 en el Crear apuesta quita parte del margen de CADA pata (cuantas más patas, más se nota).
    k: cuánto de fuerte liga de verdad las patas comparado con el modelo (1 = como el modelo).
    cuota = multiplicando × a^patas / R^k. Ajuste por mínimos cuadrados en logaritmos, con freno hacia (1, 1).
    """
    ms = [m for m in (leer(MEDIDAS, []) if ms is None else ms) or [] if m.get("R") and m.get("real") and m.get("mult")]
    A = np.eye(2) * FRENO
    b = np.array([0.0, FRENO])
    for m in ms:
        x = np.array([len(m["sel"]), -math.log(m["R"])])
        A += np.outer(x, x)
        b += x * math.log(m["real"] / m["mult"])
    la, k = np.linalg.solve(A, b)
    return math.exp(la), float(k)


def cuota(sel, cuotas, c=None):
    """La cuota que calcula el bot para el «Crear apuesta» (o None si no hay cuotas del partido)."""
    fid = sel[0].split("|")[0]
    c = c or (leer(DATOS / "proximos" / f"{fid}.json", {}) or {}).get("cuotas")
    if not c:
        return None
    r = calcular(sel, cuotas, c)
    a, k = parametros()
    return round(r["mult"] * a ** len(sel) / r["R"] ** k, 2)


def guardar_medida(pid, sel, cuotas, real, fuente="Marcos"):
    """Cada cuota real que da Marcos se guarda con las cuotas del partido de ESE momento (luego desaparecen)."""
    fid = sel[0].split("|")[0]
    c = (leer(DATOS / "proximos" / f"{fid}.json", {}) or {}).get("cuotas")
    if not c:
        return None
    ms = leer(MEDIDAS, []) or []
    if any(m["id"] == pid and abs(m["real"] - real) < 0.005 for m in ms):
        return None
    r = calcular(sel, cuotas, c)
    claves = ("Match Winner", "Total - Home", "Total - Away", "Goals Over/Under")
    jug = {m: v for m, v in c.items() if "Player" in m or m in ("Anytime Goal Scorer", "Player to Score or Assist")}
    m = {"id": pid, "sel": sel, "cuotas": cuotas, "real": real, "fuente": fuente, **r,
         "mercados": {k: c[k] for k in claves if k in c}, "jugadores": jug}
    ms = [x for x in ms if x["id"] != pid] + [m]
    MEDIDAS.write_text(json.dumps(ms, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return m


def informe():
    ms = leer(MEDIDAS, []) or []
    if not ms:
        print("Sin medidas")
        return
    e_mult = sum(abs(m["mult"] / m["real"] - 1) for m in ms) / len(ms)
    e_mod = sum(abs(m["cuota_modelo"] / m["real"] - 1) for m in ms) / len(ms)
    print(f"{len(ms)} medidas · error multiplicando {100 * e_mult:.0f} % · error del modelo {100 * e_mod:.0f} %"
          f" · sesgo aprendido ×{math.exp(sesgo()):.3f}")
    a, k = parametros(ms)
    print(f"aprendido: a {a:.3f} por pata · k {k:.2f}")
    errs = []
    for i, m in enumerate(ms):
        a_, k_ = parametros(ms[:i] + ms[i + 1:])   # sin ella: ¿la habría acertado?
        pred = m["mult"] * a_ ** len(m["sel"]) / m["R"] ** k_
        errs.append(abs(pred / m["real"] - 1))
        print(f"  {m['id'][:42]:42} mult {m['mult']:.2f} · bot {pred:.2f} · real {m['real']:.2f}"
              f" ({100 * (pred / m['real'] - 1):+.0f} %)")
    print(f"error sin haberla visto: {100 * sum(errs) / len(errs):.0f} %")


if __name__ == "__main__":
    if sys.argv[1:] == ["--medidas"]:
        informe()
    else:
        from bot import RAIZ
        cola = (leer(RAIZ / "publicaciones" / "cola.json", []) or []) + (leer(RAIZ / "publicaciones" / "auto.json", []) or [])
        for pid in sys.argv[1:]:
            p = next(x for x in cola if x["id"] == pid)
            fid = p["sel"][0].split("|")[0]
            c = (leer(DATOS / "proximos" / f"{fid}.json", {}) or {}).get("cuotas")
            print(pid, calcular(p["sel"], p["cuotas"], c), "→ cuota", cuota(p["sel"], p["cuotas"], c))
