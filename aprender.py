"""
Aprender de los resultados · se ejecuta cada noche (y en cada recogida) cuando ya hay partidos terminados.

1. Calibra la fiabilidad: compara lo que prometía cada pick (frecuencia histórica) con lo que pasó
   de verdad en todos los picks del bot ya corregidos (datos/registro_aciertos.json). Aprende:
     - w: cuánto hay que fiarse de la frecuencia frente a la cuota de bet365
          prob = implícita + w · (frecuencia − implícita)
     - correcciones por tipo de mercado, por mercado concreto y por liga (lo que falla más de lo
       esperado baja; lo que acierta más, sube). Con pocos datos las correcciones son pequeñas
       (se "encogen" hacia 0) y crecen a medida que se repiten los fallos o aciertos.
   picks.py usa esto: ordena por la probabilidad aprendida y descarta los picks cuya probabilidad
   aprendida ya no supera la de la cuota (si un tipo de pick falla una y otra vez, deja de salir).
   Sale en datos/aprendizaje.json.

2. Lecciones del día: repasa cada pick fallado (del bot y de los posts publicados), explica por qué
   falló (partido cerrado, se quedó a 1, el jugador no jugó…), apunta qué ha cambiado en el modelo y
   lo manda por Telegram al dueño del canal una vez al día. Se guarda en LECCIONES.md.
"""
import json
import os
from collections import defaultdict
from datetime import datetime, timedelta

from bot import DATOS, MADRID, PARTIDOS, RAIZ, leer

REGISTRO = DATOS / "registro_aciertos.json"
SALIDA = DATOS / "aprendizaje.json"
LECCIONES = RAIZ / "LECCIONES.md"
ESTADO = DATOS / "lecciones_enviadas.json"

W_PREVIO, LAMBDA = 0.5, 4.0     # sin datos: medio camino entre la frecuencia y la cuota (vale por ~300 picks)
K = 15                          # "partidos de prudencia": una corrección necesita repetirse para pesar
VIDA_MEDIA = 45                 # días: lo reciente pesa más
MIN_EVIDENCIA = 25              # para descartar picks: partidos (no picks) de su tipo de mercado ya jugados
TOPE = 0.25


def seg_tipo(p):
    return f"jugador:{p.get('campo')}" if p.get("tipo") == "jugador" else p.get("tipo") or "otro"


def seg_fino(p):
    if p.get("tipo") == "jugador":
        return f"jugador:{p.get('campo')}:{p.get('n')}"
    return f"{p.get('mercado')}|{p.get('opcion')}"


def peso(p, hoy):
    try:
        dias = (hoy - datetime.fromisoformat(p["fecha"][:10])).days
    except (KeyError, ValueError):
        dias = 0
    return 0.5 ** (max(dias, 0) / VIDA_MEDIA)


def implicita(p):
    """Probabilidad que da el mercado. Si hay cuotas de otras casas, se usa su mediana (el consenso
    acierta más que una sola casa); si no, la de bet365."""
    cuota = float(p["cuota"])
    vm = p.get("valor_mercado")
    if vm is not None and -0.3 < vm < 0.3:
        cuota = cuota / (1 + vm)
    return 1 / cuota


def tramo_cuota(p):
    c = float(p.get("cuota") or 0)
    return "≤1,35" if c <= 1.35 else "1,36-1,60" if c <= 1.60 else ">1,60"


def senal(p):
    vm = p.get("valor_mercado")
    if vm is None:
        return "sin otras casas"
    return "bet365 paga más" if vm > 0.02 else "bet365 paga menos" if vm < -0.02 else "igual que el resto"


_CAL = {}


def calibracion():
    if "c" not in _CAL:
        _CAL["c"] = leer(DATOS / "calibracion.json", {}) or {}
    return _CAL["c"]


