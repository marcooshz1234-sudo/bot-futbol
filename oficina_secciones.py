"""11/11 (Marcos: «la oficina, dale más cariño: más menús, más información y todo bien dividido por lo que abarca
cada bot»). Las pestañas de la ficha de cada rol y el resumen general de la Oficina (docs/panel/oficina.json).

Cada rol tiene «secciones» (pestañas) y cada sección «bloques» que el panel pinta igual para todos:
  kpis   {"items": [{"t", "v", "s", "c"}]}          c = ok | ko | warn | (nada)
  tabla  {"t", "cols": [...], "filas": [[...]], "nota"}
  lista  {"t", "items": [{"h", "t", "s", "c"}]}
  barras {"t", "items": [{"t", "v", "s"}], "signo": True si hay negativos}
  texto  {"t", "txt"}
Todo sale de los archivos que ya escribe el bot: nada se inventa. Si un dato no está, el bloque no sale.
"""
import re
from datetime import datetime, timedelta, timezone

from bot import DATOS, MADRID, RAIZ, leer


def corto(t, n=90):
    t = " ".join(str(t or "").split())
    return t if len(t) <= n else t[:n - 1] + "…"


def pct(a, b):
    return f"{100 * a / b:.0f}%" if b else "—"


def num(x, d=2):
    return f"{x:.{d}f}".replace(".", ",")


def signo(x, d=1):
    return ("+" if x > 0 else "") + num(x, d)


def linea(texto, empieza):
    return next((x.strip() for x in str(texto or "").splitlines() if x.strip().startswith(empieza)), "")


def primera(texto):
    l = [x.strip() for x in str(texto or "").splitlines() if x.strip()]
    return l[0] if l else ""


def kpis(*items):
    return {"tipo": "kpis", "items": [dict(zip(("t", "v", "s", "c"), i)) for i in items if i]}


def tabla(t, cols, filas, nota=None):
    return {"tipo": "tabla", "t": t, "cols": cols, "filas": filas, **({"nota": nota} if nota else {})} if filas else None


def lista(t, items, vacio=None):
    if not items and vacio:
        return {"tipo": "texto", "t": t, "txt": vacio}
    return {"tipo": "lista", "t": t, "items": items} if items else None


def barras(t, items, nota=None):
    return {"tipo": "barras", "t": t, "items": items, "signo": any(x["v"] < 0 for x in items),
            **({"nota": nota} if nota else {})} if items else None


def texto(t, txt):
    return {"tipo": "texto", "t": t, "txt": txt}


def sec(id_, t, *bloques):
    return {"id": id_, "t": t, "bloques": [b for b in bloques if b]}


def tipo_post(pid):
    k = pid[11:] if re.match(r"\d{4}-\d\d-\d\d-", pid) else pid
    for a, b in (("pick-seguro", "Pick del día"), ("cuotaza", "Cuotaza"), ("escalera", "Escalera"), ("combi-tres", "Combi x3"),
                 ("combi-loca", "La loca"), ("combi-partido", "Combi de partido"), ("estrella", "Partido estrella"),
                 ("combi-multi", "Multi"), ("ganadores", "Partidos de hoy"), ("verde", "Verde"), ("rojo", "Rojo"),
                 ("lista-europa", "Lista Europa"), ("logo", "Aviso"), ("pick", "Pick")):
        if a in k:
            return b
    return "Post"


def etiqueta(texto_post):
    if "Esta va con cabeza" in texto_post:
        return "🧠 Cabeza"
    if "Esta es por diversión" in texto_post:
        return "🎉 Diversión"
    return ""


# --------------------------------------------------------------------- roles

