"""
Detector de apuestas de valor y registro de resultados.

Se ejecuta después de bot.py. Con los partidos guardados calcula la
probabilidad de cada apuesta (modelo de Poisson con xG para los goles y
binomial negativa para los córners), la compara con la cuota de Bet365 y
marca las apuestas en las que la cuota paga más de lo que debería.

Genera:
- VALOR.md: apuestas de valor de los próximos partidos.
- RESULTADOS.md: aciertos, beneficio y rentabilidad de los picks ya jugados.
- Una sección "Probabilidades del modelo" al final de cada informe.
- datos/valor.json y datos/registro_picks.json para análisis posteriores.
"""

import math
from collections import defaultdict
from datetime import timedelta

from bot import (COMPETICIONES, DATOS, EXTRA, INFORMES, MADRID, RAIZ, TRADUCCION_CUOTAS,
                 ahora, escribir, f, fecha, leer, num, partidos_guardados, por_equipo, slug,
                 traducir_opcion)

# ---------------------------------------------------------------- ajustes

VALOR_MIN = 0.06       # la cuota debe pagar al menos un 6 % más de lo justo
PROB_MIN = 0.30        # se descartan selecciones muy improbables
CUOTA_MIN, CUOTA_MAX = 1.30, 6.00
PARTIDOS_MIN = 5       # mínimo para calcular probabilidades
PARTIDOS_FIABLE = 8    # mínimo para recomendar una apuesta
PESO_MODELO = 0.5      # la probabilidad final mezcla modelo y mercado a partes iguales
PESO_PRIOR = 1         # partidos "ficticios" de equipo medio (calibrado con los partidos de octubre)
LIGAS = {140, 39, 135, 78, 61}
DISPERSION_CORNERS = 8   # binomial negativa: varianza = media + media² / r (calibrado)
FIABILIDAD_CORNERS = 0.3  # los córners son poco predecibles: se acerca la previsión a la media general
MAX_GOLES = 11
MAX_POR_PARTIDO = 2

REGISTRO = DATOS / "registro_picks.json"

# ---------------------------------------------------------------- distribuciones


def poisson(k, lam):
    return math.exp(-lam) * lam ** k / math.factorial(k)


def binom_neg(k, media, r=DISPERSION_CORNERS):
    p = r / (r + media)
    return math.exp(math.lgamma(k + r) - math.lgamma(r) - math.lgamma(k + 1)
                    + r * math.log(p) + k * math.log(1 - p))


def matriz(lh, la):
    return [[poisson(i, lh) * poisson(j, la) for j in range(MAX_GOLES)] for i in range(MAX_GOLES)]


def prob_mas_de(linea, pmf):
    """P(X > línea) para una línea .5, a partir de una función de probabilidad."""
    return 1 - sum(pmf(k) for k in range(int(math.floor(linea)) + 1))


# ---------------------------------------------------------------- medias generales


def medias_generales(todos):
    gl = gv = n = c1 = gt = 0
    corners, corners_l = [], []
    for p in todos:
        if not p or p["goles"][0] is None:
            continue
        n += 1
        gl += p["goles"][0]
        gv += p["goles"][1]
        if p["descanso"][0] is not None:
            c1 += p["descanso"][0] + p["descanso"][1]
            gt += p["goles"][0] + p["goles"][1]
        sl = p["stats"].get(str(p["local"]["id"]))
        sv = p["stats"].get(str(p["visitante"]["id"]))
        if sl and sv:
            corners.append((sl.get("corners") or 0) + (sv.get("corners") or 0))
            corners_l.append(sl.get("corners") or 0)
    return {
        "local": gl / n if n else 1.45,
        "visitante": gv / n if n else 1.2,
        "parte1": c1 / gt if gt else 0.44,
        "corners": sum(corners) / len(corners) if corners else 9.8,
        "corners_local": sum(corners_l) / len(corners_l) if corners_l else 5.2,
    }


def produccion(p, eq):
    """Goles 'merecidos' de un equipo en un partido: mezcla de xG (más estable) y goles reales."""
    local = p["local"]["id"] == eq
    g = p["goles"][0] if local else p["goles"][1]
    xg = (p["stats"].get(str(eq)) or {}).get("xg")
    return 0.6 * xg + 0.4 * g if xg is not None else g


def corners_de(p, eq):
    st = p["stats"].get(str(eq))
    rival = p["visitante"]["id"] if p["local"]["id"] == eq else p["local"]["id"]
    if not st or not p["stats"].get(str(rival)):
        return None
    return st.get("corners") or 0


