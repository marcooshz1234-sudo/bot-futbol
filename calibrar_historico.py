"""
Calibración con el histórico · ¿cuánto acierta DE VERDAD cada mercado cuando la estadística dice X %?

Para cada partido ya jugado (datos/partidos), mira solo lo que se sabía antes (los últimos partidos de
los dos equipos), calcula la frecuencia que habría visto el bot en cada mercado y comprueba si se cumplió.
Con miles de casos sale, para cada mercado, la relación real entre «lo dice el % de los últimos 10» y
«lo que pasó» (la estadística de 10 partidos siempre exagera: los extremos vuelven a la media).

Sale en datos/calibracion.json y lo usa aprender.py: antes de mezclar con la cuota, la frecuencia de
cada pick se pasa por esta calibración. No usa cuotas (no se guardan las de partidos pasados).
"""
import json
import sys
from collections import defaultdict
from datetime import datetime

from bot import DATOS, MADRID
from picks import MIN_PARTIDOS, ULTIMOS, evaluador, historial, plantilla_fija, tipo_de
from prueba_mercados import JUG_LINEAS, LINEAS

SALIDA = DATOS / "calibracion.json"
FREC_DESDE = 0.60        # se miran todos los casos desde el 60 % para ver la curva entera


def ajuste(puntos):
    """Recta real = a + b·frec por mínimos cuadrados (b entre 0 y 1). puntos: [(frec, 0/1)]."""
    n = len(puntos)
    mx = sum(f for f, _ in puntos) / n
    my = sum(y for _, y in puntos) / n
    sxx = sum((f - mx) ** 2 for f, _ in puntos)
    b = sum((f - mx) * (y - my) for f, y in puntos) / sxx if sxx else 0.0
    b = max(0.0, min(1.0, b))
    return {"n": n, "frec_media": round(mx, 4), "real": round(my, 4), "pendiente": round(b, 4)}


def main():
    hist = historial()
    partidos = {p["id"]: p for l in hist.values() for p in l}
    casos = defaultdict(list)     # clave fina -> [(frec, acierto)]
    for p in sorted(partidos.values(), key=lambda x: x["fecha"]):
        antes = {k: [x for x in v if x["fecha"] < p["fecha"]] for k, v in hist.items()}
        loc, vis = p["local"]["id"], p["visitante"]["id"]
        h_loc = [(x, loc) for x in antes.get(loc, [])[:ULTIMOS]]
        h_vis = [(x, vis) for x in antes.get(vis, [])[:ULTIMOS]]
        if len(h_loc) < MIN_PARTIDOS or len(h_vis) < MIN_PARTIDOS:
            continue
        for mercado, ops in LINEAS.items():
            for op in ops:
                if op.startswith("Under") or op == "Home/Away":
                    continue          # el bot no los publica
                fl, fv = evaluador(mercado, op, True), evaluador(mercado, op, False)
                if not fl:
                    continue
                a = [v for v in (fl(x, e) for x, e in h_loc) if v is not None]
                b = [v for v in (fv(x, e) for x, e in h_vis) if v is not None]
                if len(a) < MIN_PARTIDOS or len(b) < MIN_PARTIDOS:
                    continue
                frec = (sum(a) + sum(b)) / (len(a) + len(b))
                if frec < FREC_DESDE:
                    continue
                real = fl(p, loc)
                if real is not None:
                    casos[f"{mercado}|{op}"].append((frec, 1.0 if real else 0.0))
        for eq in (loc, vis):
            fijos = plantilla_fija(eq, antes)
            jugaron = {j["id"]: j for j in (p.get("jugadores") or {}).get(str(eq)) or []}
            for pid, d in fijos.items():
                j = jugaron.get(pid)
                if not j or (j.get("min") or 0) < (80 if d["pos"] == "G" else 60):
                    continue
                regs = d["partidos"]
                if len(regs) < MIN_PARTIDOS:
                    continue
                for campo, n, _ in JUG_LINEAS:
                    if campo not in ("tiros", "a_puerta", "faltas_c"):
                        continue
                    frec = sum(1 for r in regs if (r.get(campo) or 0) >= n) / len(regs)
                    if frec >= FREC_DESDE:
                        casos[f"jugador:{campo}:{n}"].append((frec, 1.0 if (j.get(campo) or 0) >= n else 0.0))
    # tipo de cada clave
    por_tipo = defaultdict(list)
    for k, l in casos.items():
        t = f"jugador:{k.split(':')[1]}" if k.startswith("jugador:") else tipo_de(k.split("|")[0])
        por_tipo[t].extend(l)
    todos = [x for l in casos.values() for x in l]
    salida = {"generado": datetime.now(MADRID).strftime("%Y-%m-%d %H:%M"), "partidos": len(partidos),
              "global": ajuste(todos) if todos else None,
              "tipos": {t: ajuste(l) for t, l in por_tipo.items() if len(l) >= 30},
              "mercados": {k: ajuste(l) for k, l in casos.items() if len(l) >= 30}}
    SALIDA.write_text(json.dumps(salida, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    g = salida["global"]
    print(f"Calibración: {g['n']} casos en {len(partidos)} partidos · dice {g['frec_media']:.0%} → "
          f"pasa {g['real']:.0%} (pendiente {g['pendiente']})")
    if "-v" in sys.argv:
        for k, v in sorted(salida["mercados"].items(), key=lambda x: x[1]["real"] - x[1]["frec_media"]):
            print(f"  {k:45} n={v['n']:5} dice {v['frec_media']:.0%} pasa {v['real']:.0%} b={v['pendiente']}")


if __name__ == "__main__":
    main()
