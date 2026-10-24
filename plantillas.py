"""
El Analista · escribe los posts con plantillas.

Se ejecuta después de picks.py. Con datos/picks.json monta los posts de cada día
con el formato de Combilocas y los deja en publicaciones/auto.json, con la hora a
la que tienen que salir. El Publicador los publica desde ahí.

- Solo escribe El Analista: El Publicador nunca toca auto.json (guarda lo que
  ya ha publicado en publicaciones/enviados.json), así no se pisan.
- Los posts aún no publicados se reescriben en cada pasada con las cuotas
  nuevas; los ya publicados no se tocan.
- Ningún post sale después de su primer partido: se adelanta a 1 h antes.
- AUTO_DESDE: primer día con posts automáticos (para no duplicar lo que ya
  estaba programado a mano).
"""

import json
from datetime import datetime, timedelta

from bot import DATOS, MADRID, RAIZ, leer
from picks import es_sin_empate

AUTO = RAIZ / "publicaciones" / "auto.json"
AUTO_DESDE = "2026-10-26"                       # días anteriores ya estaban programados en Metricool
ESCALERA_DESDE = "2026-10-24"                   # la escalera ya sale sola desde el sábado
REGISTRO = DATOS / "registro_aciertos.json"
MARGEN_ANTES_PARTIDO = timedelta(minutes=60)
DIAS = ["LUNES", "MARTES", "MIÉRCOLES", "JUEVES", "VIERNES", "SÁBADO", "DOMINGO"]


def num(c):
    return f"{c:.2f}".replace(".", ",")


def lista(picks):
    return "\n".join(f"✅{i}. {p['texto']} · {num(p['cuota'])}" for i, p in enumerate(picks, 1))


def clave(p):
    return (p["partido_id"], p["mercado"], p["opcion"])


MAX_POSTS_POR_SELECCION = 2   # una misma selección no sale en más de 2 posts


def dato(picks):
    """Frase de respaldo con el dato real del pick más fiable."""
    p = max(picks, key=atractivo)
    return f"📊 {p['texto']} → {p['detalle']} en sus últimos partidos"


def atractivo(p):
    """Para las listas de picks se prefieren apuestas 'a favor' (ganar, goles, córners...)
    frente a 'menos de' o 'no marcan', que se entienden peor en redes."""
    o, m = p["opcion"], p["mercado"]
    extra = 0.0
    if o.startswith("Under") or o == "No":
        extra -= 0.08
    if m in ("Match Winner", "Double Chance", "Both Teams Score") and o != "No":
        extra += 0.04
    if m in ("Corners Over Under", "Cards Over/Under") and o.startswith("Over"):
        extra += 0.03
    return p["frecuencia"] + extra


def mejores_para_lista(picks):
    elegidos, vistos = [], set()
    for p in sorted(picks, key=atractivo, reverse=True):
        if not es_sin_empate(p["mercado"], p["opcion"]) and p["partido_id"] not in vistos:
            elegidos.append(p)
            vistos.add(p["partido_id"])
    return elegidos


def posts_del_dia(dia, d):
    f = datetime.fromisoformat(dia).replace(tzinfo=MADRID)
    nombre = DIAS[f.weekday()]
    posts = []

    usos = {}   # cuántos posts llevan ya cada selección

    def apuntar(sel):
        for p in sel:
            usos[clave(p)] = usos.get(clave(p), 0) + 1

    combis = d.get("combis") or {}
    for c_clave, hora, titulo in (("cuota_3", (11, 0), f"💥 COMBINADA CUOTA 3 DEL {nombre} 💥"),
                                  ("segura", (12, 0), f"📊 COMBI DE DATOS DEL {nombre} 📊"),
                                  ("loca", (19, 0), f"🤪 COMBI LOCA DEL {nombre} 🤪")):
        c = combis.get(c_clave)
        if not c:
            continue
        apuntar(c["picks"])
        posts.append((f"combi-{c_clave}", f.replace(hour=hora[0], minute=hora[1]), c["picks"],
                      f"{titulo}\n\n{lista(c['picks'])}\n\n🎯 Cuota total: {num(c['cuota'])}\n"
                      f"💶 10€ → {num(c['cuota'] * 10)}€\n\n{dato(c['picks'])}\n\n"
                      "🍀 ¿LA PINTAMOS DE VERDE? 👀💚"))

    esc = leer(DATOS / "escalera.json") or {}
    act = esc.get("actual")
    if act and act["dia"] == dia:
        ant = act.get("anterior")
        if not ant or ant.get("resultado") != "verde":
            intro = ("❌ Ayer se cayó. Aquí no se borra nada: otra vez desde 20€ 💪"
                     if ant else "Empezamos con 20€ y subimos un escalón cada día 🚀")
        else:
            intro = f"✅ Día {ant['escalon']} superado: {num(ant['stake'])}€ → {num(ant['stake'] * ant['cuota'])}€"
        apuntar(act["picks"])
        posts.append(("escalera", f.replace(hour=11, minute=0), act["picks"],
                      f"🪜 RETO ESCALERA · DÍA {act['escalon']}/7 🍀\n\n{intro}\n\n"
                      f"{lista(act['picks'])}\n\n🎯 Cuota {num(act['cuota'])} · "
                      f"{num(act['stake'])}€ → {num(act['stake'] * act['cuota'])}€\n\n"
                      "20€ → 40 → 80 → 160 → 320 → 640 → 1.280€\n👇 ¿Llegamos al día 7?"))

    def libres(lista_picks):
        return [p for p in lista_picks if usos.get(clave(p), 0) < MAX_POSTS_POR_SELECCION]

    mejores = mejores_para_lista(libres(d.get("picks") or []))
    if len(mejores) >= 4:
        sel = mejores[:7]
        apuntar(sel)
        posts.append(("picks-manana", (f - timedelta(days=1)).replace(hour=23, minute=0), sel,
                      f"🔥 {len(sel)} PICKS PARA MAÑANA ({nombre}) 🔥\n\n{lista(sel)}\n\n{dato(sel)}\n\n"
                      "¡Combina máximo 2 o 3! 🍀"))
    tarde = [p for p in mejores_para_lista(libres(d.get("picks") or [])) if p["fecha"][11:] >= "18:30"]
    if len(tarde) >= 4:
        sel = tarde[:7]
        apuntar(sel)
        posts.append(("picks-hoy", f.replace(hour=17, minute=30), sel,
                      f"🔥 {len(sel)} PICKS PARA HOY 🔥\n\n{lista(sel)}\n\n{dato(sel)}\n\n"
                      "¡Combina máximo 2 o 3! 🍀"))

    salida = []
    for tipo, hora, picks, texto in posts:
        if any(es_sin_empate(p["mercado"], p["opcion"]) for p in picks):
            continue  # No eliminar patas de una combi conservando su cuota anterior.
        primero = min(datetime.fromisoformat(p["fecha"]).replace(tzinfo=MADRID) for p in picks)
        hora = min(hora, primero - MARGEN_ANTES_PARTIDO)
        salida.append({"id": f"{dia}-{tipo}", "fecha": hora.strftime("%Y-%m-%dT%H:%M"),
                       "texto": texto, "foto": None, "origen": "analista", "directo": True,
                       "sel": ["|".join(map(str, clave(p))) for p in picks]})
    return salida