def ratings(todos, base_local, base_visit, valor_de, iteraciones=40):
    """Ataque y defensa de cada equipo ajustados por la calidad de los rivales.

    Modelo multiplicativo: esperado(local) = base_local · ataque_local · defensa_visitante.
    Un ataque de 1,2 significa que genera un 20 % más que la media frente al mismo rival;
    una defensa de 1,2, que concede un 20 % más. Con pocos partidos se acercan a 1."""
    partidos = []
    for p in todos:
        if not p or p["goles"][0] is None:
            continue
        loc, vis = p["local"]["id"], p["visitante"]["id"]
        vl, vv = valor_de(p, loc), valor_de(p, vis)
        if vl is None or vv is None:
            continue
        partidos.append((loc, vis, vl, vv))
    equipos = {e for m in partidos for e in m[:2]}
    ata = {e: 1.0 for e in equipos}
    de = {e: 1.0 for e in equipos}
    for _ in range(iteraciones):
        num_a, den_a = defaultdict(float), defaultdict(float)
        num_d, den_d = defaultdict(float), defaultdict(float)
        for loc, vis, vl, vv in partidos:
            num_a[loc] += vl
            den_a[loc] += base_local * de[vis]
            num_a[vis] += vv
            den_a[vis] += base_visit * de[loc]
            num_d[loc] += vv
            den_d[loc] += base_visit * ata[vis]
            num_d[vis] += vl
            den_d[vis] += base_local * ata[loc]
        m = (base_local + base_visit) / 2
        ata = {e: (num_a[e] + PESO_PRIOR * m) / (den_a[e] + PESO_PRIOR * m) for e in equipos}
        de = {e: (num_d[e] + PESO_PRIOR * m) / (den_d[e] + PESO_PRIOR * m) for e in equipos}
        ma, md = sum(ata.values()) / len(ata), sum(de.values()) / len(de)
        ata = {e: v / ma for e, v in ata.items()}
        de = {e: v / md for e, v in de.items()}
    return ata, de


def preparar(todos, gen):
    """Calcula una vez los ratings de goles y de córners de todos los equipos."""
    goles = ratings(todos, gen["local"], gen["visitante"], produccion)
    cl = gen["corners_local"]
    cv = gen["corners"] - cl
    corners = ratings(todos, cl, cv, corners_de)
    return {"goles": goles, "corners": corners, "gen": gen}


# ---------------------------------------------------------------- modelo


def modelo(p, idx, rt):
    gen = rt["gen"]
    loc, vis = p["teams"]["home"]["id"], p["teams"]["away"]["id"]
    pl, pv = idx.get(loc, []), idx.get(vis, [])
    if len(pl) < PARTIDOS_MIN or len(pv) < PARTIDOS_MIN:
        return None
    ata, de = rt["goles"]
    if loc not in ata or vis not in ata:
        return None
    lh = max(gen["local"] * ata[loc] * de[vis], 0.15)
    la = max(gen["visitante"] * ata[vis] * de[loc], 0.15)

    m = matriz(lh, la)
    p1 = sum(m[i][j] for i in range(MAX_GOLES) for j in range(MAX_GOLES) if i > j)
    px = sum(m[i][i] for i in range(MAX_GOLES))
    p2 = 1 - p1 - px
    ambos = 1 - sum(m[0]) - sum(m[i][0] for i in range(MAX_GOLES)) + m[0][0]
    total = lambda k: sum(m[i][k - i] for i in range(k + 1) if i < MAX_GOLES and k - i < MAX_GOLES)

    s = gen["parte1"]
    m1 = matriz(lh * s, la * s)
    total1 = lambda k: sum(m1[i][k - i] for i in range(k + 1) if i < MAX_GOLES and k - i < MAX_GOLES)
    d1 = sum(m1[i][j] for i in range(MAX_GOLES) for j in range(MAX_GOLES) if i > j)
    dx = sum(m1[i][i] for i in range(MAX_GOLES))

    mc = None
    ca, cd = rt["corners"]
    if loc in ca and vis in ca:
        cl = gen["corners_local"]
        mc = cl * ca[loc] * cd[vis] + (gen["corners"] - cl) * ca[vis] * cd[loc]
        mc = gen["corners"] + FIABILIDAD_CORNERS * (mc - gen["corners"])

    # Confianza: los equipos con pocos partidos en las grandes ligas tienen datos
    # menos comparables (p. ej. rivales de Conference que solo juegan previas)
    en_liga = lambda eq, lista: sum(1 for x in lista if x["liga"] in LIGAS)
    fiable = min(len(pl), len(pv)) >= PARTIDOS_FIABLE and min(en_liga(loc, pl), en_liga(vis, pv)) >= 4

    return {
        "lh": lh, "la": la, "corners": mc, "fiable": fiable,
        "1x2": {"Home": p1, "Draw": px, "Away": p2},
        "ambos": ambos, "total": total, "total1": total1,
        "descanso": {"Home": d1, "Draw": dx, "Away": 1 - d1 - dx},
    }