def frec_calibrada(p, cal=None):
    """La frecuencia de los últimos partidos corregida con lo que pasó de verdad en el histórico
    (calibrar_historico.py): p. ej. «1+ tiro a puerta» que dice 75 % solo salía el 49 %."""
    f = float(p["frecuencia"])
    cal = calibracion() if cal is None else cal
    if not cal:
        return f

    def recta(m):
        return m["real"] + m["pendiente"] * (f - m["frec_media"])
    t = (cal.get("tipos") or {}).get(seg_tipo(p)) or cal.get("global")
    m = (cal.get("mercados") or {}).get(seg_fino(p))
    if not t:
        return f
    v = recta(t)
    if m:
        w = m["n"] / (m["n"] + 100)          # con pocos casos manda el tipo de mercado
        v = w * recta(m) + (1 - w) * v
    return max(0.05, min(0.97, v))


def calibrar(resueltos):
    hoy = datetime.now(MADRID).replace(tzinfo=None)
    por_partido = defaultdict(int)
    for p in resueltos:
        por_partido[p.get("partido_id")] += 1
    filas = []
    for p in resueltos:
        try:
            imp, f = implicita(p), frec_calibrada(p)
        except (KeyError, TypeError, ValueError, ZeroDivisionError):
            continue
        # los picks de un mismo partido caen juntos: entre todos cuentan como un partido
        filas.append((p, imp, f, float(bool(p["acierto"])), peso(p, hoy) / por_partido[p.get("partido_id")]))
    sxy = sum(w * (y - imp) * (f - imp) for _, imp, f, y, w in filas)
    sxx = sum(w * (f - imp) ** 2 for _, imp, f, y, w in filas)
    w_frec = max(0.0, min(1.0, (sxy + LAMBDA * W_PREVIO) / (sxx + LAMBDA)))

    def ajustar(clave, base):
        res, n = defaultdict(float), defaultdict(float)
        for i, (p, imp, f, y, w) in enumerate(filas):
            res[clave(p)] += w * (y - base[i])
            n[clave(p)] += w
        return {k: round(max(-TOPE, min(TOPE, res[k] / (n[k] + K))), 4) for k in res}, n

    base = [imp + w_frec * (f - imp) for _, imp, f, y, w in filas]
    a_tipo, n_tipo = ajustar(seg_tipo, base)
    base = [b + a_tipo[seg_tipo(x[0])] for b, x in zip(base, filas)]
    a_fino, n_fino = ajustar(seg_fino, base)
    base = [b + a_fino[seg_fino(x[0])] for b, x in zip(base, filas)]
    a_liga, n_liga = ajustar(lambda p: p.get("competicion") or "?", base)
    base = [b + a_liga[x[0].get("competicion") or "?"] for b, x in zip(base, filas)]
    a_cuota, n_cuota = ajustar(tramo_cuota, base)
    base = [b + a_cuota[tramo_cuota(x[0])] for b, x in zip(base, filas)]
    a_senal, n_senal = ajustar(senal, base)

    def tabla(aj, n, clave):
        out = {}
        for k in aj:
            sel = [x for x in filas if clave(x[0]) == k]
            out[k] = {"ajuste": aj[k], "n": len(sel), "partidos": round(n[k], 1), "aciertos": int(sum(x[3] for x in sel)),
                      "prometido": round(sum(x[2] for x in sel) / len(sel), 3),
                      "cuota_implicita": round(sum(x[1] for x in sel) / len(sel), 3)}
        return out

    n = len(filas)
    return {"generado": datetime.now(MADRID).strftime("%Y-%m-%d %H:%M"), "picks_usados": n,
            "aciertos": int(sum(x[3] for x in filas)),
            "prometido_medio": round(sum(x[2] for x in filas) / n, 3) if n else None,
            "implicita_media": round(sum(x[1] for x in filas) / n, 3) if n else None,
            "w_frecuencia": round(w_frec, 3),
            "tipos": tabla(a_tipo, n_tipo, seg_tipo), "mercados": tabla(a_fino, n_fino, seg_fino),
            "ligas": tabla(a_liga, n_liga, lambda p: p.get("competicion") or "?"),
            "cuotas": tabla(a_cuota, n_cuota, tramo_cuota), "senales": tabla(a_senal, n_senal, senal)}


