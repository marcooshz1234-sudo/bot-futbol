"""
Prueba con partidos ya jugados: ¿aciertan de verdad los picks que elige el bot?

Para cada partido terminado desde DESDE, mira solo lo que se sabía ANTES del
partido (los partidos anteriores de los dos equipos) y aplica el mismo filtro
del Analista (≥ 75 % entre los dos, ≥ 70 % cada equipo; jugadores titulares
fijos con ≥ 75 %). Luego comprueba si se cumplió. No usa cuotas (no se guardan
las de partidos pasados), así que mide la fiabilidad del filtro por mercado.

Escribe informes/prueba_mercados.md
"""

import sys
from collections import defaultdict

from bot import RAIZ
from picks import (FREC_EQUIPO, FREC_MIN, MIN_PARTIDOS, ULTIMOS, STATS_OU, evaluador, historial,
                   plantilla_fija, tipo_de)

DESDE = sys.argv[1] if len(sys.argv) > 1 else "2026-09-25"

LINEAS = {
    "Goals Over/Under": ["Over 1.5", "Over 2.5"],
    "Goals Over/Under First Half": ["Over 0.5"],
    "Goals Over/Under - Second Half": ["Over 0.5", "Over 1.5"],
    "Both Teams Score": ["Yes"],
    "Total - Home": ["Over 0.5", "Over 1.5"], "Total - Away": ["Over 0.5", "Over 1.5"],
    "Home Team Score a Goal (2nd Half)": ["Yes"], "Away Team Score a Goal (2nd Half)": ["Yes"],
    "To Win Either Half": ["Home", "Away"],
    "Double Chance": ["Home/Draw", "Draw/Away", "Home/Away"], "Match Winner": ["Home", "Away"],
    "Corners Over Under": ["Over 7.5", "Over 8.5", "Over 9.5", "Under 10.5", "Under 11.5"],
    "Home Corners Over/Under": ["Over 3.5", "Over 4.5", "Over 5.5"],
    "Away Corners Over/Under": ["Over 2.5", "Over 3.5", "Over 4.5"],
    "Total Corners (1st Half)": ["Over 3.5", "Over 4.5"],
    "Corners 1x2": ["Home", "Away"],
    "Cards Over/Under": ["Over 2.5", "Over 3.5", "Over 4.5", "Under 5.5"],
    "Home Team Total Cards": ["Over 0.5", "Over 1.5"], "Away Team Total Cards": ["Over 0.5", "Over 1.5"],
    "Both Teams to Receive a Card": ["Yes"],
    "Total ShotOnGoal": ["Over 6.5", "Over 7.5", "Over 8.5"],
    "Home Total ShotOnGoal": ["Over 2.5", "Over 3.5", "Over 4.5"],
    "Away Total ShotOnGoal": ["Over 2.5", "Over 3.5", "Over 4.5"],
    "ShotOnTarget 1x2": ["Home", "Away"],
    "Fouls. Total": ["Over 19.5", "Over 21.5", "Over 23.5"],
    "Fouls. Home Total": ["Over 9.5", "Over 10.5"], "Fouls. Away Total": ["Over 9.5", "Over 10.5"],
    "Offsides Total": ["Over 2.5", "Over 3.5"],
    "Saves O/U Home": ["Over 1.5", "Over 2.5"], "Saves O/U Away": ["Over 1.5", "Over 2.5", "Over 3.5"],
}
JUG_LINEAS = [("a_puerta", 1, "tiro a puerta 1+"), ("tiros", 2, "tiros 2+"), ("tiros", 3, "tiros 3+"),
              ("faltas_c", 1, "faltas 1+"), ("faltas_c", 2, "faltas 2+"), ("amarillas", 1, "amonestado"),
              ("paradas", 2, "paradas 2+"), ("paradas", 3, "paradas 3+"), ("goles", 1, "marca")]


