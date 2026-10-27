"""Comprueba que las claves de Meta funcionan (sin publicar nada) y lo apunta en publicaciones/estado_redes.json."""
import json
import os
from datetime import datetime
from zoneinfo import ZoneInfo

from redes import FACEBOOK, INSTAGRAM, RAIZ, THREADS, llamar, pagina_facebook

estado = {"comprobado": datetime.now(ZoneInfo("Europe/Madrid")).strftime("%Y-%m-%d %H:%M")}
pruebas = {
    "instagram": ("INSTAGRAM_TOKEN", lambda t: llamar("GET", f"{INSTAGRAM}/me", {"fields": "username,account_type", "access_token": t})),
    "threads": ("THREADS_TOKEN", lambda t: llamar("GET", f"{THREADS}/me", {"fields": "username", "access_token": t})),
    "facebook": ("FACEBOOK_TOKEN", lambda t: (lambda pid_tok: llamar("GET", f"{FACEBOOK}/{pid_tok[0]}",
                 {"fields": "name", "access_token": pid_tok[1]}))(pagina_facebook(t, os.environ.get("FACEBOOK_PAGINA")))),
}
for red, (var, prueba) in pruebas.items():
    token = os.environ.get(var)
    if not token:
        estado[red] = "sin clave"
        continue
    try:
        r = prueba(token)
        estado[red] = f"OK · {r.get('username') or r.get('name')}" + (f" ({r['account_type']})" if r.get("account_type") else "")
    except Exception as e:
        estado[red] = f"ERROR · {e}"
# aviso por Telegram al dueño del canal (máx. 1 al día): si una clave falla o se acerca su caducidad
ARCHIVO = RAIZ / "publicaciones" / "estado_redes.json"
try:   # 27/10: si el archivo se rompe (choque de git), se sigue igual: lo importante es comprobar las claves
    previo = json.loads(ARCHIVO.read_text(encoding="utf-8")) if ARCHIVO.exists() else {}
except ValueError:
    previo = {}
hoy = estado["comprobado"][:10]
estado["avisado"] = previo.get("avisado")
fallos = [f"{r}: {v}" for r, v in estado.items() if isinstance(v, str) and v.startswith("ERROR")]
if hoy >= "2026-12-14":
    fallos.append("Las claves de Meta caducan sobre el 21/12: hay que renovarlas (pídeselo a Claude)")
if fallos and estado["avisado"] != hoy and os.environ.get("TELEGRAM_TOKEN") and os.environ.get("TELEGRAM_CANAL"):
    try:
        from publicar_telegram import api
        tk, canal = os.environ["TELEGRAM_TOKEN"], os.environ["TELEGRAM_CANAL"]
        duenio = next(a["user"]["id"] for a in api(tk, "getChatAdministrators", {"chat_id": canal})["result"]
                      if a["status"] == "creator")
        api(tk, "sendMessage", {"chat_id": duenio, "text": "⚠️ Aviso de las redes:\n\n" + "\n".join(fallos)})
        estado["avisado"] = hoy
    except Exception as e:
        print(f"No se pudo avisar: {e}")
(RAIZ / "publicaciones" / "estado_redes.json").write_text(json.dumps(estado, ensure_ascii=False, indent=1), encoding="utf-8")
print(estado)
