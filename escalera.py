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
import math
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


# 01/11 (Marcos: «mejora las escaleras, no salen nunca»): 3 verdes de 10, nunca pasó del escalón 2. Casi siempre
# falló la pata floja (más de 2,5, córners, «gana alguna parte», Sevilla o empate con 45 %...). Ahora se elige de lo
# mismo que las combis (combis_dia.pool_partido, con todas las lecciones, árbitro y jugadores fijos): solo patas que
# el bot ve al 68 % o más (ya corregido con lo que acierta de verdad, 01/11), sin córners ni tarjetas, 2 o 3 de partidos distintos y la pareja/trío MÁS PROBABLE.
SEGURA = {"prob_min": 0.68, "rango": (1.80, 2.40), "patas": (2, 3), "comb_min": 0.50}
# 06/11: también una sola pata a ≈x2 (sin el filtro de 68 %, que es por pata de pareja): gana la opción que más sale
# 06/11 (Marcos, opción A: seguir a ≈x2): sin patas con ventaja negativa; si ningún día sale así, como mucho −0,05
MIN_VENTAJA = [-0.10]   # 06/11: la probabilidad prudente ya manda; −0,03 dejó fuera al Sevilla (salió «empate al descanso»)
# 06/11 (Marcos): nada de descanso / 1ª o 2ª parte en la escalera («Empate al descanso» no)
FUERA = ("Corner", "Card", "To Win Either Half", "Over 2.5", "Over 3.5", "First Half", "Second Half", "Halftime",
         "HT/FT", "1st Half", "2nd Half")


def elegir_pool(fecha):
    """02/11: si con lo exigente no sale (el 02/11 no salió y cayó en Lorient + «Fiorentina más tiros» al 27 %),
    se afloja un poco, pero nunca por debajo del 60 % por pata."""
    for prob_min, comb_min in ((SEGURA["prob_min"], SEGURA["comb_min"]), (0.60, 0.30)):
        r = elegir_pool_(fecha, prob_min, comb_min)
        if r:
            return r
    return None


def elegir_pool_(fecha, prob_min, comb_min):
    import itertools
    import math
    import combis_dia as C
    import picks as P
    hist = P.historial()
    ap = leer(DATOS / "aprendizaje.json") or {}
    limite = (datetime.now(MADRID) + timedelta(minutes=40)).strftime("%Y-%m-%dT%H:%M")
    pausadas = PAUSADAS.get(fecha, ())
    cand, solas, mismos = [], [], {}
    for f in C.EXTRA.glob("*.json"):
        ex = leer(f) or {}
        pa = ex.get("partido")
        if not pa or datetime.fromisoformat(pa["fixture"]["date"]).astimezone(MADRID).strftime("%Y-%m-%d") != fecha:
            continue
        ya = False
        for p in C.pool_partido(ex, hist, ap):
            k = f"{p['mercado']}|{p['opcion']}"
            if any(x in k for x in FUERA) or p["fecha"] <= limite \
                    or p.get("estimada") or p.get("solo_con_tarjetas") or not C.fijisimo(p) \
                    or p.get("liga_id") in pausadas or es_sin_empate(p["mercado"], p["opcion"]) \
                    or (p.get("ventaja") or 0) < MIN_VENTAJA[0] \
                    or (p.get("solo_bet365") and not p.get("favorito")):   # 08/11: en el parón, solo lo del favorito
                continue
            if SEGURA["rango"][0] <= p["cuota"] <= SEGURA["rango"][1]:
                solas.append(p)   # 06/11 (Marcos: «Gana el Sevilla» sola salía más que la pareja/trío del bot)
            if p["prob_aprendida"] < prob_min:
                continue
            mismos.setdefault(p["partido_id"], []).append(p)
            if not ya:
                cand.append(p)
                ya = True   # la mejor de cada partido para las parejas
    cand = sorted(cand, key=lambda p: -p["prob_aprendida"])[:14]
    # 06/11: probabilidad prudente: ni más de lo que ve el bot ni más de 5 puntos por encima de bet365 (sin margen)
    # (el bot veía «Gana el Académico Viseu» a 2,35 al 66 % y bet365 al 40 %: no es una escalera segura)
    prud = lambda p: min(p["prob_aprendida"], 1 / p["cuota"] / 1.05 + 0.05)
    mejor = None
    for p in solas:
        if prud(p) >= comb_min and (not mejor or prud(p) > mejor[0]):
            mejor = (prud(p), [p], round(p["cuota"], 2))
    for n in range(SEGURA["patas"][0], SEGURA["patas"][1] + 1):
        for comb in itertools.combinations(cand, n):
            c = math.prod(p["cuota"] for p in comb)
            if not SEGURA["rango"][0] <= c <= SEGURA["rango"][1]:
                continue
            pr = math.prod(prud(p) for p in comb)
            if pr >= comb_min and (not mejor or pr > mejor[0]):
                mejor = (pr, list(comb), round(c, 2))
    if not mejor:   # 08/11 (Marcos: «haz las escaleras igualmente»): días de un solo partido → Crear apuesta de 2
        for l in mismos.values():
            for a, b in itertools.combinations(l[:10], 2):
                if C.implica(a, b) or C.implica(b, a):
                    continue
                sel = [f"{p['partido_id']}|{p['mercado']}|{p['opcion']}" for p in (a, b)]
                c = C.cuota_real_sel(sel, [a["cuota"], b["cuota"]]) or a["cuota"] * b["cuota"]
                if not SEGURA["rango"][0] <= c <= SEGURA["rango"][1]:
                    continue
                pr = prud(a) * prud(b)
                if pr >= comb_min and (not mejor or pr > mejor[0]):
                    mejor = (pr, [a, b], round(c, 2))
    if not mejor:   # y si tampoco: una sola pata desde 1,60
        for p in (x for l in mismos.values() for x in l):
            if 1.60 <= p["cuota"] <= SEGURA["rango"][1] and prud(p) >= comb_min and (not mejor or prud(p) > mejor[0]):
                mejor = (prud(p), [p], round(p["cuota"], 2))
    return mejor