def ojeador(ctx):
    hoy, ahora = ctx["hoy"], ctx["ahora"]
    raw = leer(DATOS / "tipsters_raw.json", {}) or {}
    picks = leer(DATOS / "tipsters.json", []) or []
    ap = leer(DATOS / "tipsters_aprendizaje.json", {}) or {}
    posts_hoy = sum(1 for l in raw.values() for p in l if (p.get("fecha") or "")[:10] == hoy)
    fotos_hoy = sum(1 for l in raw.values() for p in l if (p.get("fecha") or "")[:10] == hoy and p.get("foto"))
    picks_hoy = [x for x in picks if x.get("dia") == hoy]
    resueltos = [x for x in picks if x.get("estado")]
    verdes = sum(1 for x in resueltos if x["estado"] in ("verde", "medio_verde"))
    por_canal = {}
    for x in picks:
        por_canal[x["tipster"]] = por_canal.get(x["tipster"], 0) + 1
    canales = []
    for canal, l in sorted(raw.items(), key=lambda kv: -len([p for p in kv[1] if (p.get("fecha") or "")[:10] == hoy])):
        ult = max((p.get("fecha") or "" for p in l), default="")
        canales.append([canal, str(len([p for p in l if (p.get("fecha") or "")[:10] == hoy])),
                        f"{ult[8:10]}/{ult[5:7]} {ult[11:16]}" if ult else "—", str(por_canal.get(canal, 0)),
                        "⏸️ apagado" if canal in ctx["off"] else "✅ leyendo"])
    tip = []
    for t, c in (ap.get("tipster") or {}).items():
        res = c["verdes"] + c["rojos"]
        esp = c.get("prob_cuota")
        tip.append([t, str(c["n"]), f"{c['verdes']}✅ {c['rojos']}❌", pct(c["verdes"], res),
                    pct(esp, c.get("resueltos_con_cuota") or 0) if esp else "—", signo(c.get("unidades", 0), 2) + " u"])
    ult_picks = [{"h": f"{x['dia'][8:10]}/{x['dia'][5:7]}", "t": f"{x['tipster']} · {x.get('local')} – {x.get('visitante')}: {x.get('texto')}"
                  + (f" @{num(x['cuota'])}" if x.get("cuota") else ""),
                  "s": corto("; ".join(x.get("por_que") or x.get("argumento") or []), 140),
                  "c": {"verde": "ok", "medio_verde": "ok", "rojo": "ko", "medio_rojo": "ko"}.get(x.get("estado"), "")}
                 for x in sorted(picks, key=lambda x: x.get("dia", ""), reverse=True)[:12]]

    def bar(dim, n=8):
        out = []
        for k, c in list((ap.get(dim) or {}).items())[:n]:
            res = c["verdes"] + c["rojos"]
            if res:
                out.append({"t": k, "v": round(100 * c["verdes"] / res), "s": f"{c['verdes']}/{res} · {signo(c.get('unidades', 0), 2)} u"})
        return out
    return [
        sec("resumen", "Resumen",
            kpis(("Canales", str(len(raw)), f"{len(raw) - len(ctx['off'])} leyendo", ""),
                 ("Posts hoy", str(posts_hoy), f"{fotos_hoy} con foto", ""),
                 ("Picks apuntados hoy", str(len(picks_hoy)), "con su porqué", "ok" if picks_hoy else "warn"),
                 ("Resueltos", str(len(resueltos)), f"{verdes} verdes · {pct(verdes, len(resueltos))}", ""),
                 ("Para fiarse", f"{len(resueltos)}/30", "picks resueltos por canal", "warn" if len(resueltos) < 30 else "ok")),
            lista("Lo último de los canales", ctx["base"]["ojeador"]["historial"][:6], "Hoy aún no han subido nada.")),
        sec("canales", "Canales", tabla("Canales que lee", ["Canal", "Hoy", "Último post", "Picks apuntados", "Estado"], canales,
                                        "Encender/apagar cada canal: abajo, en Ajustes.")),
        sec("tipsters", "Tipsters",
            tabla("Cómo van", ["Tipster", "Picks", "Resultado", "Acierto", "Según la cuota", "Unidades"], tip,
                  "«Según la cuota» = lo que deberían acertar por la cuota. Si aciertan más, son buenos de verdad."),
            lista("Sus últimos picks y por qué", ult_picks, "Aún no hay picks apuntados.")),
        sec("aprende", "Qué aprende",
            barras("Acierto por mercado (%)", bar("mercado")), barras("Acierto por lado (%)", bar("lado")),
            barras("Acierto por tipo de razón (%)", bar("razon")), barras("Con o sin valor según Pinnacle (%)", bar("valor_pinnacle")),
            texto("Cómo lo usa el bot", "Si una pata del bot coincide con la de un tipster ese día, sube un poco su probabilidad "
                  "(+2 puntos; +5 si ese tipster ha demostrado ganar con 20+ picks; 0 si ha demostrado perder).")),
    ]