def prob_seleccion(mod, mercado, opcion):
    """Probabilidad del modelo para una selección de Bet365, o None si no se modela."""
    o = str(opcion)
    if mercado == "Match Winner":
        return mod["1x2"].get(o)
    if mercado == "First Half Winner":
        return mod["descanso"].get(o)
    if mercado == "Double Chance":
        x = mod["1x2"]
        return {"Home/Draw": x["Home"] + x["Draw"], "Home/Away": x["Home"] + x["Away"],
                "Draw/Away": x["Draw"] + x["Away"]}.get(o)
    if mercado == "Both Teams Score":
        return {"Yes": mod["ambos"], "No": 1 - mod["ambos"]}.get(o)
    partes = o.split()
    if len(partes) != 2 or partes[0] not in ("Over", "Under"):
        return None
    try:
        linea = float(partes[1])
    except ValueError:
        return None
    if abs(linea * 2 - round(linea * 2)) > 1e-9 or linea == int(linea):
        return None  # solo líneas .5 (sin empates ni líneas asiáticas)
    if mercado == "Goals Over/Under":
        pmf = mod["total"]
    elif mercado == "Goals Over/Under First Half":
        pmf = mod["total1"]
    elif mercado == "Total - Home":
        pmf = lambda k: poisson(k, mod["lh"])
    elif mercado == "Total - Away":
        pmf = lambda k: poisson(k, mod["la"])
    elif mercado == "Corners Over Under" and mod["corners"]:
        pmf = lambda k: binom_neg(k, mod["corners"])
    else:
        return None
    mas = prob_mas_de(linea, pmf)
    return mas if partes[0] == "Over" else 1 - mas


def prob_casa(opciones, opcion, mercado):
    """Probabilidad implícita de la cuota, quitando el margen de la casa."""
    cuotas = {str(v): num(o) for v, o in opciones if num(o)}
    if str(opcion) not in cuotas:
        return None
    if mercado == "Double Chance":
        grupo = list(cuotas)
    elif str(opcion).split()[0] in ("Over", "Under"):
        linea = str(opcion).split()[-1]
        grupo = [k for k in cuotas if k.split()[-1] == linea]
    else:
        grupo = list(cuotas)
    total = sum(1 / cuotas[k] for k in grupo)
    if mercado == "Double Chance":
        total /= 2  # cada resultado aparece en dos selecciones
    return (1 / cuotas[str(opcion)]) / total if total else None


# ---------------------------------------------------------------- evaluación


def evaluar(p, ex, idx, rt):
    """Devuelve (modelo, filas para el informe, picks de valor) de un partido.

    La probabilidad 'estimada' mezcla la del modelo con la del mercado: las casas
    aciertan mucho, así que solo se considera valor cuando el modelo discrepa con
    fuerza y la mezcla sigue por encima de lo que paga la cuota."""
    mod = modelo(p, idx, rt)
    cuotas = ex.get("cuotas") or {}
    if not mod:
        return mod, [], []
    filas, picks = [], []
    for mercado, opciones in cuotas.items():
        for opcion, cuota in opciones:
            prob = prob_seleccion(mod, mercado, opcion)
            c = num(cuota)
            if prob is None or not c:
                continue
            casa = prob_casa(opciones, opcion, mercado)
            final = PESO_MODELO * prob + (1 - PESO_MODELO) * casa if casa is not None else prob
            valor = final * c - 1
            fila = {"mercado": mercado, "opcion": opcion, "cuota": c, "prob": prob,
                    "casa": casa, "final": final, "valor": valor}
            filas.append(fila)
            if (mod["fiable"] and valor >= VALOR_MIN and final >= PROB_MIN
                    and CUOTA_MIN <= c <= CUOTA_MAX):
                picks.append(fila)
    # Una sola selección por mercado y partido: la de más valor
    mejor = {}
    for k in picks:
        if k["mercado"] not in mejor or k["valor"] > mejor[k["mercado"]]["valor"]:
            mejor[k["mercado"]] = k
    # Máximo 2 por partido: varias apuestas del mismo partido suelen apostar a la misma idea
    return mod, filas, sorted(mejor.values(), key=lambda k: -k["valor"])[:MAX_POR_PARTIDO]