def elegir(dia, compartir=False, fecha=None):
    """Dos picks de partidos distintos con cuota total en rango, los más fiables primero.
    No comparte selección con la combi segura del mismo día; si así no sale ninguna pareja, se permite
    (26/10: ese día la escalera se quedó sin escalón por esa regla)."""
    if fecha:
        try:
            r = elegir_pool(fecha)
            if r:
                return r
        except Exception as e:
            print("escalera (pool):", str(e)[:150])
    for nivel in NIVELES:
        r = elegir_(dia, compartir, nivel, fecha) or (None if compartir else elegir_(dia, True, nivel, fecha))
        if r:
            return r
    # «todos los días tiene que haber escalera» (29/10): se afloja la ventaja poco a poco, y en último caso sin filtro
    siguiente = {-0.10: -9.0}.get(MIN_VENTAJA[0])
    if siguiente is not None:
        antes, MIN_VENTAJA[0] = MIN_VENTAJA[0], siguiente
        try:
            return elegir(dia, compartir, fecha)
        finally:
            MIN_VENTAJA[0] = antes
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
    picks = [p for p in picks if fiab(p) >= 0.60 and (p.get("ventaja") or 0) >= MIN_VENTAJA[0]]   # 06/11 sin ventaja negativa · 02/11: nada de patas al 27 % («Fiorentina más tiros»)
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
    if p and p.get("estado") in ("PST", "CANC", "ABD", "AWD", "WO"):
        return "anulada"   # 07/11: partido aplazado o suspendido: bet365 la anula
    if not p or p.get("estado") not in ("FT", "AET", "PEN"):
        return None
    r = evaluar_pick(pick, p)
    if r is None:
        from picks import no_jugo
        if no_jugo(pick, p):
            return "anulada"   # 07/11: el jugador no jugó
    return r


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
            res = ["anulada" if r is None else r for r in res]
        if all(r is not None for r in res) or any(r is False for r in res):   # una pata fallada ya es roja
            verde = all(r in (True, "anulada") for r in res) and any(r is True for r in res)
            if verde and "anulada" in res:   # 07/11 (Marcos): la cuota se rehace sin la pata anulada
                act["cuota_publicada"] = act["cuota"]
                act["cuota"] = round(math.prod(float(p["cuota"]) for p, r in zip(act["picks"], res) if r is True), 2)
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
        for dia in sorted(set(picks["dias"]) | dias_con_partidos()):   # 08/11: también días sin picks (parón)
            if dia < max(hoy, DESDE):
                continue
            ya = any(h["dia"] == dia for h in estado["historial"])
            if ya:
                continue
            elegido = elegir(picks["dias"].get(dia) or {"picks": [], "mejores_por_partido": []}, fecha=dia)
            if elegido:
                _, sel, cuota = elegido
                ahora = datetime.now(MADRID)
                # se publica a las 11:00; si se prepara más tarde ese mismo día, dentro de 15 min
                from panel_datos import ajustes
                h_esc = ajustes()["hora_escalera"]
                hora = None if dia > hoy or ahora.strftime("%H:%M") < h_esc else (ahora + timedelta(minutes=15)).strftime("%H:%M")
                estado["actual"] = {"dia": dia, "escalon": estado["escalon"], "stake": estado["stake"],
                                    "cuota": cuota, "picks": sel, "hora": hora,
                                    "anterior": estado["historial"][-1] if estado["historial"] else None}
                print(f"Escalón {estado['escalon']} para {dia}: x{cuota}")
                break
    elif estado.get("actual") and picks:
        # si el escalón aún no ha empezado, se actualizan cuotas/picks con los datos nuevos
        act = estado["actual"]
        primero = min(p["fecha"] for p in act["picks"])
        env_ruta = DATOS.parent / "publicaciones" / "enviados.json"
        enviados = leer(env_ruta, {}) or {}
        reg = enviados.get(f"{act['dia']}-escalera") or {}
        publicado = bool(reg.get("enviado") or reg.get("mensaje_id"))   # 10/11: «caducada» no es publicada
        # 10/11: si el partido del escalón se ha movido de día o aplazado (Badajoz–Tenerife → 18/11) y aún no ha
        # salido, se elige otro para ese mismo día (la escalera sale todos los días)
        movido = False
        try:
            from bot import fechas_calendario
            cal = fechas_calendario()
        except Exception:
            cal = {}
        for p in act["picks"]:
            pa = (leer(DATOS / "proximos" / f"{p['partido_id']}.json", {}) or {}).get("partido") or {}
            f = (pa.get("fixture") or {})
            nueva = cal.get(str(p["partido_id"])) or f.get("date")
            if f.get("status", {}).get("short") in ("PST", "CANC", "SUSP") or (
                    nueva and datetime.fromisoformat(str(nueva)).astimezone(MADRID).strftime("%Y-%m-%d") != act["dia"]):
                movido = True
        if not publicado and (movido or primero > datetime.now(MADRID).strftime("%Y-%m-%dT%H:%M")):
            dia_datos = picks["dias"].get(act["dia"]) or {"picks": [], "mejores_por_partido": []}
            elegido = elegir(dia_datos, fecha=act["dia"])
            if elegido and (movido or act["dia"] in picks["dias"]):
                act["picks"], act["cuota"] = elegido[1], elegido[2]
                if movido:
                    ahora = datetime.now(MADRID)
                    if ahora.strftime("%Y-%m-%d") == act["dia"]:
                        act["hora"] = (ahora + timedelta(minutes=15)).strftime("%H:%M")
                    if reg.get("caducada"):   # que pueda salir el nuevo
                        enviados.pop(f"{act['dia']}-escalera", None)
                        env_ruta.write_text(json.dumps(enviados, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
                    print(f"Escalera: partido movido, nuevo escalón x{act['cuota']}")
            elif movido:
                print("Escalera: partido movido y no hay otro pick que valga hoy")
            elif any(es_sin_empate(p["mercado"], p["opcion"]) for p in act["picks"]):
                estado["actual"] = None

    ESTADO.write_text(json.dumps(estado, ensure_ascii=False, indent=1), encoding="utf-8")


def dias_con_partidos(dias=4):
    """Días (de hoy en adelante) con algún partido sin empezar en los datos."""
    import combis_dia as C
    hoy = datetime.now(MADRID)
    hasta = (hoy + timedelta(days=dias)).strftime("%Y-%m-%d")
    salida = set()
    for f in C.EXTRA.glob("*.json"):
        pa = (leer(f) or {}).get("partido")
        if pa and pa["fixture"]["status"]["short"] in ("NS", "TBD"):
            d = datetime.fromisoformat(pa["fixture"]["date"]).astimezone(MADRID).strftime("%Y-%m-%d")
            if hoy.strftime("%Y-%m-%d") <= d <= hasta:
                salida.add(d)
    return salida


if __name__ == "__main__":
    main()
