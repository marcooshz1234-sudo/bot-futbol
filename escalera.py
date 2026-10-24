"""
El Analista · Reto escalera.

Empieza con 20 € y cada día juega una combi de 2 picks (cuota ~2) con lo ganado
el día anterior. Si sale verde, sube un escalón; si falla, se reinicia con 20 €.

- Elige el escalón de cada día entre los picks de datos/picks.json (los más
  fiables, de partidos distintos, cuota total entre 1,85 y 2,40).
- Cuando los partidos del escalón han terminado, lo corrige solo con los
  resultados guardados en datos/partidos/ y prepara el siguiente.
- Estado en datos/escalera.json. El post lo escribe plantillas.py.
"""

import json
from datetime import datetime

from bot import DATOS, MADRID, PARTIDOS, leer
from picks import evaluar_pick

ESTADO = DATOS / "escalera.json"
INICIAL = 20.0
CUOTA_MIN, CUOTA_MAX = 1.85, 2.40
DESDE = "2026-10-24"
DIAS_RETO = 7          # 20 → 40 → … → 1.280 €; tras el día 7 (o un fallo) vuelve al día 1


def elegir(dia):
    """Dos picks de partidos distintos con cuota total en rango, los más fiables primero.
    Nunca comparte selección con la combi segura del mismo día."""
    segura = (dia.get("combis") or {}).get("segura") or {}
    en_segura = {(p["partido_id"], p["mercado"], p["opcion"]) for p in segura.get("picks", [])}
    picks = [p for p in dia["picks"] if p.get("tipo") != "jugador"   # los de jugador se corrigen aparte
             and (p["partido_id"], p["mercado"], p["opcion"]) not in en_segura]
    orden = sorted(picks, key=lambda p: (-p["frecuencia"], -p["ventaja"]))
    mejor = None
    for i, a in enumerate(orden):
        for b in orden[i + 1:]:
            if a["partido_id"] == b["partido_id"]:
                continue
            c = a["cuota"] * b["cuota"]
            if CUOTA_MIN <= c <= CUOTA_MAX:
                nota = a["frecuencia"] + b["frecuencia"]
                if not mejor or nota > mejor[0]:
                    mejor = (nota, [a, b], round(c, 2))
        if mejor and i > 10:
            break
    return mejor


def resultado(pick):
    """True/False si el partido ya terminó, None si aún no."""
    p = leer(PARTIDOS / f"{pick['partido_id']}.json")
    if not p or p.get("estado") not in ("FT", "AET", "PEN"):
        return None
    return evaluar_pick(pick, p)


def main():
    picks = leer(DATOS / "picks.json")
    estado = leer(ESTADO) or {"escalon": 1, "stake": INICIAL, "historial": [], "actual": None}
    hoy = datetime.now(MADRID).strftime("%Y-%m-%d")

    # 1) corregir el escalón en juego
    act = estado.get("actual")
    if act:
        res = [resultado(p) for p in act["picks"]]
        if all(r is not None for r in res):
            verde = all(res)
            act["resultado"] = "verde" if verde else "roja"
            act["aciertos"] = res
            estado["historial"].append(act)
            if verde and act["escalon"] < DIAS_RETO:
                estado["stake"] = round(act["stake"] * act["cuota"], 2)
                estado["escalon"] = act["escalon"] + 1
            else:
                estado["stake"] = INICIAL
                estado["escalon"] = 1
            estado["actual"] = None
            print(f"Escalón {act['escalon']} corregido: {act['resultado']}")

    # 2) preparar el siguiente escalón (el primer día con picks desde hoy)
    if not estado.get("actual") and picks:
        for dia in sorted(picks["dias"]):
            if dia < max(hoy, DESDE):
                continue
            ya = any(h["dia"] == dia for h in estado["historial"])
            if ya:
                continue
            elegido = elegir(picks["dias"][dia])
            if elegido:
                _, sel, cuota = elegido
                estado["actual"] = {"dia": dia, "escalon": estado["escalon"], "stake": estado["stake"],
                                    "cuota": cuota, "picks": sel,
                                    "anterior": estado["historial"][-1] if estado["historial"] else None}
                print(f"Escalón {estado['escalon']} para {dia}: x{cuota}")
                break
    elif estado.get("actual") and picks:
        # si el escalón aún no ha empezado, se actualizan cuotas/picks con los datos nuevos
        act = estado["actual"]
        primero = min(p["fecha"] for p in act["picks"])
        publicado = f"{act['dia']}-escalera" in (leer(DATOS.parent / "publicaciones" / "enviados.json", {}) or {})
        if not publicado and primero > datetime.now(MADRID).strftime("%Y-%m-%dT%H:%M") and act["dia"] in picks["dias"]:
            elegido = elegir(picks["dias"][act["dia"]])
            if elegido:
                act["picks"], act["cuota"] = elegido[1], elegido[2]

    ESTADO.write_text(json.dumps(estado, ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
