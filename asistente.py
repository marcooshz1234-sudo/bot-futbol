"""
El Publicador · asistente en el móvil.

Hablas con @combilocas_publica_bot por privado y solo te hace caso a ti (el
creador del canal). Funciona en GitHub Actions: cada tanda escucha ~5 h 50 min
y la siguiente toma el relevo.

Comandos:
  /hoy        lo que hay programado hoy en el canal
  /picks      picks de hoy · /manana picks de mañana
  /combis     combis de hoy y escalera
  /pausa      para todas las publicaciones automáticas · /reanudar
  /borrar     últimos posts → los borras de Telegram, Threads, Instagram y Facebook a la vez
  /ayuda
Además:
  - 60 min antes de cada post automático te llega el borrador con
    [✅ Vale] [✏️ Cambiar] [❌ Cancelar]. Si no contestas, sale tal cual.
  - Si le mandas un texto o una foto con texto, te pregunta si lo sube ya.
  - /editar → últimos posts publicados para cambiar su texto en el canal.

Lo que decides se guarda en publicaciones/control.json (el Publicador lo lee).
"""

import json
import os
import subprocess
import time
from datetime import datetime, timedelta
from pathlib import Path
from incidencias import solicitar, publicaciones, identificador, motivo_bloqueo

from publicar_telegram import AUTOS, COLA, ENVIADOS, MADRID, RAIZ, api, preparar_texto

CONTROL = RAIZ / "publicaciones" / "control.json"
PROPIOS = RAIZ / "publicaciones" / "asistente.json"     # lo que se publica desde el móvil
DURACION = timedelta(hours=5, minutes=50)
AVISO_ANTES = timedelta(minutes=60)


