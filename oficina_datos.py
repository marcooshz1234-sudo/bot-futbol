"""
10/11 (Marcos): datos de la OFICINA COMBILOCAS (pestaña 🏢 del panel). Cada rol es un muñeco en su sala con lo que
está haciendo ahora, lo que ha hecho hoy y sus ajustes (ajustes.py). Todo sale de los archivos que ya escribe el bot:
nada se inventa. Lo llama panel_datos.py en cada vuelta → docs/panel/oficina.json.
"""
import json
from datetime import datetime, timedelta, timezone

from ajustes import AJUSTES_ROLES, ROLES, canales_off, pausado, valor
from bot import DATOS, MADRID, RAIZ, leer

SALIDA = RAIZ / "docs" / "panel" / "oficina.json"
RITMO = {"ojeador": "cada 30 min", "analista": "picks a las {h1} y {h2}", "redactor": "antes de cada post",
         "verificador": "cada 3 min en directo", "community": "2 veces al día", "vigilante": "siempre", "cazador": "cada 10 min"}


def corto(t, n=90):
    t = " ".join(str(t or "").split())
    return t if len(t) <= n else t[:n - 1] + "…"


def primera(texto):
    l = [x.strip() for x in str(texto or "").splitlines() if x.strip()]
    if l and "COMBI LOCAS" in l[0].upper() and len(l) > 1:
        return l[1]
    return l[0] if l else ""


def linea(texto, empieza):
    return next((x.strip() for x in str(texto or "").splitlines() if x.strip().startswith(empieza)), "")


def bucle(ahora):
    """[(hora Madrid, script, código)] de hoy, del registro del bucle (va en UTC)."""
    out = []
    try:
        filas = (DATOS / "bucle_log.txt").read_text(encoding="utf-8").splitlines()
    except Exception:
        return out
    hoy_utc = ahora.astimezone(timezone.utc).date()
    for f in filas:
        x = f.split()
        if len(x) < 3 or len(x[0]) != 8:
            continue
        try:
            t = datetime.combine(hoy_utc, datetime.strptime(x[0], "%H:%M:%S").time(), tzinfo=timezone.utc)
        except ValueError:
            continue
        if t > ahora.astimezone(timezone.utc) + timedelta(minutes=5):
            t -= timedelta(days=1)
        out.append((t.astimezone(MADRID), x[1], x[2]))
    return out


def posts():
    todos = {}
    for f in ("auto.json", "cola.json"):
        for p in leer(RAIZ / "publicaciones" / f, []) or []:
            todos[p["id"]] = p   # la cola manda sobre lo del bot
    return todos