def analista(ctx):
    hoy, man = ctx["hoy"], ctx["manana"]
    todos, cancel = ctx["todos"], ctx["cancel"]
    import plantillas
    v, r, gan = plantillas.balance_seguro()
    m = leer(DATOS / "modelo_patas.json", {}) or {}
    ev = (m.get("evaluacion") or {}).get("nuevo") or {}
    agenda = []
    for p in sorted((p for p in todos.values() if p["fecha"][:10] in (hoy, man) and p["id"] not in cancel
                     and any(k in p["id"] for k in ("pick", "escalera", "combi", "estrella", "cuotaza"))), key=lambda p: p["fecha"]):
        cu = re.search(r"@(\d+,\d+)", linea(p["texto"], "🍀") or linea(p["texto"], "📈") or "")
        agenda.append(["Hoy" if p["fecha"][:10] == hoy else "Mañana", p["fecha"][11:16], tipo_post(p["id"]), etiqueta(p["texto"]),
                       corto(linea(p["texto"], "🍀").replace("🍀", "").strip() or primera(p["texto"]), 60), cu.group(1) if cu else "—",
                       "✅ salió" if p["id"] in ctx["env"] else "⏳"])
    pesos = sorted((m.get("pesos") or {}).items(), key=lambda kv: kv[1])
    nombres = {"cuota": "lo que dice la cuota", "ventaja_racha": "nuestra racha frente a la cuota", "baja_1_35": "cuota ≤1,35",
               "liga_grande": "liga grande", "senal=b365_menos": "bet365 paga menos que otras", "senal=b365_mas": "bet365 paga más que otras",
               "senal=sin_otras": "solo hay cuota de bet365", "senal=igual": "bet365 igual que otras", "lado=local": "pata del local",
               "lado=visitante": "pata del visitante", "lado=partido": "pata del partido", "lado=jugador": "pata de jugador"}
    nom = lambda k: nombres.get(k, k.replace("fam=", "mercado: ").replace("jugador:", "jugador ").replace("a_puerta", "a puerta")
                                .replace("faltas_c", "faltas") .replace("comp=", "competición: "))
    rent = [[x["tipo"], str(x["jugadas"]), f"{x['verdes']} ({x['pct']}%)", num(x["cuota_media"]), f"{x['roi']:+d}%"]
            for x in ctx["datos"].get("rentabilidad") or []]
    sharp = leer(DATOS / "cuotas_sharp.json", {}) or {}
    return [
        sec("resumen", "Resumen",
            kpis(("Pick del día", f"{v}✅ {r}❌", f"{signo(100 * gan / (10 * (v + r)) if v + r else 0, 0)}% de rentabilidad", "ok" if gan >= 0 else "ko"),
                 ("Posts hoy", str(len([a for a in agenda if a[0] == "Hoy"])), "picks, escalera y combis", ""),
                 ("Modelo: promete", pct(ev.get("prometido", 0), 1), f"salen {pct(ev.get('real', 0), 1)}", "ok" if abs(ev.get("prometido", 0) - ev.get("real", 0)) < 0.03 else "warn"),
                 ("Pinnacle hoy", str(len(sharp.get("partidos") or {})), f"partidos ({sharp.get('dia', '—')})", ""))),
        sec("agenda", "Hoy y mañana", tabla("Lo que ha elegido", ["Día", "Hora", "Tipo", "Etiqueta", "Pick", "Cuota", "Estado"], agenda,
                                            "Solo picks, escalera, combis y cuotazas. Lo demás, en la sala del Redactor.")),
        sec("modelo", "Cómo elige",
            kpis(("Patas aprendidas", str(m.get("patas", "—")), f"actualizado {str(m.get('generado', ''))[5:16]}", ""),
                 ("Precisión", num(ev.get("logloss", 0), 3) if ev else "—", "log-loss (más bajo = mejor)", ""),
                 ("Contexto", "sí" if m.get("con_contexto") else "aún no",
                  f"sin {num(m.get('sin_contexto_logloss', 0), 3)} · con {num(m.get('con_contexto_logloss', 0), 3)}", "" if m.get("con_contexto") else "warn")),
            barras("Lo que le SUMA probabilidad", [{"t": nom(k), "v": round(w, 2), "s": ""} for k, w in pesos[::-1] if w > 0.05][:8]),
            barras("Lo que le RESTA probabilidad", [{"t": nom(k), "v": round(w, 2), "s": ""} for k, w in pesos if w < -0.05][:8]),
            texto("Cómo funciona", "Aprende de todas las patas ya jugadas: cuota, racha, tipo de mercado, lado, si bet365 paga más o menos que "
                  "otras casas y la liga. Pinnacle manda en lo justo (60%) junto a lo nuestro (40%) y fuera solo si bet365 paga un 10% menos. "
                  "Descanso, forma, árbitro, tiempo y estadio entran solos cuando de verdad mejoren la predicción.")),
        sec("rent", "Rentabilidad", tabla("Desde el " + str(ctx["datos"].get("stats_desde") or "")[:10], ["Tipo", "Jugadas", "Verdes", "Cuota media", "ROI"], rent,
                                          "Una unidad por apuesta. ROI = lo ganado o perdido por cada 100 jugados.")),
    ]