def balance(dia, posts_ayer):
    """Post de las 10:30 con cómo salió lo de ayer. Solo si ya está todo corregido."""
    reg = leer(REGISTRO, {}) or {}
    lineas, total, verdes = [], 0, 0
    nombres = {"combi-cuota_3": "Combi cuota 3", "combi-segura": "Combi de datos", "combi-loca": "Combi loca",
               "picks-manana": "Picks del día", "picks-hoy": "Picks de la tarde"}
    for p in posts_ayer:
        tipo = p["id"][11:]
        if tipo not in nombres:
            continue
        res = [reg.get(k, {}).get("acierto") for k in p.get("sel", [])]
        if not res or any(r is None for r in res):
            return None                      # falta algún resultado: aún no se publica
        a = sum(res)
        total, verdes = total + len(res), verdes + a
        if tipo.startswith("combi"):
            lineas.append(f"{'✅' if a == len(res) else '❌'} {nombres[tipo]}")
        else:
            lineas.append(f"{'✅' if a >= len(res) * 0.7 else '❌'} {nombres[tipo]}: {a}/{len(res)}")
    ayer = (datetime.fromisoformat(dia) - timedelta(days=1)).strftime("%Y-%m-%d")
    esc = leer(DATOS / "escalera.json") or {}
    h = next((x for x in reversed(esc.get("historial", [])) if x.get("dia") == ayer), None)
    if h and h.get("resultado"):
        lineas.append(f"{'✅' if h['resultado'] == 'verde' else '❌'} Escalera día {h['escalon']}")
    if not lineas:
        return None
    texto = "📋 ASÍ FUE AYER\n\n" + "\n".join(lineas)
    if total:
        texto += f"\n\n🎯 {verdes}/{total} selecciones acertadas"
    texto += "\n\nHoy seguimos 💪🍀"
    return {"id": f"{dia}-balance", "fecha": f"{dia}T10:30", "texto": texto, "foto": None,
            "origen": "analista", "directo": True, "sel": []}


def main():
    picks = leer(DATOS / "picks.json")
    if not picks:
        print("Sin datos/picks.json")
        return
    enviados = leer(RAIZ / "publicaciones" / "enviados.json", {}) or {}
    estados_redes = leer(RAIZ / "publicaciones" / "enviados_redes.json", {}) or {}
    publicados = {pid for pid, estado in enviados.items() if estado.get("enviado")}
    publicados.update(pid for pid, estado in estados_redes.items()
                      if any((estado.get("redes") or {}).values()))
    anteriores = {p["id"]: p for p in (leer(AUTO, []) or [])}
    ahora = datetime.now(MADRID).strftime("%Y-%m-%dT%H:%M")

    nuevos = {}
    for dia, d in picks["dias"].items():
        if dia < ESCALERA_DESDE:
            continue
        todos = posts_del_dia(dia, d)
        if dia < AUTO_DESDE:                 # hasta el lunes solo la escalera (lo demás está en Metricool)
            todos = [p for p in todos if p["id"].endswith("-escalera")]
        else:
            ayer = (datetime.fromisoformat(dia) - timedelta(days=1)).strftime("%Y-%m-%d")
            b = balance(dia, [p for p in anteriores.values() if p["id"].startswith(ayer)])
            if b:
                todos.append(b)
        for p in todos:
            if p["id"] in publicados:        # publicado en cualquier destino: conservar texto y selecciones
                continue
            if p["fecha"] <= ahora:          # su hora ya pasó sin publicarse
                continue
            nuevos[p["id"]] = p
    # conservar los ya publicados para que quede registro
    for pid, p in anteriores.items():
        if pid in publicados:
            nuevos.setdefault(pid, p)

    lista_final = sorted(nuevos.values(), key=lambda p: p["fecha"])
    AUTO.parent.mkdir(exist_ok=True)
    AUTO.write_text(json.dumps(lista_final, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Posts automáticos en cola: {sum(1 for p in lista_final if p['id'] not in publicados)}")


if __name__ == "__main__":
    main()