def leer(ruta, defecto):
    try:
        return json.loads(Path(ruta).read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return defecto


def escribir(ruta, datos):
    Path(ruta).write_text(json.dumps(datos, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def git(*args):
    return subprocess.run(["git", "-C", str(RAIZ), *args], capture_output=True, text=True)


def guardar(mensaje):
    git("add", "-A", "publicaciones", "datos/comunidad_picks.json")
    if git("diff", "--cached", "--quiet").returncode == 0:
        return
    git("commit", "-q", "-m", f"Asistente: {mensaje}")
    for _ in range(3):
        if git("pull", "--rebase", "-q").returncode == 0 and git("push", "-q").returncode == 0:
            return
        time.sleep(5)


def actualizar():
    git("pull", "--rebase", "-q")


def borrables():
    """Posts ya publicados en los últimos 3 días (cola a mano y automáticos)."""
    desde = (datetime.now(MADRID) - timedelta(days=3)).strftime("%Y-%m-%dT%H:%M")
    ahora = datetime.now(MADRID).strftime("%Y-%m-%dT%H:%M")
    cola = leer(COLA, [])
    enviados = leer(ENVIADOS, {})
    auto = [dict(p, **enviados.get(p["id"], {})) for r in AUTOS if r.exists() for p in leer(r, [])]
    hechos = leer(RAIZ / "publicaciones" / "borrados.json", [])
    lista = [p for p in cola + auto if desde <= p["fecha"] <= ahora and p["id"] not in hechos
             and (p.get("enviado") or p.get("redes") or p.get("borrado") or not p.get("caducada"))]
    return sorted(lista, key=lambda p: p["fecha"])[-12:]


def borrar_en_todas(token_tg, canal, p):
    """Lo pulsa el dueño del canal: borra el post en cada red. Si no tenemos el id de una red
    (posts que salieron por Metricool) lo busca entre los últimos posts por la primera línea."""
    from redes import FACEBOOK, INSTAGRAM, THREADS, llamar, pagina_facebook
    linea = p["texto"].strip().splitlines()[0].strip()[:40]
    ids = dict(p.get("redes") or {})
    res = []
    if p.get("mensaje_id") and not p.get("borrado"):
        try:
            api(token_tg, "deleteMessage", {"chat_id": canal, "message_id": p["mensaje_id"]})
            res.append("✅ Telegram")
        except Exception as e:
            res.append(f"⚠️ Telegram: {e}")
    claves = {"threads": os.environ.get("THREADS_TOKEN"), "instagram": os.environ.get("INSTAGRAM_TOKEN")}
    fb_usuario = os.environ.get("FACEBOOK_TOKEN")
    redes = []
    if claves["threads"]:
        redes.append(("Threads", THREADS, claves["threads"], "me/threads", "text", "timestamp"))
    if claves["instagram"]:
        redes.append(("Instagram", INSTAGRAM, claves["instagram"], "me/media", "caption", "timestamp"))
    if fb_usuario:
        try:
            pag, tok = pagina_facebook(fb_usuario, os.environ.get("FACEBOOK_PAGINA"))
            redes.append(("Facebook", FACEBOOK, tok, f"{pag}/posts", "message", "created_time"))
        except Exception as e:
            res.append(f"⚠️ Facebook: {e}")
    from datetime import timezone
    momento = datetime.fromisoformat(p["fecha"]).replace(tzinfo=MADRID)

    def mismo_dia(ts):   # solo posts publicados cerca de su hora (evita títulos repetidos de otros días)
        try:
            t = datetime.fromisoformat((ts or "").replace("Z", "+00:00").replace("+0000", "+00:00"))
        except ValueError:
            return False
        return abs((t - momento).total_seconds()) < 6 * 3600

    for nombre, base, tok, lista, campo, ts in redes:
        clave = {"Threads": "threads", "Instagram": "instagram", "Facebook": "facebook"}[nombre]
        objetivo = [i for i in (ids.get(clave), ids.get("instagram_reel") if clave == "instagram" else None) if i]
        try:
            if not objetivo:   # buscarlo por la primera línea entre los últimos posts
                r = llamar("GET", f"{base}/{lista}", {"fields": f"id,{campo},{ts}", "limit": 40, "access_token": tok})
                objetivo = [x["id"] for x in r.get("data", []) if linea and linea in (x.get(campo) or "")
                            and mismo_dia(x.get(ts))]
            if not objetivo:
                res.append(f"➖ {nombre}: no estaba publicado")
                continue
            for i in objetivo:
                llamar("DELETE", f"{base}/{i}", {"access_token": tok})
            res.append(f"✅ {nombre}" + (f" ({len(objetivo)})" if len(objetivo) > 1 else ""))
        except Exception as e:
            motivo = ("Instagram no deja borrar posts desde fuera de su app" if nombre == "Instagram"
                      else "lo publicó Metricool y Facebook solo deja borrarlo a quien lo publicó"
                      if "(#200)" in str(e) else str(e)[:150])
            enlaces = []
            for i in objetivo:   # enlace directo para borrarlo a mano de un toque
                try:
                    campo_url = "permalink_url" if nombre == "Facebook" else "permalink"
                    u = llamar("GET", f"{base}/{i}", {"fields": campo_url, "access_token": tok}).get(campo_url)
                    if u:
                        enlaces.append(u if u.startswith("http") else f"https://www.facebook.com{u}")
                except Exception:
                    pass
            res.append(f"⚠️ {nombre}: {motivo}\n👉 Ábrelo y bórralo: " + (" ".join(enlaces) or "(no encuentro el enlace)"))
    hechos = leer(RAIZ / "publicaciones" / "borrados.json", [])
    escribir(RAIZ / "publicaciones" / "borrados.json", (hechos + [p["id"]])[-200:])
    guardar(f"borrado {p['id']}")
    return "🗑️ " + p["texto"].splitlines()[0][:50] + "\n\n" + "\n\n".join(res)


class Asistente:
    def __init__(self, token, canal):
        self.t, self.canal = token, canal
        admins = api(token, "getChatAdministrators", {"chat_id": canal})["result"]
        self.duenio = next(a["user"]["id"] for a in admins if a["status"] == "creator")
        self.esperando = None       # ("cambiar", id) / ("editar", mensaje_id, es_foto)
        self.borrador = None        # texto/foto recibidos pendientes de "¿lo subo?"
        api(token, "setMyCommands", {"commands": [
            {"command": "hoy", "description": "Lo programado hoy en el canal"},
            {"command": "picks", "description": "Picks de hoy"},
            {"command": "manana", "description": "Picks de mañana"},
            {"command": "combis", "description": "Combis de hoy y escalera"},
            {"command": "editar", "description": "Cambiar un post ya publicado"},
            {"command": "pausa", "description": "Parar las publicaciones automáticas"},
            {"command": "reanudar", "description": "Volver a publicar"},
            {"command": "ayuda", "description": "Qué puedo hacer"}]})

    # ---------------------------------------------------------------- utilidades
    def enviar(self, texto, botones=None):
        d = {"chat_id": self.duenio, "text": texto[:4096], "link_preview_options": {"is_disabled": True}}
        if botones:
            d["reply_markup"] = {"inline_keyboard": [[{"text": t, "callback_data": c} for t, c in fila] for fila in botones]}
        return api(self.t, "sendMessage", d)

    def control(self):
        c = leer(CONTROL, {})
        c.setdefault("pausa", False)
        c.setdefault("cancelados", [])
        c.setdefault("textos", {})
        c.setdefault("avisados", [])
        return c

    def programados(self):
        enviados = leer(ENVIADOS, {})
        posts = [p for ruta in AUTOS for p in leer(ruta, [])] + leer(COLA, [])
        for p in posts:
            p.update(enviados.get(p["id"], {}))
        return sorted(posts, key=lambda p: p["fecha"])

    # ---------------------------------------------------------------- avisos previos
    def avisar_borradores(self):
        c = self.control()
        ahora = datetime.now(MADRID)
        cambios = False
        for p in self.programados():
            if p.get("enviado") or p.get("caducada") or p["id"] in c["avisados"] or p["id"] in c["cancelados"]:
                continue
            cuando = datetime.fromisoformat(p["fecha"]).replace(tzinfo=MADRID)
            if timedelta(0) < cuando - ahora <= AVISO_ANTES:
                texto = c["textos"].get(p["id"], p["texto"])
                try:
                    from revisor import veredicto
                    avisos = veredicto(p)
                except Exception as e:
                    print("veredicto:", str(e)[:120])
                    avisos = None
                nota = ("" if avisos is None else "\n\n🟢 El bot no ve nada raro." if not avisos
                        else "\n\n⚠️ Ojo:\n" + "\n".join(f"• {a}" for a in avisos[:6]))
                self.enviar(f"📝 Sale a las {cuando:%H:%M}:\n\n{texto}{nota}",
                            [[("✅ Vale", f"ok|{p['id']}"), ("✏️ Cambiar", f"cambiar|{p['id']}"),
                              ("❌ Cancelar", f"cancelar|{p['id']}")]])
                c["avisados"].append(p["id"])
                cambios = True
        if cambios:
            c["avisados"] = c["avisados"][-200:]
            escribir(CONTROL, c)
            guardar("avisos enviados")

    # ---------------------------------------------------------------- comandos
    def cmd(self, texto):
        partes = texto.split()
        orden = partes[0].split("@")[0].lower()
        hoy = datetime.now(MADRID).date()
        if orden == "/start" and len(partes) == 2 and partes[1].startswith("retry_"):
            clave = partes[1][6:]
            for p in publicaciones(RAIZ):
                for red in ("telegram", "threads", "instagram", "facebook", "instagram_reel"):
                    if identificador(p['id'], red) == clave:
                        motivo = motivo_bloqueo(p, red, self.control(), datetime.now(MADRID))
                        if motivo:
                            return self.enviar(motivo)
                        return self.enviar(f"Reintentar en {red}: {p['texto'].splitlines()[0]}\n\nSolo se intentará esta red; se conservarán los envíos ya confirmados.",
                                           [[("Reintentar", f"retry|{clave}"), ("Cancelar", "ok_no")]])
            return self.enviar("Incidencia no encontrada. Actualiza el panel.")
        if orden == "/start" and len(partes) == 2 and partes[1] in ("pausa", "reanudar"):   # botones de la app
            return self.cmd("/" + partes[1])
        if orden == "/start" and len(partes) == 2 and partes[1][:2] in ("c_", "r_", "e_"):
            import hashlib
            accion, codigo = partes[1][:1], partes[1][2:]
            p = next((x for x in self.programados() if hashlib.sha1(x["id"].encode()).hexdigest()[:16] == codigo), None)
            if not p:
                return self.enviar("No encuentro ese post (puede que ya haya salido). Actualiza la app.")
            c = self.control()
            titulo = p["texto"].strip().splitlines()[0][:60]
            if accion == "c":
                if p["id"] not in c["cancelados"]:
                    c["cancelados"].append(p["id"])
                    escribir(CONTROL, c)
                    guardar(f"cancelado desde la app {p['id']}")
                return self.enviar(f"❌ Cancelado: «{titulo}» ({p['fecha'][11:16]}). No saldrá.",
                                   [[("↩️ Recuperarlo", f"recuperar|{p['id']}")]])
            if accion == "r":
                c["cancelados"] = [x for x in c["cancelados"] if x != p["id"]]
                escribir(CONTROL, c)
                guardar(f"recuperado desde la app {p['id']}")
                return self.enviar(f"↩️ Recuperado: «{titulo}» saldrá a las {p['fecha'][11:16]}.")
            self.esperando = ("cambiar", p["id"])
            actual = c["textos"].get(p["id"], p["texto"])
            return self.enviar(f"✏️ Así está ahora «{titulo}» ({p['fecha'][11:16]}):\n\n{actual}\n\n"
                               "Mándame el texto nuevo completo (el aviso de +18 lo pongo yo).")
        if orden in ("/start", "/ayuda"):
            return self.enviar(__doc__.split("Comandos:")[1].split("Lo que decides")[0].strip())
        if orden == "/hoy":
            c = self.control()
            lineas = []
            for p in self.programados():
                if p["fecha"][:10] != hoy.isoformat():
                    continue
                estado = ("✅ publicado" if p.get("enviado") else "❌ cancelado" if p["id"] in c["cancelados"]
                          else "⏭️ caducado" if p.get("caducada") else "⏳ pendiente")
                lineas.append(f"{p['fecha'][11:]} · {p['texto'].splitlines()[0][:45]} · {estado}")
            pausa = "\n\n⏸️ PUBLICACIONES EN PAUSA (/reanudar)" if c["pausa"] else ""
            return self.enviar("📅 Hoy en el canal:\n\n" + ("\n".join(lineas) or "Nada programado") + pausa)
        if orden in ("/picks", "/manana", "/picks_manana", "/picksmanana"):
            pide_manana = orden != "/picks" or (len(partes) > 1 and partes[1].lower().startswith("ma"))
            dia = hoy + timedelta(days=1 if pide_manana else 0)
            d = (leer(RAIZ / "datos" / "picks.json", {}).get("dias") or {}).get(dia.isoformat())
            if not d:
                return self.enviar(f"No hay picks para el {dia:%d/%m}.")
            lineas = [f"{p['fecha'][11:]} · {p['texto']} · {p['cuota']:.2f} · {p['frecuencia']:.0%}"
                      for p in d["mejores_por_partido"][:15]]
            return self.enviar(f"🎯 Picks {dia:%d/%m} (cuota · se cumplió):\n\n" + "\n".join(lineas))
        if orden == "/combis":
            d = (leer(RAIZ / "datos" / "picks.json", {}).get("dias") or {}).get(hoy.isoformat()) or {}
            txt = []
            for k, v in (d.get("combis") or {}).items():
                if v:
                    txt.append(f"{k.upper()} · {v['cuota']:.2f}\n" + "\n".join(f"- {p['texto']}" for p in v["picks"]))
            esc = (leer(RAIZ / "datos" / "escalera.json", {}) or {}).get("actual")
            if esc:
                txt.append(f"ESCALERA · escalón {esc['escalon']} · {esc['stake']:.2f}€ · x{esc['cuota']:.2f}\n"
                           + "\n".join(f"- {p['texto']}" for p in esc["picks"]))
            return self.enviar("\n\n".join(txt) or "Hoy no hay combis.")
        if orden in ("/pausa", "/reanudar"):
            c = self.control()
            c["pausa"] = orden == "/pausa"
            escribir(CONTROL, c)
            guardar(orden[1:])
            return self.enviar("⏸️ Publicaciones automáticas en pausa." if c["pausa"] else "▶️ Publicaciones reanudadas.")
        if orden == "/editar":
            ultimos = [p for p in self.programados() if p.get("mensaje_id")][-6:]
            ultimos += [p for p in leer(PROPIOS, []) if p.get("mensaje_id")][-3:]
            if not ultimos:
                return self.enviar("No hay publicaciones recientes del bot para editar.")
            botones = [[(f"{p.get('enviado', '')[11:16]} {p['texto'].splitlines()[0][:30]}",
                         f"editar|{p['mensaje_id']}|{1 if p.get('foto') else 0}")] for p in ultimos]
            return self.enviar("¿Cuál quieres cambiar?", botones)
        if orden == "/borrar":
            recientes = borrables()
            if not recientes:
                return self.enviar("No hay publicaciones recientes para borrar.")
            botones = [[(f"{p['fecha'][5:10]} {p['fecha'][11:16]} {p['texto'].splitlines()[0][:28]}",
                         f"borrar|{p['id']}")] for p in recientes]
            return self.enviar("🗑️ ¿Cuál quieres borrar de todas las redes?", botones)
        return self.enviar("No conozco ese comando. Escribe /ayuda.")

    # ---------------------------------------------------------------- botones
    def boton(self, q):
        accion, *resto = q["data"].split("|")
        api(self.t, "answerCallbackQuery", {"callback_query_id": q["id"]})
        c = self.control()
        if accion == "retry":
            resultado = solicitar(RAIZ, resto[0])
            guardar("solicitud de reintento")
            return self.enviar(resultado)
        if accion == "ok":
            return self.enviar("👍 Saldrá a su hora.")
        if accion == "recuperar":
            c["cancelados"] = [x for x in c["cancelados"] if x != resto[0]]
            escribir(CONTROL, c)
            guardar(f"recuperado {resto[0]}")
            return self.enviar("↩️ Recuperado, saldrá a su hora.")
        if accion == "cancelar":
            c["cancelados"].append(resto[0])
            escribir(CONTROL, c)
            guardar(f"cancelado {resto[0]}")
            return self.enviar("❌ Cancelado, no se publicará.")
        if accion == "cambiar":
            self.esperando = ("cambiar", resto[0])
            return self.enviar("✏️ Mándame el texto nuevo completo (el aviso de +18 lo pongo yo).")
        if accion == "editar":
            self.esperando = ("editar", int(resto[0]), resto[1] == "1")
            return self.enviar("✏️ Mándame el texto nuevo para ese post del canal.")
        if accion == "subir" and self.borrador:
            b, self.borrador = self.borrador, None
            texto = preparar_texto(b["texto"])
            if b.get("foto"):
                r = api(self.t, "sendPhoto", {"chat_id": self.canal, "photo": b["foto"], "caption": texto[:1024]})
            else:
                r = api(self.t, "sendMessage", {"chat_id": self.canal, "text": texto,
                                                "link_preview_options": {"is_disabled": True}})
            propios = leer(PROPIOS, [])
            propios.append({"id": f"movil-{datetime.now(MADRID):%Y%m%d-%H%M%S}", "texto": b["texto"],
                            "foto": bool(b.get("foto")), "enviado": datetime.now(MADRID).strftime("%Y-%m-%dT%H:%M"),
                            "mensaje_id": r["result"]["message_id"]})
            escribir(PROPIOS, propios[-100:])
            guardar("publicado desde el móvil")
            return self.enviar("✅ Publicado en el canal.")
        if accion == "borrar":
            p = next((x for x in borrables() if x["id"] == resto[0]), None)
            if not p:
                return self.enviar("No lo encuentro.")
            return self.enviar(f"¿Borrar este post de Telegram, Threads, Instagram y Facebook? No se puede deshacer.\n\n"
                               f"{p['texto'][:300]}", [[("🗑️ Sí, borrar", f"borrarya|{p['id']}"), ("No", "ok_no")]])
        if accion == "borrarya":
            p = next((x for x in borrables() if x["id"] == resto[0]), None)
            if not p:
                return self.enviar("No lo encuentro.")
            self.enviar("⏳ Borrando…")
            return self.enviar(borrar_en_todas(self.t, self.canal, p))
        if accion == "ok_no":
            return self.enviar("👍 No se borra nada.")
        if accion == "descartar":
            self.borrador = None
            return self.enviar("🗑️ Descartado.")

    # ---------------------------------------------------------------- mensajes
    def mensaje(self, m):
        texto = m.get("text") or m.get("caption") or ""
        if texto.startswith("/"):
            return self.cmd(texto)
        if self.esperando:
            tipo, *datos = self.esperando
            self.esperando = None
            if tipo == "cambiar":
                c = self.control()
                c["textos"][datos[0]] = texto
                escribir(CONTROL, c)
                guardar(f"texto cambiado {datos[0]}")
                return self.enviar("✅ Cambiado. Saldrá con tu texto.")
            if tipo == "editar":
                mid, es_foto = datos
                metodo, campo = ("editMessageCaption", "caption") if es_foto else ("editMessageText", "text")
                api(self.t, metodo, {"chat_id": self.canal, "message_id": mid, campo: preparar_texto(texto)})
                return self.enviar("✅ Editado en el canal.")
        foto = (m.get("photo") or [{}])[-1].get("file_id")
        if not texto and not foto:
            return self.enviar("Mándame un texto o una foto con texto y te pregunto si lo subo.")
        self.borrador = {"texto": texto, "foto": foto}
        vista = preparar_texto(texto) if texto else "(solo foto)"
        return self.enviar(f"¿Lo subo así al canal?\n\n{vista}",
                           [[("✅ Publicar ya", "subir"), ("🗑️ Descartar", "descartar")]])

    # ---------------------------------------------------------------- bucle
    def escuchar(self):
        fin = datetime.now(MADRID) + DURACION
        offset, ultimo_pull = None, 0
        while datetime.now(MADRID) < fin:
            if time.time() - ultimo_pull > 120:
                actualizar()
                ultimo_pull = time.time()
                try:
                    self.avisar_borradores()
                except Exception as e:
                    print("aviso:", e)
            try:
                r = api(self.t, "getUpdates", {"timeout": 50, "offset": offset,
                                                "allowed_updates": ["message", "callback_query"]})
            except Exception as e:
                print("getUpdates:", e)
                time.sleep(10)
                continue
            for u in r.get("result", []):
                offset = u["update_id"] + 1
                quien = (u.get("message") or u.get("callback_query") or {}).get("from", {}).get("id")
                if quien != self.duenio:
                    m = u.get("message") or {}
                    if (m.get("chat") or {}).get("type") == "private" and m.get("text"):
                        try:   # seguidores: concurso del pick (comunidad.py)
                            import comunidad
                            r = comunidad.responder(m["text"], m.get("from") or {})
                            api(self.t, "sendMessage", {"chat_id": m["chat"]["id"], "text": r})
                            if m["text"].startswith("/pick"):
                                guardar("pick de un seguidor")
                        except Exception as e:
                            print("comunidad:", e)
                    continue
                try:
                    if "callback_query" in u:
                        self.boton(u["callback_query"])
                    elif (u["message"].get("chat") or {}).get("type") == "private":
                        self.mensaje(u["message"])
                except Exception as e:
                    print("error:", e)
                    try:
                        self.enviar(f"⚠️ Algo ha fallado: {e}")
                    except Exception:
                        pass


if __name__ == "__main__":
    Asistente(os.environ["TELEGRAM_TOKEN"], os.environ["TELEGRAM_CANAL"]).escuchar()