def redactor(ctx):
    hoy, ahora = ctx["hoy"], ctx["ahora"]
    todos, cancel, env = ctx["todos"], ctx["cancel"], ctx["env"]
    textos = ctx["control"].get("textos") or {}
    ya = ahora.strftime("%Y-%m-%dT%H:%M")
    prox = sorted((p for p in todos.values() if p["fecha"] >= ya and p["id"] not in env and p["id"] not in cancel
                   and p["fecha"] <= (ahora + timedelta(hours=30)).strftime("%Y-%m-%dT%H:%M")), key=lambda p: p["fecha"])
    def redes(p):
        solo = p.get("solo_en")
        r = [] if p.get("solo_redes") else ["📨 Telegram"]
        if not solo or "threads" in solo:
            r.append("🧵 Threads")
        if not p.get("sin_instagram") and (not solo or "instagram" in solo):
            r.append("📸 IG")
        return " ".join(r)
    agenda = [[("Hoy " if p["fecha"][:10] == hoy else "Mañ. ") + p["fecha"][11:16], tipo_post(p["id"]), etiqueta(textos.get(p["id"], p["texto"])),
               corto(primera(textos.get(p["id"], p["texto"])), 55), redes(p).strip(), "✋ tu OK" if p.get("requiere_ok") else ""] for p in prox[:20]]
    hechos = sorted(((e, pid) for pid, e in env.items() if e[:10] == hoy), reverse=True)
    cab = sum(1 for p in todos.values() if p["fecha"][:10] == hoy and "Esta va con cabeza" in p["texto"])
    div = sum(1 for p in todos.values() if p["fecha"][:10] == hoy and "Esta es por diversión" in p["texto"])
    return [
        sec("resumen", "Resumen",
            kpis(("Publicados hoy", str(len(hechos)), "en Telegram y redes", "ok" if hechos else ""),
                 ("Quedan hoy", str(len([p for p in prox if p["fecha"][:10] == hoy])), "programados", ""),
                 ("Próximas 30 h", str(len(prox)), "en cola", ""),
                 ("Cabeza / diversión", f"{cab} / {div}", "posts de hoy", ""))),
        sec("agenda", "Agenda", tabla("Lo que viene", ["Cuándo", "Tipo", "Etiqueta", "Primera línea", "Dónde", ""], agenda)),
        sec("hecho", "Publicado hoy", lista("Ya salió", [{"h": e[11:16], "t": f"{tipo_post(pid)} · " + corto(primera(todos[pid]["texto"]) if pid in todos else pid, 80)}
                                                          for e, pid in hechos[:15]], "Hoy aún no ha salido nada.")),
        sec("estilo", "Estilo", texto("Reglas del canal",
                                      "• Pick: saludo, 🍀 pick @cuota, 🧠 Stake n/10, razones con 👨‍💻.\n"
                                      "• Segunda línea: «🧠 Esta va con cabeza» o «🎉 Esta es por diversión».\n"
                                      "• Nombres completos y «(fem.)» en femenino. Nada de dinero en Instagram (salvo la escalera).\n"
                                      "• Cierre: «🔔 Activad las notificaciones, que vienen más combis 👀».\n"
                                      "• Telegram: pick del día, escalera y una combi; lo demás, solo redes.")),
    ]


