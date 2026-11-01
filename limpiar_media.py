"""
01/11 (Marcos): el repo pesaba mucho (161 MB de imágenes y vídeos de posts). Las imágenes, historias y reels
solo hacen falta hasta que el post sale en todas las redes. Se borran del repo las de posts de hace más de
DIAS días; siguen en el historial de GitHub y los posts siguen publicados en Telegram, Threads e Instagram
(no se borra ninguna publicación). Nunca se toca escudos/ ni lo que use un post que aún no ha salido.
Lo llama recoger.yml (cada 6 h).
"""
import re
import sys
from datetime import datetime, timedelta

from bot import MADRID, RAIZ
from incidencias import publicaciones

MEDIA = RAIZ / "publicaciones" / "media"
DIAS = 3
FECHA = re.compile(r"^(\d{4}-\d{2}-\d{2})-")


def a_borrar(ahora=None):
    ahora = ahora or datetime.now(MADRID)
    limite = (ahora - timedelta(days=DIAS)).strftime("%Y-%m-%d")
    pendientes = [p for p in publicaciones(RAIZ) if not (p.get("enviado") or p.get("mensaje_id"))
                  and p["fecha"] >= ahora.strftime("%Y-%m-%dT%H:%M")]
    usados = {p["id"] for p in pendientes}
    rutas = {str(p.get(k)) for p in pendientes for k in ("foto", "foto_tg", "imagen") if p.get(k)}
    salida = []
    for f in MEDIA.iterdir():
        m = FECHA.match(f.name)
        if not f.is_file() or not m or m.group(1) >= limite:
            continue
        if any(f.name.startswith(u + ".") for u in usados) or any(f.name in r for r in rutas):
            continue
        salida.append(f)
    return salida


def main():
    lista = a_borrar()
    peso = sum(f.stat().st_size for f in lista)
    if "--probar" not in sys.argv:
        for f in lista:
            f.unlink()
    print(f"Media: {len(lista)} archivos de hace más de {DIAS} días ({peso / 1e6:.0f} MB)"
          + (" (prueba, no se borra nada)" if "--probar" in sys.argv else " borrados"))


if __name__ == "__main__":
    main()