def nombre_seleccion(mercado, opcion):
    return f"{TRADUCCION_CUOTAS.get(mercado, mercado)}: {traducir_opcion(opcion)}"


def pct(x):
    return "–" if x is None else f"{round(100 * x)}%"


def seccion_informe(mod, filas, picks):
    out = ["", "## Probabilidades del modelo"]
    if not mod:
        out.append("_No hay suficientes partidos de alguno de los dos equipos para calcularlas._")
        return "\n".join(out) + "\n"
    out.append(f"_Goles esperados: local {f(mod['lh'], 2)} · visitante {f(mod['la'], 2)}"
               + (f" · córners esperados {f(mod['corners'], 1)}" if mod["corners"] else "") + "._")
    if not filas:
        out.append("\n_Sin cuotas de Bet365 todavía para comparar._")
        return "\n".join(out) + "\n"
    if not mod["fiable"]:
        out.append("\n_Datos poco comparables para alguno de los equipos (pocos partidos en las grandes "
                   "ligas): se muestran las probabilidades pero no se recomiendan apuestas._")
    elegidos = {(k["mercado"], k["opcion"]) for k in picks}
    out += ["", "| Apuesta | Modelo | Casa | Estimada | Cuota | Valor |", "|---|---|---|---|---|---|"]
    interesantes = [x for x in filas if x["mercado"] in ("Match Winner", "Both Teams Score", "Double Chance")
                    or (x["casa"] or 0) >= 0.2 and (x["casa"] or 1) <= 0.8]
    for x in sorted(interesantes, key=lambda x: (list(TRADUCCION_CUOTAS).index(x["mercado"])
                                                 if x["mercado"] in TRADUCCION_CUOTAS else 99, str(x["opcion"]))):
        marca = " ✅" if (x["mercado"], x["opcion"]) in elegidos else ""
        out.append(f"| {nombre_seleccion(x['mercado'], x['opcion'])}{marca} | {pct(x['prob'])} | {pct(x['casa'])} "
                   f"| {pct(x['final'])} | {x['cuota']:.2f} | {x['valor'] * 100:+.0f}% |")
    out.append("\n_Estimada = mezcla de modelo y casa. ✅ = apuesta de valor._")
    return "\n".join(out) + "\n"


# ---------------------------------------------------------------- registro de picks


def liquidar(pick, partido):
    """Devuelve 'ganada', 'perdida', 'nula' o None si aún no se puede saber."""
    gl, gv = partido["goles"]
    hl, hv = partido["descanso"]
    m, o = pick["mercado"], str(pick["opcion"])
    if gl is None:
        return None
    gana = None
    if m == "Match Winner":
        gana = {"Home": gl > gv, "Draw": gl == gv, "Away": gl < gv}.get(o)
    elif m == "Double Chance":
        gana = {"Home/Draw": gl >= gv, "Home/Away": gl != gv, "Draw/Away": gl <= gv}.get(o)
    elif m == "Both Teams Score":
        gana = (gl > 0 and gv > 0) if o == "Yes" else not (gl > 0 and gv > 0)
    elif m == "First Half Winner" and hl is not None:
        gana = {"Home": hl > hv, "Draw": hl == hv, "Away": hl < hv}.get(o)
    else:
        lado, linea = o.split()[0], float(o.split()[1])
        valor = None
        if m == "Goals Over/Under":
            valor = gl + gv
        elif m == "Goals Over/Under First Half" and hl is not None:
            valor = hl + hv
        elif m == "Total - Home":
            valor = gl
        elif m == "Total - Away":
            valor = gv
        elif m == "Corners Over Under":
            st = list(partido["stats"].values())
            if len(st) == 2 and all(st):
                valor = sum((s.get("corners") or 0) for s in st)
        if valor is not None:
            gana = valor > linea if lado == "Over" else valor < linea
    if gana is None:
        return None
    return "ganada" if gana else "perdida"