def verificador(ctx):
    hoy, ahora = ctx["hoy"], ctx["ahora"]
    d = ctx["datos"]
    res = [x for x in d.get("publicados_hoy") or [] if x.get("estado") in ("verde", "rojo")]
    hoy_r = [x for x in res if (x.get("fecha") or "")[:10] == hoy]
    vivo = {k: v for k, v in (leer(DATOS / "en_directo.json", {}) or {}).items() if v.get("estado") not in ("FT", "AET", "PEN", "NS", "PST", "CANC")}
    import plantillas
    v, r, gan = plantillas.balance_seguro()
    directo = [[f"{x.get('local', '')} – {x.get('visitante', '')}", f"{x.get('marcador') or x.get('goles') or ''}", str(x.get("minuto") or x.get("estado") or "")]
               for x in vivo.values()][:10]
    return [
        sec("resumen", "Resumen",
            kpis(("Verdes hoy", str(sum(1 for x in hoy_r if x["estado"] == "verde")), "", "ok"),
                 ("Rojos hoy", str(sum(1 for x in hoy_r if x["estado"] == "rojo")), "", "ko" if any(x["estado"] == "rojo" for x in hoy_r) else ""),
                 ("En directo", str(len(vivo)), "partidos con algo nuestro", ""),
                 ("Esperando tu OK", str(len(ctx["base"]["verificador"].get("pendientes") or [])), "verdes, rojos y cuotazas", "warn" if ctx["base"]["verificador"].get("pendientes") else ""))),
        sec("resultados", "Resultados", lista("Últimos resultados", [
            {"h": (x.get("fecha") or "")[11:16] if (x.get("fecha") or "")[:10] == hoy else "ayer",
             "t": corto(x.get("titulo"), 90), "c": "ok" if x["estado"] == "verde" else "ko"} for x in sorted(res, key=lambda x: x.get("fecha") or "", reverse=True)[:15]],
            "Sin resultados en las últimas 48 h.")),
        sec("directo", "En directo", tabla("Partidos en juego", ["Partido", "Marcador", "Minuto"], directo) or texto("En juego", "Ahora no hay partidos nuestros en juego.")),
        sec("balance", "Balance", kpis(("Pick del día", f"{v}✅ {r}❌", f"{signo(gan / 10, 2)} stakes de 10", "ok" if gan >= 0 else "ko")),
            tabla("Por tipo", ["Tipo", "Jugadas", "Verdes", "ROI"], [[x["tipo"], str(x["jugadas"]), f"{x['verdes']} ({x['pct']}%)", f"{x['roi']:+d}%"]
                                                                   for x in d.get("rentabilidad") or []])),
    ]