def main(control=None):
    ahora = datetime.now(MADRID)
    hoy = ahora.strftime("%Y-%m-%d")
    control = control if control is not None else (leer(RAIZ / "publicaciones" / "control.json", {}) or {})
    enviados = leer(RAIZ / "publicaciones" / "enviados.json", {}) or {}
    todos = posts()
    cancel = set(control.get("cancelados") or [])
    roles = {}

    # 🔎 Ojeador: lo último que han subido los canales de tipsters
    raw = leer(DATOS / "tipsters_raw.json", {}) or {}
    off = canales_off(control)
    vistos = sorted(((p.get("fecha") or "", canal, p) for canal, l in raw.items() for p in l
                     if (p.get("fecha") or "")[:10] == hoy and (p.get("texto") or "").strip()), key=lambda v: (v[0], v[1]), reverse=True)
    nuevos30 = [v for v in vistos if (v[2].get("visto") or "") >= (ahora - timedelta(minutes=30)).strftime("%Y-%m-%dT%H:%M")]
    picks_t = [x for x in (leer(DATOS / "tipsters.json", []) or []) if x.get("dia") == hoy]
    roles["ojeador"] = {
        "ahora": (f"Leyendo {nuevos30[0][1]}: «{corto(primera(nuevos30[0][2]['texto']), 60)}»" if nuevos30 else
                  f"{len(vistos)} posts leídos hoy · {len(picks_t)} picks de tipsters apuntados"),
        "trabajando": bool(nuevos30),
        "historial": [{"h": f[11:16], "t": f"{c}: {corto(primera(p['texto']), 80)}"} for f, c, p in vistos[:6]],
        "canales": [{"n": c, "on": c not in off, "posts": len([p for p in l if (p.get("fecha") or "")[:10] == hoy])}
                    for c, l in sorted(raw.items(), key=lambda x: x[0].lower())],
    }

    # 🧠 Analista: los picks del día y la escalera que ha elegido para hoy
    elegidos = sorted((p for p in todos.values() if p["fecha"][:10] == hoy and p["id"] not in cancel
                       and any(k in p["id"] for k in ("pick-seguro", "escalera", "pick-"))), key=lambda p: p["fecha"])
    prox = next((p for p in elegidos if p["fecha"] > ahora.strftime("%Y-%m-%dT%H:%M") and p["id"] not in enviados and not p.get("enviado")), None)
    roles["analista"] = {
        "ahora": (f"Preparando el pick de las {prox['fecha'][11:16]}: {corto(linea(prox['texto'], '🍀') or primera(prox['texto']), 60)}"
                  if prox else f"Picks de hoy elegidos ({len(elegidos)}). Mañana sigo"),
        "trabajando": bool(prox and datetime.fromisoformat(prox["fecha"]).replace(tzinfo=MADRID) - ahora < timedelta(hours=1)),
        "historial": [{"h": p["fecha"][11:16], "t": corto(("Pick del día: " if "pick" in p["id"] else "Escalera: ")
                                                         + (linea(p["texto"], "🍀") or linea(p["texto"], "✅") or primera(p["texto"])), 90)}
                      for p in elegidos][-6:],
    }

    # ✍️ Redactor: lo que sale (y lo que ha salido) hoy
    env = {pid: v.get("enviado") for pid, v in enviados.items() if isinstance(v, dict) and v.get("enviado")}
    env.update({pid: p["enviado"] for pid, p in todos.items() if isinstance(p.get("enviado"), str)})   # la cola guarda su estado
    hechos = sorted(((e, pid) for pid, e in env.items() if e[:10] == hoy), reverse=True)
    cola = sorted((p for p in todos.values() if p["fecha"][:10] == hoy and p["id"] not in env and p["id"] not in cancel
                   and p["fecha"] > ahora.strftime("%Y-%m-%dT%H:%M")), key=lambda p: p["fecha"])
    sig = cola[0] if cola else None
    roles["redactor"] = {
        "ahora": (f"Próximo post a las {sig['fecha'][11:16]}: {corto(primera((control.get('textos') or {}).get(sig['id'], sig['texto'])), 55)}"
                  if sig else "Nada más programado para hoy"),
        "trabajando": bool(sig and datetime.fromisoformat(sig["fecha"]).replace(tzinfo=MADRID) - ahora < timedelta(minutes=20)),
        "historial": [{"h": e[11:16], "t": "Publicado: " + corto(primera(todos[pid]["texto"]) if pid in todos else pid, 80)}
                      for e, pid in hechos[:6]],
    }

    # ✅ Verificador: resultados de hoy, partidos en directo y verdes que esperan tu OK
    d = leer(RAIZ / "docs" / "datos.json", {}) or {}
    res = [x for x in d.get("publicados_hoy") or [] if x.get("estado") in ("verde", "rojo") and (x.get("fecha") or "")[:10] >= (ahora - timedelta(days=1)).strftime("%Y-%m-%d")]
    vivo = {k: v for k, v in (leer(DATOS / "en_directo.json", {}) or {}).items() if v.get("estado") not in ("FT", "AET", "PEN", "NS", "PST", "CANC")}
    aprob = control.get("aprobados") or {}
    pend = [pid for pid in (control.get("por_aprobar") or {}).values() if pid not in aprob and pid not in cancel]
    pend = [{"id": pid, "texto": corto(primera(todos[pid]["texto"]) + " · " + (linea(todos[pid]["texto"], "📈") or linea(todos[pid]["texto"], "🍀")), 110)}
            for pid in dict.fromkeys(pend) if pid in todos]
    roles["verificador"] = {
        "ahora": (f"Mirando {len(vivo)} partido{'s' if len(vivo) != 1 else ''} en directo" if vivo else
                  f"{len(pend)} verde(s) esperando tu OK" if pend else "Sin partidos en juego ahora"),
        "trabajando": bool(vivo),
        "historial": [{"h": (x.get("fecha") or "")[11:16] if (x.get("fecha") or "")[:10] == hoy else "ayer", "t": ("✅ Entró: " if x["estado"] == "verde" else "❌ Falló: ") + corto(x.get("titulo"), 70)}
                      for x in sorted(res, key=lambda x: x.get("fecha") or "", reverse=True)[:6]],
        "pendientes": pend,
    }

    # 💬 Community: comentarios por contestar y respuestas propuestas
    com = [c for c in (leer(DATOS / "comentarios_threads.json", []) or []) if not c.get("hecho")
           and (c.get("fecha") or "9") >= (ahora - timedelta(hours=48)).strftime("%Y-%m-%dT%H:%M")]
    prop = leer(DATOS / "comentarios_claude.json", {}) or {}
    resp = [r for r in (leer(RAIZ / "publicaciones" / "respuestas_threads.json", []) or []) if r.get("hecho")]
    hechas = {r.get("comentario") for r in resp}
    com = [c for c in com if c["id"] not in hechas]
    roles["community"] = {
        "ahora": (f"{len(com)} comentario{'s' if len(com) != 1 else ''} por contestar · {len([c for c in com if c['id'] in prop])} con respuesta propuesta"
                  if com else "Todo contestado"),
        "trabajando": bool(com),
        "historial": ([{"h": (c.get("fecha") or "")[11:16], "t": f"@{c.get('usuario')}: «{corto(c.get('texto'), 60)}»"} for c in com[-4:]][::-1]
                      + [{"h": "", "t": "Respondido: " + corto(r.get("texto"), 70)} for r in resp[-2:]]),
        "propuestas": len([c for c in com if c["id"] in prop]),
    }

    # 🛠️ Vigilante: cómo va el bucle
    reg = bucle(ahora)
    ult = reg[-1][0] if reg else None
    fallos = [(t, n, c) for t, n, c in reg if c not in ("0", "-") and t.strftime("%Y-%m-%d") == hoy]
    mins = int((ahora - ult).total_seconds() // 60) if ult else None
    roles["vigilante"] = {
        "ahora": (f"Bucle OK · última vuelta hace {mins} min" if mins is not None and mins <= 15 else
                  f"⚠️ El bucle no da señales desde hace {mins} min" if mins is not None else "Sin registro del bucle"),
        "trabajando": mins is not None and mins <= 15,
        "alerta": mins is None or mins > 15 or len(fallos) >= 3,
        "historial": ([{"h": t.strftime("%H:%M"), "t": f"Fallo en {n} (código {c})"} for t, n, c in fallos[-5:]][::-1]
                      or [{"h": ult.strftime("%H:%M") if ult else "", "t": "Sin fallos hoy en el bucle"}]),
    }

    # 🎯 Cazador (11/11): cuotas de bet365 por encima de lo justo
    cz = leer(DATOS / "cazador.json", {}) or {}
    ult = cz.get("ultima") or {}
    mejor = ult.get("mejor")
    avisos_hoy = [v for v in (cz.get("avisos") or {}).values() if v.get("dia") == hoy]
    roles["cazador"] = {
        "ahora": (f"Última vuelta {ult.get('hora', '')[11:16]}: " + (f"mejor {corto(mejor['texto'], 40)} @{mejor['cuota']} (justa {mejor['justa']})"
                                                                    if mejor else "nada por encima de lo justo")) if ult else "Aún no ha buscado",
        "trabajando": bool(ult and (ult.get("hora") or "") >= (ahora - timedelta(minutes=15)).strftime("%Y-%m-%dT%H:%M")),
        "alerta": bool(avisos_hoy and any(v.get("post") not in (control.get("aprobados") or {}) and v.get("post") not in cancel
                                          for v in avisos_hoy)),
        "historial": [{"h": x["hora"][11:16], "t": "🚨 " + corto(x["t"], 90)} for x in (cz.get("historial") or [])
                      if x["hora"][:10] == hoy][-6:],
    }

    # 10/11 (Marcos: «un mínimo diario»): a las 17:00, si hoy falta el pick del día, aviso al móvil (una vez al día)
    try:
        faltan = [n for n, k in (("pick de las 10:30", "-pick-seguro"), ("pick de las 18:00", "-pick-seguro-2"))
                  if not any(pid.startswith(hoy) and pid.endswith(k) and pid not in cancel for pid in todos)]
        marca = DATOS / "minimo_avisado.txt"
        if faltan and ahora.hour == 17 and valor("aviso_guardar", control) and \
                (not marca.exists() or marca.read_text().strip() != hoy):
            from alineaciones_posts import dm
            dm("⚠️ Mínimo diario: hoy falta el " + " y el ".join(faltan)
               + ". El bot no encontró ninguno que cumpla. Dime si buscamos uno a mano 👀")
            marca.write_text(hoy)
            roles["vigilante"]["historial"].insert(0, {"h": ahora.strftime("%H:%M"), "t": "Aviso: falta el " + " y el ".join(faltan)})
    except Exception as e:
        print("mínimo diario:", e)

    # 10/11: lo que apuntan los roles de IA (las revisiones programadas de Claude) en datos/oficina_roles.json
    for x in leer(DATOS / "oficina_roles.json", []) or []:
        if (x.get("hora") or "")[:10] == hoy and x.get("rol") in roles:
            roles[x["rol"]]["historial"].insert(0, {"h": x["hora"][11:16], "t": "🤖 " + corto(x.get("texto"), 120)})
    for r in roles.values():
        r["historial"] = sorted(r["historial"], key=lambda h: h["h"] if h["h"][:1].isdigit() else "", reverse=True)[:8]

    h1, h2 = valor("hora_pick1", control), valor("hora_pick2", control)
    salida = []
    for rid, meta in ROLES.items():
        r = roles[rid]
        pausa = pausado(rid, control)
        estado = "pausa" if pausa else ("alerta" if r.get("alerta") else "trabajando" if r["trabajando"] else "esperando")
        salida.append({
            "id": rid, "t": meta["t"], "d": meta["d"], "estado": estado,
            "ahora": "En pausa: no hago nada hasta que me reanudes" if pausa else r["ahora"],
            "ritmo": RITMO[rid].format(h1=h1, h2=h2),
            "historial": r["historial"],
            "ajustes": [dict({x: y for x, y in a.items() if x != "rol"}, k=k, v=valor(k, control))
                        for k, a in AJUSTES_ROLES.items() if a["rol"] == rid],
            **{k: r[k] for k in ("canales", "pendientes", "propuestas") if k in r},
        })
    datos = {"generado": ahora.strftime("%Y-%m-%d %H:%M"), "roles": salida}
    SALIDA.parent.mkdir(parents=True, exist_ok=True)
    SALIDA.write_text(json.dumps(datos, ensure_ascii=False) + "\n", encoding="utf-8")
    return datos


if __name__ == "__main__":
    d = main()
    for r in d["roles"]:
        print(f"{r['t']:12} {r['estado']:11} {r['ahora']}")
        for h in r["historial"][:3]:
            print(f"     {h['h']:5} {h['t']}")