def prob_aprendida(p, ap):
    """Probabilidad real estimada de un pick con lo aprendido (None si no hay modelo o cuota)."""
    if not ap or not p.get("cuota"):
        return None
    imp = implicita(p)
    prob = imp + ap["w_frecuencia"] * (frec_calibrada(p) - imp)
    for tabla, clave in (("tipos", seg_tipo(p)), ("mercados", seg_fino(p)),
                         ("ligas", p.get("competicion") or "?"), ("cuotas", tramo_cuota(p)), ("senales", senal(p))):
        prob += (ap.get(tabla, {}).get(clave) or {}).get("ajuste", 0)
    return max(0.01, min(0.99, prob))


def evidencia(p, ap):
    """Partidos ya jugados (ponderados) del tipo de mercado del pick."""
    return (ap.get("tipos", {}).get(seg_tipo(p)) or {}).get("partidos", 0) if ap else 0


# ---------- lecciones del día ----------

def motivo(p):
    """Explicación corta de por qué falló un pick del bot, con el partido ya terminado."""
    pa = leer(PARTIDOS / f"{p['partido_id']}.json") or {}
    g = pa.get("goles") or [None, None]
    marc = f"{g[0]}-{g[1]}" if None not in g else "?"
    t, m, o = p.get("tipo"), p.get("mercado", ""), str(p.get("opcion", ""))
    if t == "jugador":
        for lista in (pa.get("jugadores") or {}).values():
            for j in lista:
                if j.get("id") == p.get("jugador_id"):
                    if not j.get("min"):
                        return "el jugador no jugó"
                    v = j.get(p.get("campo"))
                    return f"jugó {j['min']}′ e hizo {v} (necesitaba {p.get('n')})"
        return "sin datos del jugador"
    if t == "goles" or m in ("Match Winner", "Double Chance"):
        if None in g:
            return "sin marcador"
        ht = pa.get("descanso") or [0, 0]
        ht = [x or 0 for x in ht]
        if m in ("Total - Home", "Total - Away"):
            eq = p["local"] if m == "Total - Home" else p["visitante"]
            return f"{eq} no marcó lo esperado ({marc})"
        if m == "Both Teams Score":
            return f"solo marcó un equipo o ninguno ({marc})"
        if m in ("Match Winner", "Double Chance"):
            return f"resultado {marc}"
        tot = g[0] + g[1]
        if "First Half" in m:
            tot, que = ht[0] + ht[1], "en la 1ª parte"
        elif "Second Half" in m:
            tot, que = tot - ht[0] - ht[1], "en la 2ª parte"
        else:
            que = ""
        if o.startswith("Over"):
            try:
                falta = int(float(o.split()[1]) + 0.5) - tot
                if falta > 0:
                    return f"partido cerrado ({marc}): faltó {falta} gol{'es' if falta > 1 else ''} {que}".strip()
            except (IndexError, ValueError):
                pass
        return f"resultado {marc}"
    return f"no llegó a la línea ({marc})"


