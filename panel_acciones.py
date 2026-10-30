"""
30/10 (Marcos): acciones del PANEL DE CONTROL (docs/panel). La mini app manda al bot del móvil una lista de
cambios ({"v":1,"acc":[...]}) y asistente.py llama a aplicar(). Devuelve (líneas para contestar, archivos tocados).

  texto      {"id", "t"}             texto nuevo del post (control.json → textos)
  hora       {"id", "h", "f"}        nueva hora (HH:MM) del día f; si es del bot, pasa a la cola con esa hora
  ya         {"id"}                  sale en 2 minutos
  cancelar / recuperar {"id"}
  retry      {"k"}                   reintentar una red que falló (incidencias.solicitar)
  resp       {"id","post","u","c","t"}  responder en Threads a un comentario (lo publica redes.py)
  ignorar    {"id"}                  comentario que no se contesta
  pausa      {"v"}                   parar / reanudar todo
  ajuste     {"k","v"}               interruptores (control.json → ajustes)
  subir      {}                      el bot pide la foto o el texto
"""
import json
from datetime import datetime, timedelta

from bot import DATOS, MADRID, RAIZ, leer
from incidencias import publicaciones, solicitar
from panel_datos import AJUSTES

CONTROL = RAIZ / "publicaciones" / "control.json"
COLA = RAIZ / "publicaciones" / "cola.json"
RESPUESTAS = RAIZ / "publicaciones" / "respuestas_threads.json"
COMENTARIOS = DATOS / "comentarios_threads.json"