def community(ctx):
    base = ctx["base"]["community"]
    com = [c for c in (leer(DATOS / "comentarios_threads.json", []) or []) if not c.get("hecho")
           and (c.get("fecha") or "9") >= (ctx["ahora"] - timedelta(hours=48)).strftime("%Y-%m-%dT%H:%M")]
    prop = leer(DATOS / "comentarios_claude.json", {}) or {}
    resp = [r for r in (leer(RAIZ / "publicaciones" / "respuestas_threads.json", []) or []) if r.get("hecho")]
    top = (ctx["datos"].get("rendimiento") or {}).get("top") or []
    return [
        sec("resumen", "Resumen",
            kpis(("Por contestar", str(len(com)), "últimas 48 h", "warn" if com else "ok"),
                 ("Con respuesta propuesta", str(len([c for c in com if c["id"] in prop])), "esperan tu OK", ""),
                 ("Respondidos", str(len(resp)), "en total", ""))),
        sec("comentarios", "Comentarios", lista("Sin contestar", [
            {"h": (c.get("fecha") or "")[11:16], "t": f"@{c.get('usuario')}: «{corto(c.get('texto'), 100)}»",
             "s": ("💬 Propuesta: " + corto((prop.get(c["id"]) or {}).get("t"), 100)) if c["id"] in prop else ""} for c in com[-12:][::-1]],
            "Todo contestado.")),
        sec("vistas", "Lo más visto", tabla("Threads esta semana", ["#", "Post", "Vistas"],
                                            [[str(i + 1), corto(p.get("titulo"), 60), f"{p.get('vistas', 0):,}".replace(",", ".")] for i, p in enumerate(top[:8])])
            or texto("Lo más visto", "Sin datos de vistas aún.")),
        sec("estilo", "Cómo contesta", texto("Normas", "Cortas, como un chaval, sin tildes, hablando a esa persona (tío, crack; nunca «familia») "
                                                       "y con lo que pasó de verdad. Nunca se publican solas: las apruebas tú.")),
    ]


