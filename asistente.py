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
    git("add", "-A", "publicaciones")
    if git("diff", "--cached", "--quiet").returncode == 0:
        return
    git("commit", "-q", "-m", f"Asistente: {mensaje}")
    for _ in range(3):
        if git("pull", "--rebase", "-q").returncode == 0 and git("push", "-q").returncode == 0:
            return
        time.sleep(5)


def actualizar():
    git("pull", "--rebase", "-q")


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
                self.enviar(f"📝 Sale a las {cuando:%H:%M}:\n\n{texto}",
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
        return self.enviar("No conozco ese comando. Escribe /ayuda.")

    # ---------------------------------------------------------------- botones
    def boton(self, q):
        accion, *resto = q["data"].split("|")
        api(self.t, "answerCallbackQuery", {"callback_query_id": q["id"]})
        c = self.control()
        if accion == "ok":
            return self.enviar("👍 Saldrá a su hora.")
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