def lecciones(reg, ap, previo, dia):
    fallos = [p for p in reg.values() if p.get("fecha", "")[:10] == dia and p.get("acierto") is False]
    ok = [p for p in reg.values() if p.get("fecha", "")[:10] == dia and p.get("acierto") is True]
    pend = [p for p in reg.values() if p.get("fecha", "")[:10] == dia and p.get("acierto") is None]
    lineas = [f"🧠 LECCIONES DEL {dia[8:10]}/{dia[5:7]}",
              f"Picks del bot: {len(ok)} ✅ · {len(fallos)} ❌" + (f" · {len(pend)} sin resultado" if pend else "")]
    # los posts publicados
    datos = leer(RAIZ / "docs" / "datos.json", {}) or {}
    rojos = []
    for post in datos.get("publicados_hoy", []):
        if post.get("fecha", "")[:10] != dia or post.get("estado") != "rojo":
            continue
        for x in post.get("picks", []):
            if x.get("estado") == "rojo":
                pr = (x.get("progreso") or {}).get("texto")
                rojos.append(f"• {x['texto']} → {pr or 'marcador ' + '-'.join(map(str, x.get('marcador') or []))}")
    if rojos:
        lineas += ["", "❌ Lo que falló en lo publicado:"] + sorted(set(rojos))[:15]
    if fallos:
        lineas += ["", "❌ Fallos de los picks del bot y por qué:"]
        por_motivo = defaultdict(list)
        for p in fallos:
            lineas.append(f"• {p['texto']} — {motivo(p)}")
            por_motivo[seg_tipo(p)].append(p)
        # patrones: partidos con 2+ fallos (picks del mismo partido que caen juntos)
        por_partido = defaultdict(list)
        for p in fallos:
            por_partido[f"{p['local']}–{p['visitante']}"].append(p)
        juntos = [k for k, v in por_partido.items() if len(v) >= 2]
        if juntos:
            lineas += ["", "⚠️ Partidos donde cayeron varios picks a la vez (van ligados, no conviene "
                       "meter dos del mismo partido en distintas combis): " + ", ".join(juntos)]
    # qué ha cambiado en el modelo
    if ap:
        lineas += ["", f"📐 Modelo: {ap['aciertos']}/{ap['picks_usados']} aciertos reales "
                   f"({ap['aciertos'] / max(ap['picks_usados'], 1):.0%}) frente al {ap['prometido_medio']:.0%} que "
                   f"prometían las estadísticas y el {ap['implicita_media']:.0%} de la cuota.",
                   f"Peso de la estadística frente a la cuota: {ap['w_frecuencia']:.2f}"
                   + (f" (antes {previo['w_frecuencia']:.2f})" if previo and previo.get("w_frecuencia") is not None else "")]
        cambios = []
        for tabla, nombre in (("tipos", "tipo"), ("mercados", "mercado"), ("ligas", "liga"),
                              ("cuotas", "cuota"), ("senales", "mercado de casas:")):
            for k, v in ap.get(tabla, {}).items():
                antes = ((previo or {}).get(tabla, {}).get(k) or {}).get("ajuste", 0)
                if abs(v["ajuste"]) >= 0.03 and abs(v["ajuste"] - antes) >= 0.01:
                    flecha = "⬇️ castigo" if v["ajuste"] < 0 else "⬆️ premio"
                    cambios.append((abs(v["ajuste"]), f"{flecha} {nombre} {k}: {v['aciertos']}/{v['n']} "
                                                      f"({v['ajuste'] * 100:+.0f} pts)"))
        if cambios:
            lineas += ["Ajustes nuevos:"] + [c for _, c in sorted(cambios, reverse=True)[:8]]
        lineas.append("Desde ahora los picks se ordenan con esta probabilidad aprendida y se quitan los que ya "
                      "no superan a la cuota.")
    return "\n".join(lineas)


