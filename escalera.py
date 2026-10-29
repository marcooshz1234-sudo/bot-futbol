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
from datetime import datetime, timedelta

from bot import DATOS, MADRID, PARTIDOS, leer
from picks import evaluar_pick, es_sin_empate

ESTADO = DATOS / "escalera.json"
INICIAL = 20.0
CUOTA_MIN, CUOTA_MAX = 1.85, 2.40
DESDE = "2026-10-24"
DIAS_RETO = 7          # 20 → 40 → … → 1.280 €; tras el día 7 (o un fallo) vuelve al día 1


# 29/10 (Marcos): «todos los días tiene que haber escalera y punto». Si con lo exigente no sale, se va aflojando:
# 1) patas que el bot ve por encima de la cuota · 2) cualquier pick del bot · 3) cuota algo más abierta · 4) también jugador
NIVELES = [{"valor": True, "rango": (CUOTA_MIN, CUOTA_MAX), "jugador": False},
           {"valor": False, "rango": (CUOTA_MIN, CUOTA_MAX), "jugador": False},
           {"valor": False, "rango": (1.70, 2.60), "jugador": False},
           {"valor": False, "rango": (1.70, 2.60), "jugador": True}]
# ligas que no se juegan un día (29/10: accidente de tren en España, Marcos: «de los partidos de España no subas nada hoy»)
PAUSADAS = {"2026-10-29": (140, 141, 143)}


def elegir(dia, compartir=False, fecha=None):
    """Dos picks de partidos distintos con cuota total en rango, los más fiables primero.
    No comparte selección con la combi segura del mismo día; si así no sale ninguna pareja, se permite
    (26/10: ese día la escalera se quedó sin escalón por esa regla)."""
    for nivel in NIVELES:
        r = elegir_(dia, compartir, nivel, fecha) or (None if compartir else elegir_(dia, True, nivel, fecha))
        if r:
            return r
    return None


def elegir_(dia, compartir, nivel=NIVELES[0], fecha=None):
    segura = (dia.get("combis") or {}).get("segura") or {}
    en_segura = set() if compartir else {(p["partido_id"], p["mercado"], p["opcion"]) for p in segura.get("picks", [])}
    limite = (datetime.now(MADRID) + timedelta(minutes=40)).strftime("%Y-%m-%dT%H:%M")   # que no haya empezado
    pausadas = PAUSADAS.get(fecha, ())
    picks = [p for p in dia["picks"] if not es_sin_empate(p["mercado"], p["opcion"])
             and (nivel["jugador"] or p.get("tipo") != "jugador")   # los de jugador se corrigen aparte
             and (p["partido_id"], p["mercado"], p["opcion"]) not in en_segura
             and p.get("fecha", "9") > limite and p.get("liga_id") not in pausadas]
    # 26/10: con lo aprendido (aprender.py), solo patas cuya probabilidad real supera la de la cuota
    if nivel["valor"]:
        picks = [p for p in picks if p.get("prob_aprendida") is None or p["prob_aprendida"] >= 1 / p["cuota"] - 0.03]
    fiab = lambda p: p.get("prob_aprendida") or p["frecuencia"]
    orden = sorted(picks, key=lambda p: (-fiab(p), -p["ventaja"]))
    mejor = None
    for i, a in enumerate(orden):
        for b in orden[i + 1:]:
            if a["partido_id"] == b["partido_id"]:
                continue
            c = a["cuota"] * b["cuota"]
            if nivel["rango"][0] <= c <= nivel["rango"][1]:
                nota = fiab(a) + fiab(b)
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
        ultimo = max(datetime.fromisoformat(p["fecha"][:16]) for p in act["picks"]).replace(tzinfo=MADRID)
        if any(r is None for r in res) and datetime.now(MADRID) - ultimo > timedelta(hours=30):
            # pasado más de un día sin dato (p. ej. jugador que no jugó): bet365 la anula → cuenta como acertada
            res = [True if r is None else r for r in res]
        if all(r is not None for r in res) or any(r is False for r in res):   # una pata fallada ya es roja
            verde = all(r is True for r in res)
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
            elegido = elegir(picks["dias"][dia], fecha=dia)
            if elegido:
                _, sel, cuota = elegido
                ahora = datetime.now(MADRID)
                # se publica a las 11:00; si se prepara más tarde ese mismo día, dentro de 15 min
                hora = "11:00" if dia > hoy or ahora.strftime("%H:%M") < "10:45" else (ahora + timedelta(minutes=15)).strftime("%H:%M")
                estado["actual"] = {"dia": dia, "escalon": estado["escalon"], "stake": estado["stake"],
                                    "cuota": cuota, "picks": sel, "hora": hora,
                                    "anterior": estado["historial"][-1] if estado["historial"] else None}
                print(f"Escalón {estado['escalon']} para {dia}: x{cuota}")
                break
    elif estado.get("actual") and picks:
        # si el escalón aún no ha empezado, se actualizan cuotas/picks con los datos nuevos
        act = estado["actual"]
        primero = min(p["fecha"] for p in act["picks"])
        publicado = f"{act['dia']}-escalera" in (leer(DATOS.parent / "publicaciones" / "enviados.json", {}) or {})
        if not publicado and primero > datetime.now(MADRID).strftime("%Y-%m-%dT%H:%M") and act["dia"] in picks["dias"]:
            elegido = elegir(picks["dias"][act["dia"]], fecha=act["dia"])
            if elegido:
                act["picks"], act["cuota"] = elegido[1], elegido[2]
            elif any(es_sin_empate(p["mercado"], p["opcion"]) for p in act["picks"]):
                estado["actual"] = None

    ESTADO.write_text(json.dumps(estado, ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