def actualizar_registro(evaluados):
    registro = leer(REGISTRO, [])
    ya = ahora()
    # Los picks de partidos que aún no han empezado se recalculan en cada ejecución
    registro = [r for r in registro if not (r["estado"] == "pendiente" and fecha(r["fecha"]) > ya)]
    claves = {r["id"] for r in registro}
    for p, picks in evaluados:
        if fecha(p["fixture"]["date"]) <= ya:
            continue
        for k in picks:
            clave = f"{p['fixture']['id']}|{k['mercado']}|{k['opcion']}"
            if clave in claves:
                continue
            registro.append({
                "id": clave, "fixture": p["fixture"]["id"], "fecha": p["fixture"]["date"],
                "competicion": COMPETICIONES.get(p["league"]["id"], p["league"]["name"]),
                "partido": f"{p['teams']['home']['name']} – {p['teams']['away']['name']}",
                "mercado": k["mercado"], "opcion": k["opcion"], "cuota": k["cuota"],
                "prob": round(k["final"], 4), "prob_modelo": round(k["prob"], 4), "valor": round(k["valor"], 4),
                "estado": "pendiente", "beneficio": None,
            })
    # Liquida los picks de partidos ya terminados
    for r in registro:
        if r["estado"] != "pendiente":
            continue
        partido = leer(DATOS / "partidos" / f"{r['fixture']}.json")
        if partido:
            res = liquidar(r, partido)
            if res:
                r["estado"] = res
                r["beneficio"] = round(r["cuota"] - 1, 2) if res == "ganada" else -1.0
        elif fecha(r["fecha"]) < ya - timedelta(days=4):
            r["estado"], r["beneficio"] = "nula", 0.0  # partido aplazado o sin datos
    registro.sort(key=lambda r: r["fecha"])
    escribir(REGISTRO, registro)
    return registro


def resumen_resultados(registro):
    hechos = [r for r in registro if r["estado"] in ("ganada", "perdida")]
    pendientes = [r for r in registro if r["estado"] == "pendiente"]
    out = ["# Resultados de las apuestas de valor", "",
           f"_Actualizado el {ahora().astimezone(MADRID).strftime('%d/%m/%Y %H:%M')}. "
           "Cada pick cuenta como 1 unidad apostada a la cuota de Bet365 de la última "
           "actualización antes del partido._", ""]
    if not hechos:
        out.append("_Todavía no hay picks terminados. Los primeros resultados aparecerán "
                   "en cuanto se jueguen los partidos marcados en VALOR.md._")
    else:
        def bloque(lista):
            g = sum(r["estado"] == "ganada" for r in lista)
            ben = sum(r["beneficio"] for r in lista)
            cm = sum(r["cuota"] for r in lista) / len(lista)
            return len(lista), g, ben, cm
        n, g, ben, cm = bloque(hechos)
        out += [f"- **Picks jugados:** {n} · **acertados:** {g} ({round(100 * g / n)}%)",
                f"- **Beneficio:** {ben:+.2f} unidades · **rentabilidad (yield):** {100 * ben / n:+.1f}%",
                f"- **Cuota media:** {cm:.2f} · **pendientes:** {len(pendientes)}", ""]
        if n < 100:
            out.append(f"_Con {n} picks el resultado todavía depende mucho de la suerte; "
                       "a partir de unos 200–300 se puede juzgar si el modelo funciona._\n")
        por = defaultdict(list)
        for r in hechos:
            por[TRADUCCION_CUOTAS.get(r["mercado"], r["mercado"])].append(r)
        out += ["## Por tipo de apuesta", "", "| Mercado | Picks | Acertados | Beneficio | Yield |",
                "|---|---|---|---|---|"]
        for nombre, lista in sorted(por.items(), key=lambda x: -len(x[1])):
            n2, g2, b2, _ = bloque(lista)
            out.append(f"| {nombre} | {n2} | {g2} ({round(100 * g2 / n2)}%) | {b2:+.2f} | {100 * b2 / n2:+.1f}% |")
        out += ["", "## Últimos picks", "", "| Fecha | Partido | Apuesta | Cuota | Resultado | Unidades |",
                "|---|---|---|---|---|---|"]
        for r in reversed(hechos[-40:]):
            out.append(f"| {r['fecha'][:10]} | {r['partido']} | {nombre_seleccion(r['mercado'], r['opcion'])} "
                       f"| {r['cuota']:.2f} | {'✅' if r['estado'] == 'ganada' else '❌'} | {r['beneficio']:+.2f} |")
    (RAIZ / "RESULTADOS.md").write_text("\n".join(out) + "\n", encoding="utf-8")