def notas_estilos():
    """Nota de cada estilo de post del bot (1 = normal): mitad vistas en Threads frente a la mediana,
    mitad verdes frente a la media. Con pocos datos se queda cerca de 1. Sale en datos/estilos.json."""
    est_redes = leer(RAIZ / "publicaciones" / "enviados_redes.json", {}) or {}
    vistas = leer(DATOS / "threads_vistas.json", {}) or {}
    pub = {p["id"]: p for p in (leer(RAIZ / "docs" / "datos.json", {}) or {}).get("publicados", [])}
    filas = defaultdict(lambda: {"v": [], "verde": [], })
    for pid, e in est_redes.items():
        estilo = pid[11:]
        if not estilo:
            continue
        tid = (e.get("redes") or {}).get("threads")
        if tid in vistas:
            filas[estilo]["v"].append(vistas[tid])
        r = (pub.get(pid) or {}).get("resultado")
        if r in ("verde", "rojo"):
            filas[estilo]["verde"].append(1.0 if r == "verde" else 0.0)
    todas_v = sorted(v for f in filas.values() for v in f["v"])
    med = todas_v[len(todas_v) // 2] if todas_v else 0
    todas_r = [x for f in filas.values() for x in f["verde"]]
    media_r = sum(todas_r) / len(todas_r) if todas_r else 0
    k = 3
    salida = {}
    for estilo, f in filas.items():
        nv = ((sum(min(v / med, 4) for v in f["v"]) + k) / (len(f["v"]) + k)) if med else 1.0
        nr = ((sum(f["verde"]) / media_r + k) / (len(f["verde"]) + k)) if media_r else 1.0
        salida[estilo] = {"nota": round(0.5 * nv + 0.5 * nr, 3), "posts_threads": len(f["v"]),
                          "resultados": len(f["verde"]), "verdes": int(sum(f["verde"]))}
    (DATOS / "estilos.json").write_text(json.dumps({"generado": datetime.now(MADRID).strftime("%Y-%m-%d %H:%M"),
                                                    "estilos": salida}, ensure_ascii=False, indent=1) + "\n",
                                        encoding="utf-8")
    return salida


def main():
    try:
        notas_estilos()
    except Exception as e:
        print("estilos:", str(e)[:150])
    reg = leer(REGISTRO, {}) or {}
    resueltos = [p for p in reg.values() if p.get("acierto") is not None]
    previo = leer(SALIDA, {}) or {}
    ap = calibrar(resueltos) if resueltos else None
    if ap:
        SALIDA.write_text(json.dumps(ap, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        print(f"Aprendizaje: w={ap['w_frecuencia']} · {ap['aciertos']}/{ap['picks_usados']}")

    # lecciones: del día anterior si son más de las 0:00, o de hoy si ya es de noche y no queda nada
    ahora = datetime.now(MADRID)
    hoy = ahora.strftime("%Y-%m-%d")
    ayer = (ahora - timedelta(days=1)).strftime("%Y-%m-%d")
    estado = leer(ESTADO, {}) or {}
    dia = None
    for d in (ayer, hoy):
        if d in estado:
            continue
        del_dia = [p for p in reg.values() if p.get("fecha", "")[:10] == d]
        if not del_dia:
            continue
        sin = [p for p in del_dia if p.get("acierto") is None]
        if not sin or (d == ayer and ahora.hour >= 2):
            dia = d
    if not dia:
        return
    texto = lecciones(reg, ap, previo, dia)
    print(texto)
    previo_md = LECCIONES.read_text(encoding="utf-8") if LECCIONES.exists() else "# Lecciones del bot\n"
    cab, _, resto = previo_md.partition("\n")
    LECCIONES.write_text(f"{cab}\n\n## {dia}\n\n```\n{texto}\n```\n{resto}", encoding="utf-8")
    estado[dia] = ahora.strftime("%Y-%m-%d %H:%M")
    ESTADO.write_text(json.dumps(estado, ensure_ascii=False, indent=1), encoding="utf-8")
    token, canal = os.environ.get("TELEGRAM_TOKEN"), os.environ.get("TELEGRAM_CANAL")
    if token and canal:
        try:
            from publicar_telegram import api
            admins = api(token, "getChatAdministrators", {"chat_id": canal})["result"]
            duenio = next(a["user"]["id"] for a in admins if a["status"] == "creator")
            for i in range(0, len(texto), 3900):
                api(token, "sendMessage", {"chat_id": duenio, "text": texto[i:i + 3900]})
        except Exception as e:
            print("No se pudo mandar la lección:", str(e)[:150])


if __name__ == "__main__":
    main()
