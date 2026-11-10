"""
10/11: los roles de IA de la Oficina (revisiones programadas de Claude) apuntan aquí lo que han hecho, para que
salga en la ficha de su muñeco (oficina_datos.py). Uso: python anotar_rol.py <rol> "texto corto"
Roles: ojeador, analista, redactor, verificador, community, vigilante.
"""
import json
import sys
from datetime import datetime

from ajustes import ROLES
from bot import DATOS, MADRID, leer

RUTA = DATOS / "oficina_roles.json"


def anotar(rol, texto):
    if rol not in ROLES:
        raise SystemExit(f"Rol desconocido: {rol} (vale: {', '.join(ROLES)})")
    l = leer(RUTA, []) or []
    l.append({"rol": rol, "hora": datetime.now(MADRID).strftime("%Y-%m-%dT%H:%M"), "texto": " ".join(str(texto).split())[:200]})
    RUTA.write_text(json.dumps(l[-300:], ensure_ascii=False, indent=1) + "\n", encoding="utf-8")


if __name__ == "__main__":
    anotar(sys.argv[1], " ".join(sys.argv[2:]))
    print("apuntado")
