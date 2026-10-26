"""
Escudos de todos los equipos de las ligas del bot (27/10), guardados en el repo para no depender de
internet al hacer la tarjeta del partido: publicaciones/media/escudos/<id>.png

Los saca del calendario de cada liga (datos/calendario_<liga>.json); solo descarga los que faltan.
"""
import json
import urllib.request

from bot import DATOS, RAIZ

DESTINO = RAIZ / "publicaciones" / "media" / "escudos"


def main():
    DESTINO.mkdir(parents=True, exist_ok=True)
    equipos = {}
    for f in DATOS.glob("calendario_*.json"):
        for x in json.loads(f.read_text(encoding="utf-8")):
            for lado in ("home", "away"):
                t = x["teams"][lado]
                if t.get("logo"):
                    equipos[t["id"]] = t["logo"]
    nuevos = fallos = 0
    for eq, url in equipos.items():
        destino = DESTINO / f"{eq}.png"
        if destino.exists():
            continue
        try:
            destino.write_bytes(urllib.request.urlopen(url, timeout=15).read())
            nuevos += 1
        except Exception as e:
            fallos += 1
            print(f"  ! {eq}: {e}")
    print(f"Escudos: {len(equipos)} equipos · {nuevos} nuevos · {fallos} fallos")


if __name__ == "__main__":
    main()