def vigilante(ctx):
    from oficina_datos import bucle
    ahora, hoy = ctx["ahora"], ctx["hoy"]
    reg = bucle(ahora)
    hoy_reg = [x for x in reg if x[0].strftime("%Y-%m-%d") == hoy]
    fallos = [(t, n, c) for t, n, c in hoy_reg if c not in ("0", "-")]
    por = {}
    for t, n, c in fallos:
        por.setdefault(n, []).append(t)
    api = leer(DATOS / "consumo_api.json", {}) or {}
    ult = api.get(max(api)) if api else {}
    frescos = []
    for nombre, ruta in (("Cuotas de partidos", None), ("Tipsters (canales)", DATOS / "tipsters_raw.json"), ("Pinnacle", DATOS / "cuotas_sharp.json"),
                         ("Modelo de patas", DATOS / "modelo_patas.json"), ("Aprendizaje", DATOS / "aprendizaje.json"),
                         ("Cazador", DATOS / "cazador.json"), ("Panel", RAIZ / "docs" / "datos.json")):
        try:
            if ruta is None:
                hs = []
                for f in (DATOS / "proximos").glob("*.json"):
                    h = (leer(f, {}) or {}).get("cuotas_hora")
                    if h:
                        hs.append(datetime.fromisoformat(h).astimezone(MADRID))
                t = max(hs) if hs else None
            else:
                t = datetime.fromtimestamp(ruta.stat().st_mtime, timezone.utc).astimezone(MADRID) if ruta.exists() else None
        except Exception:
            t = None
        if t:
            mins = int((ahora - t).total_seconds() // 60)
            frescos.append([nombre, t.strftime("%d/%m %H:%M"), f"hace {mins // 60} h {mins % 60} min" if mins >= 60 else f"hace {mins} min"])
    pasos = {}
    for t, n, c in hoy_reg:
        pasos[n] = pasos.get(n, 0) + 1
    return [
        sec("resumen", "Resumen",
            kpis(("Bucle", ctx["base"]["vigilante"]["ahora"].split("·")[0].strip(), "telegram.yml", "ko" if ctx["base"]["vigilante"].get("alerta") else "ok"),
                 ("Fallos hoy", str(len(fallos)), f"en {len(por)} script(s)", "ko" if len(fallos) >= 3 else "warn" if fallos else "ok"),
                 ("API-Football", f"{ult.get('usadas', '—')}", f"usadas · quedan {ult.get('restantes', '—')}", ""),
                 ("Vueltas hoy", str(pasos.get("git_pull", 0)), "del bucle", ""))),
        sec("fallos", "Fallos", tabla("Qué ha fallado hoy", ["Script", "Veces", "Última"], [[n, str(len(l)), max(l).strftime("%H:%M")] for n, l in
                                                                                          sorted(por.items(), key=lambda kv: -len(kv[1]))])
            or texto("Fallos", "Ningún fallo en el bucle hoy ✅")),
        sec("frescos", "Datos al día", tabla("Cuándo se actualizó cada cosa", ["Qué", "Última vez", ""], frescos,
                                             "Si algo lleva muchas horas sin actualizarse, el Vigilante lo mira en su turno.")),
        sec("pasos", "El bucle", barras("Pasos de hoy (veces)", [{"t": n, "v": c, "s": ""} for n, c in sorted(pasos.items(), key=lambda kv: -kv[1])[:14]])),
    ]


def cazador(ctx):
    import ajustes as AJ
    cz = leer(DATOS / "cazador.json", {}) or {}
    ult = cz.get("ultima") or {}
    avisos = [dict(v, k=k) for k, v in (cz.get("avisos") or {}).items()]
    aprob, cancel, env = ctx["control"].get("aprobados") or {}, ctx["cancel"], ctx["env"]
    estado = lambda pid: "✅ publicada" if pid in env else "👍 aprobada" if pid in aprob else "❌ descartada" if pid in cancel else "⏳ esperando tu OK"
    hoy_av = [a for a in avisos if a.get("dia") == ctx["hoy"]]
    top = [[f"{x['local']} – {x['visitante']}", f"{x['inicio'][11:16]}", corto(x["texto"], 40), num(x["cuota"]), num(x["justa"]),
            f"{x['ev']:+.0%}", x["fuente"], f"{x['edad_h']:.0f} h"] for x in cz.get("top") or []]
    return [
        sec("resumen", "Resumen",
            kpis(("Última vuelta", (ult.get("hora") or "—")[11:16], "cada 20 min", "ok" if ult else "warn"),
                 ("Avisa desde", f"+{AJ.valor('cazador_umbral', ctx['control'])}%", "por encima de lo justo", ""),
                 ("Cuota mínima", num(float(AJ.valor("cazador_cuota_min", ctx["control"]))), "hasta 5,00", ""),
                 ("Cuotazas hoy", f"{len(hoy_av)}/4", "como mucho 4 al día", "warn" if any(estado(a.get('post')) == '⏳ esperando tu OK' for a in hoy_av) else ""))),
        sec("ahora", "Mejores ahora", tabla("Las mejores cuotas de bet365 frente a lo justo", ["Partido", "Hora", "Pick", "bet365", "Justa", "Valor", "Según", "Cuotas de"],
                                            top, "Aunque no lleguen al aviso. «Valor» = cuánto paga bet365 por encima de lo justo.")
            or texto("Mejores ahora", "En la última vuelta no había nada por encima de lo justo (o las cuotas son viejas).")),
        sec("avisos", "Avisos", lista("Cuotazas avisadas", [{"h": a.get("dia", "")[8:10] + "/" + a.get("dia", "")[5:7], "t": f"{a['k'].split('|', 1)[1]} @{num(a['cuota'])} ({a.get('ev', 0):+.0%})",
                                                             "s": estado(a.get("post")), "c": "ok" if "publicada" in estado(a.get("post")) else ""}
                                                            for a in sorted(avisos, key=lambda a: a.get("dia", ""), reverse=True)[:12]],
                                      "Aún no ha encontrado ninguna cuotaza.")),
        sec("como", "Cómo calcula", texto("Lo justo", "1) Cada 20 min refresca las cuotas de los partidos de las próximas 12 h (bet365, Pinnacle y el resto de casas).\n"
                                                      "2) Lo justo: la cuota de Pinnacle sin su margen; si no hay, la media de las otras casas sin su margen.\n"
                                                      "3) Si bet365 paga por encima del umbral, te llega al móvil con ✅ Publicar / ❌ No sale.\n"
                                                      "4) Sin mercados prohibidos, entre la cuota mínima y 5,00, como mucho 4 al día y nunca repite (salvo que suba más).")),
    ]


COMO = {
    "ojeador": "Lee los canales de los tipsters (cada 30 min el bot; mañana y tarde Claude apunta sus picks con su porqué) y aprende quién acierta y en qué.",
    "analista": "Elige el pick del día, la escalera y las combis con el modelo de patas, Pinnacle y lo que aprende de los tipsters.",
    "redactor": "Escribe los posts con el estilo del canal, con su etiqueta (cabeza o diversión) y los saca a su hora.",
    "verificador": "Sigue los partidos en directo, marca verdes y rojos y te los manda para que des el OK.",
    "community": "Lee los comentarios de Threads y propone respuestas que tú apruebas en el panel.",
    "vigilante": "Vigila que el bucle del bot funcione, que los datos estén al día y te avisa si algo falla.",
    "cazador": "Busca cuotas de bet365 por encima de lo justo y te avisa al momento para subirlas.",
}


def todo(ctx):
    """{rol: [secciones]} (si un rol falla, ese rol sale sin pestañas extra; no rompe la Oficina)."""
    out = {}
    for rid, f in (("ojeador", ojeador), ("analista", analista), ("redactor", redactor), ("verificador", verificador),
                   ("community", community), ("vigilante", vigilante), ("cazador", cazador)):
        try:
            out[rid] = f(ctx)
        except Exception as e:
            print(f"oficina ({rid}):", str(e)[:200])
            out[rid] = []
    return out


def general(ctx, roles):
    """Cabecera de la Oficina: números del día, lo que necesita tu decisión y la actividad de todos."""
    hoy = ctx["hoy"]
    pend = ctx["base"]["verificador"].get("pendientes") or []
    para_ti = [{"rol": "verificador", "t": "Esperando tu OK: " + p["texto"]} for p in pend[:5]]
    com = ctx["base"]["community"].get("propuestas") or 0
    if com:
        para_ti.append({"rol": "community", "t": f"{com} respuesta(s) de Threads para aprobar"})
    if ctx["base"]["vigilante"].get("alerta"):
        para_ti.append({"rol": "vigilante", "t": ctx["base"]["vigilante"]["ahora"]})
    faltan = [n for n, k in (("10:30", "-pick-seguro"), ("18:00", "-pick-seguro-2"))
              if not any(pid.startswith(hoy) and pid.endswith(k) and pid not in ctx["cancel"] for pid in ctx["todos"])]
    if faltan:
        para_ti.append({"rol": "analista", "t": "Hoy falta el pick de las " + " y el de las ".join(faltan)})
    d = ctx["datos"]
    res = [x for x in d.get("publicados_hoy") or [] if x.get("estado") in ("verde", "rojo") and (x.get("fecha") or "")[:10] == hoy]
    publicados = len([1 for e in ctx["env"].values() if e[:10] == hoy])
    act = []
    for r in roles:
        for h in r.get("historial") or []:
            if h.get("h") and h["h"][:1].isdigit():
                act.append({"h": h["h"], "rol": r["id"], "t": h["t"]})
    act.sort(key=lambda x: x["h"], reverse=True)
    trabajando = sum(1 for r in roles if r["estado"] == "trabajando")
    return {
        "kpis": [{"t": "Publicados hoy", "v": str(publicados), "c": "ok" if publicados else ""},
                 {"t": "Verdes / rojos", "v": f"{sum(1 for x in res if x['estado'] == 'verde')} / {sum(1 for x in res if x['estado'] == 'rojo')}", "c": ""},
                 {"t": "Para ti", "v": str(len(para_ti)), "c": "warn" if para_ti else "ok"},
                 {"t": "Trabajando ahora", "v": f"{trabajando}/{len(roles)}", "c": ""}],
        "para_ti": para_ti, "actividad": act[:30],
    }
