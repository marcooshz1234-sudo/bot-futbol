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
(RAIZ / "publicaciones" / "estado_redes.json").write_text(json.dumps(estado, ensure_ascii=False, indent=1), encoding="utf-8")
print(estado)
