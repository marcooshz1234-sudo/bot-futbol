"""09/11 (Marcos): el mapa de categorías (datos/ligas_mapa.json): qué liga es mejor o peor."""
from bot import DATOS, leer

_MAPA = None


def mapa():
    global _MAPA
    if _MAPA is None:
        _MAPA = leer(DATOS / "ligas_mapa.json", {}) or {}
    return _MAPA


def categoria(nombre_liga, pais="Spain", femenino=False):
    """{"nivel", "nombre", "fuerza"} de una liga por su nombre de API-Football; None si no está en el mapa."""
    paises = mapa().get("paises") or {}
    lista = paises.get(f"{pais} (femenino)" if femenino and f"{pais} (femenino)" in paises else pais) or []
    n = (nombre_liga or "").lower()
    mejor = None
    for c in lista:
        for p in c.get("patrones") or []:
            if n.startswith(p.lower()) and (not mejor or len(p) > mejor[0]):   # el patrón más largo gana
                mejor = (len(p), c)
    return mejor[1] if mejor else None