def escribir(ruta, datos):
    ruta.write_text(json.dumps(datos, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def titulo(p):
    l = [x for x in (p.get("texto") or "").strip().splitlines() if x.strip()]
    return (l[1] if l and "COMBI LOCAS" in l[0].upper() and len(l) > 1 else (l[0] if l else p["id"]))[:50]


def mover(p, cuando, cola):
    """Cambia la hora: si está en la cola se cambia ahí; si es del bot, se copia a la cola (manda sobre auto.json)."""
    nueva = cuando.strftime("%Y-%m-%dT%H:%M")
    for x in cola:
        if x["id"] == p["id"]:
            x["fecha"] = nueva
            return
    copia = {k: v for k, v in p.items() if k not in ("enviado", "mensaje_id", "error", "redes", "errores_redes", "caducada")}
    copia.update(fecha=nueva, directo=True, forzar=True, nota=f"hora cambiada desde el panel ({datetime.now(MADRID):%d/%m %H:%M})")
    cola.append(copia)


def aplicar(datos, ahora=None):
    ahora = ahora or datetime.now(MADRID)
    acc = (datos or {}).get("acc") or []
    control = leer(CONTROL, {}) or {}
    control.setdefault("cancelados", [])
    control.setdefault("textos", {})
    cola = leer(COLA, []) or []
    resp = leer(RESPUESTAS, []) or []
    com = leer(COMENTARIOS, []) or []
    posts = {p["id"]: p for p in publicaciones(RAIZ)}
    lineas, tocados = [], set()
    for a in acc:
        tipo, pid = a.get("a"), a.get("id")
        p = posts.get(pid) if pid else None
        try:
            if tipo in ("texto", "hora", "ya", "cancelar", "recuperar") and not p:
                lineas.append("⚠️ No encuentro un post (puede que ya haya salido).")
                continue
            if tipo in ("texto", "hora", "ya") and (p.get("enviado") or p.get("mensaje_id")):
                lineas.append(f"⚠️ «{titulo(p)}» ya ha salido: no lo cambio.")
                continue
            if tipo == "texto" and a.get("t", "").strip():
                control["textos"][pid] = a["t"].strip()
                tocados.add(CONTROL)
                lineas.append(f"✏️ Texto cambiado: «{titulo(p)}»")
            elif tipo == "hora":
                h, m = (int(x) for x in a["h"].split(":"))
                cuando = datetime.fromisoformat(a.get("f") or p["fecha"][:10]).replace(hour=h, minute=m, tzinfo=MADRID)
                if cuando < ahora - timedelta(minutes=5):
                    lineas.append(f"⚠️ «{titulo(p)}»: las {a['h']} ya han pasado.")
                    continue
                mover(p, cuando, cola)
                tocados.add(COLA)
                lineas.append(f"🕒 «{titulo(p)}» → {a['h']}")
            elif tipo == "ya":
                mover(p, ahora + timedelta(minutes=2), cola)
                tocados.add(COLA)
                lineas.append(f"⚡ «{titulo(p)}» sale ya")
            elif tipo == "cancelar":
                if pid not in control["cancelados"]:
                    control["cancelados"].append(pid)
                tocados.add(CONTROL)
                lineas.append(f"✕ Cancelado: «{titulo(p)}»")
            elif tipo == "recuperar":
                control["cancelados"] = [x for x in control["cancelados"] if x != pid]
                tocados.add(CONTROL)
                lineas.append(f"↩️ Recuperado: «{titulo(p)}»")
            elif tipo == "retry":
                lineas.append("🔁 " + str(solicitar(RAIZ, a["k"], ahora)))
                tocados.add(RAIZ / "publicaciones" / "reintentos.json")
            elif tipo == "resp" and a.get("t", "").strip():
                resp.append({"post": a["post"], "usuario": a["u"], "comentario": a.get("c"), "texto": a["t"].strip(),
                             "pedido": f"{ahora:%Y-%m-%d %H:%M} panel"})
                for c in com:
                    if c["id"] == pid:
                        c["hecho"] = "respondido"
                tocados |= {RESPUESTAS, COMENTARIOS}
                lineas.append(f"💬 A @{a['u']}: «{a['t'].strip()}»")
            elif tipo == "ignorar":
                for c in com:
                    if c["id"] == pid:
                        c["hecho"] = "ignorado"
                tocados.add(COMENTARIOS)
                lineas.append("🙈 Comentario sin contestar")
            elif tipo == "pausa":
                control["pausa"] = bool(a.get("v"))
                tocados.add(CONTROL)
                lineas.append("⏸️ Bot en PAUSA: no se publica nada" if control["pausa"] else "▶️ Bot publicando otra vez")
            elif tipo == "ajuste" and a.get("k") in AJUSTES:
                k, v = a["k"], a.get("v")
                cfg = AJUSTES[k]
                if cfg["tipo"] == "num":
                    v = max(cfg["min"], min(cfg["max"], float(v)))
                    v = int(v) if cfg["paso"] == 1 else v
                elif cfg["tipo"] == "si_no":
                    v = bool(v)
                elif not (isinstance(v, str) and len(v) == 5 and v[2] == ":"):
                    continue
                control.setdefault("ajustes", {})[k] = v
                tocados.add(CONTROL)
                bonito = ("sí" if v else "no") if cfg["tipo"] == "si_no" else str(v).replace(".", ",")
                lineas.append(f"🎛️ {cfg['t']}: {bonito}")
        except Exception as e:
            lineas.append(f"⚠️ No he podido hacer «{tipo}»: {str(e)[:80]}")
    a_cuota = (control.get("ajustes") or {})
    if a_cuota.get("cuota_min", 0) > a_cuota.get("cuota_max", 99):
        a_cuota["cuota_min"], a_cuota["cuota_max"] = a_cuota["cuota_max"], a_cuota["cuota_min"]
    if CONTROL in tocados:
        escribir(CONTROL, control)
    if COLA in tocados:
        escribir(COLA, cola)
    if RESPUESTAS in tocados:
        RESPUESTAS.write_text(json.dumps(resp, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    if COMENTARIOS in tocados:
        COMENTARIOS.write_text(json.dumps(com, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return lineas, [t for t in tocados if t.exists()]
