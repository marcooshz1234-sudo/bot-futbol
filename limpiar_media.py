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


DIAS_DATOS = 7   # 13/11: fotos de boletos de los canales y partidos en directo ya jugados


def datos_viejos(ahora=None):
    """13/11 (Marcos: «el proyecto limpio, que no ocupe espacio»): las fotos de boletos de los canales
    (datos/tipsters_fotos) de posts de hace más de una semana o que ya no están en tipsters_raw.json, y los
    partidos de datos/en_directo jugados hace más de una semana (los resultados quedan en datos/partidos)."""
    import json
    ahora = ahora or datetime.now(MADRID)
    limite = (ahora - timedelta(days=DIAS_DATOS)).strftime("%Y-%m-%d")
    datos = RAIZ / "datos"
    salida = []
    try:
        raw = json.loads((datos / "tipsters_raw.json").read_text(encoding="utf-8"))
        vivas = {x["foto_ruta"].rsplit("/", 1)[-1] for v in raw.values() for x in v
                 if x.get("foto_ruta") and (x.get("fecha") or "")[:10] >= limite}
        salida += [f for f in (datos / "tipsters_fotos").glob("*") if f.is_file() and f.name not in vivas]
    except Exception as e:
        print("tipsters_fotos:", e)
    for f in (datos / "en_directo").glob("*.json"):
        try:
            fecha = (json.loads(f.read_text(encoding="utf-8")).get("fecha") or "")[:10]
        except Exception:
            continue
        if fecha and fecha < limite:
            salida.append(f)
    return salida


def main():
    lista = a_borrar() + datos_viejos()
    peso = sum(f.stat().st_size for f in lista)
    if "--probar" not in sys.argv:
        for f in lista:
            f.unlink()
    print(f"Media: {len(lista)} archivos de hace más de {DIAS} días ({peso / 1e6:.0f} MB)"
          + (" (prueba, no se borra nada)" if "--probar" in sys.argv else " borrados"))


if __name__ == "__main__":
    main()