# ---------------------------------------------------------------- inicio


def main():
    todos = partidos_guardados()
    idx = por_equipo(todos)
    gen = medias_generales(todos)
    rt = preparar(todos, gen)
    print(f"Medias generales: local {gen['local']:.2f}, visitante {gen['visitante']:.2f}, "
          f"goles 1ª parte {gen['parte1']:.0%}, córners {gen['corners']:.1f}")

    proximos = []
    for ruta in EXTRA.glob("*.json"):
        ex = leer(ruta, {})
        p = ex.get("partido")
        if p and fecha(p["fixture"]["date"]) > ahora() - timedelta(hours=3):
            proximos.append((p, ex))
    proximos.sort(key=lambda x: x[0]["fixture"]["date"])

    evaluados, tabla, resumen = [], [], []
    for p, ex in proximos:
        mod, filas, picks = evaluar(p, ex, idx, rt)
        evaluados.append((p, picks))
        hora = fecha(p["fixture"]["date"]).astimezone(MADRID)
        nombre = f"{hora.strftime('%Y-%m-%d')}_{slug(p['teams']['home']['name'])}-vs-{slug(p['teams']['away']['name'])}.md"
        ruta = INFORMES / nombre
        if ruta.exists():
            with open(ruta, "a", encoding="utf-8") as fh:
                fh.write(seccion_informe(mod, filas, picks))
        partido = f"{p['teams']['home']['name']} – {p['teams']['away']['name']}"
        for k in picks:
            tabla.append((hora, p, partido, nombre, k))
            resumen.append({"fecha": p["fixture"]["date"], "partido": partido,
                            "competicion": COMPETICIONES.get(p["league"]["id"]),
                            "mercado": k["mercado"], "opcion": k["opcion"], "cuota": k["cuota"],
                            "prob_modelo": round(k["prob"], 3), "prob_casa": round(k["casa"] or 0, 3),
                            "prob_estimada": round(k["final"], 3),
                            "valor": round(k["valor"], 3), "informe": f"informes/{nombre}"})

    out = ["# Apuestas de valor", "",
           f"_Actualizado el {ahora().astimezone(MADRID).strftime('%d/%m/%Y %H:%M')} (hora España)._", "",
           f"Selecciones en las que la probabilidad estimada (mitad modelo, mitad mercado) supera a la que implica la cuota de Bet365 "
           f"(valor mínimo {round(VALOR_MIN * 100)}%, cuotas entre {CUOTA_MIN:.2f} y {CUOTA_MAX:.2f}). "
           "El **valor** es lo que pagaría de más la cuota si el modelo acierta la probabilidad: "
           "un +10% significa que a largo plazo ganarías 10 céntimos por cada euro apostado.", "",
           "> Es un modelo estadístico: no sabe de rotaciones, motivación ni noticias de última hora. "
           "Revisa siempre el informe del partido antes de apostar.", ""]
    if not tabla:
        out.append("_Ahora mismo no hay apuestas de valor con cuotas publicadas._")
    dia = None
    for hora, p, partido, nombre, k in tabla:
        d = hora.strftime("%d/%m")
        if d != dia:
            out += ["", f"## {d}", "", "| Hora | Partido | Apuesta | Cuota | Modelo | Casa | Estimada | Valor |",
                    "|---|---|---|---|---|---|---|---|"]
            dia = d
        out.append(f"| {hora.strftime('%H:%M')} | [{partido}](informes/{nombre}) "
                   f"| {nombre_seleccion(k['mercado'], k['opcion'])} | {k['cuota']:.2f} "
                   f"| {pct(k['prob'])} | {pct(k['casa'])} | {pct(k['final'])} | **{k['valor'] * 100:+.0f}%** |")
    out += ["", "Ver el historial de aciertos en [RESULTADOS.md](RESULTADOS.md)."]
    (RAIZ / "VALOR.md").write_text("\n".join(out) + "\n", encoding="utf-8")
    escribir(DATOS / "valor.json", resumen)

    registro = actualizar_registro(evaluados)
    resumen_resultados(registro)
    print(f"- Apuestas de valor encontradas: {len(tabla)} · picks en el registro: {len(registro)}")


if __name__ == "__main__":
    main()