def main():
    hist = historial()
    partidos = {}
    for l in hist.values():
        for p in l:
            if p["fecha"] >= DESDE:
                partidos[p["id"]] = p
    res = defaultdict(lambda: [0, 0])          # (tipo, mercado) -> [aciertos, total]
    jug = defaultdict(lambda: [0, 0])
    for p in partidos.values():
        antes = {k: [x for x in v if x["fecha"] < p["fecha"]] for k, v in hist.items()}
        loc, vis = p["local"]["id"], p["visitante"]["id"]
        h_loc = [(x, loc) for x in antes.get(loc, [])[:ULTIMOS]]
        h_vis = [(x, vis) for x in antes.get(vis, [])[:ULTIMOS]]
        if len(h_loc) < MIN_PARTIDOS or len(h_vis) < MIN_PARTIDOS:
            continue
        for mercado, ops in LINEAS.items():
            for op in ops:
                fl, fv = evaluador(mercado, op, True), evaluador(mercado, op, False)
                if not fl:
                    continue
                a = [v for v in (fl(x, e) for x, e in h_loc) if v is not None]
                b = [v for v in (fv(x, e) for x, e in h_vis) if v is not None]
                if len(a) < MIN_PARTIDOS or len(b) < MIN_PARTIDOS:
                    continue
                fa, fb = sum(a) / len(a), sum(b) / len(b)
                if (sum(a) + sum(b)) / (len(a) + len(b)) < FREC_MIN or min(fa, fb) < FREC_EQUIPO:
                    continue
                real = fl(p, loc)
                if real is None:
                    continue
                k = (tipo_de(mercado), f"{mercado} {op}")
                res[k][0] += bool(real)
                res[k][1] += 1
        # jugadores
        for eq in (loc, vis):
            fijos = plantilla_fija(eq, antes)
            jugaron = {j["id"]: j for j in (p.get("jugadores") or {}).get(str(eq)) or []}
            for pid, d in fijos.items():
                j = jugaron.get(pid)
                minimo = 80 if d["pos"] == "G" else 60
                if not j or (j.get("min") or 0) < minimo:
                    continue  # no fue titular: bet365 anula la pata
                regs = d["partidos"]
                if len(regs) < MIN_PARTIDOS:
                    continue
                for campo, n, nombre in JUG_LINEAS:
                    if (campo == "paradas") != (d["pos"] == "G"):
                        continue
                    frec = sum(1 for r in regs if (r.get(campo) or 0) >= n) / len(regs)
                    if frec < FREC_MIN:
                        continue
                    valor = j.get(campo)
                    if campo == "paradas" and not valor:
                        valor = ((p.get("stats") or {}).get(str(eq)) or {}).get("paradas")
                    jug[nombre][0] += (valor or 0) >= n
                    jug[nombre][1] += 1

    por_tipo = defaultdict(lambda: [0, 0])
    for (tipo, _), (s, n) in res.items():
        por_tipo[tipo][0] += s
        por_tipo[tipo][1] += n
    jt = [sum(v[0] for v in jug.values()), sum(v[1] for v in jug.values())]
    por_tipo["jugador"] = jt

    out = [f"# Prueba de mercados con partidos ya jugados (desde {DESDE})", "",
           f"Partidos analizados: {len(partidos)}. Para cada uno se usa solo lo que se sabía antes del partido "
           "y el mismo filtro del bot (≥ 75 %). Se cuenta cuántas veces acertó.", "",
           "## Por tipo de mercado", "", "| Tipo | Aciertos | Picks | % |", "|---|---|---|---|"]
    for t, (s, n) in sorted(por_tipo.items(), key=lambda x: -(x[1][0] / x[1][1] if x[1][1] else 0)):
        if n:
            out.append(f"| {t} | {s} | {n} | {s / n:.0%} |")
    out += ["", "## Por mercado y línea (mín. 10 picks)", "", "| Mercado | Aciertos | Picks | % |", "|---|---|---|---|"]
    filas = [(k[1], s, n) for k, (s, n) in res.items() if n >= 10] + [(f"Jugador: {k}", s, n) for k, (s, n) in jug.items() if n >= 10]
    for m, s, n in sorted(filas, key=lambda x: -x[1] / x[2]):
        out.append(f"| {m} | {s} | {n} | {s / n:.0%} |")
    (RAIZ / "informes").mkdir(exist_ok=True)
    (RAIZ / "informes" / "prueba_mercados.md").write_text("\n".join(out) + "\n", encoding="utf-8")
    print("\n".join(out))


if __name__ == "__main__":
    main()
