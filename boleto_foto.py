"""
Recorta el dinero de una captura de boleto de bet365 (27/10, Marcos): quita el bloque
«Imp: … / Ganancias …» y el botón verde de abajo («Cerrar apuesta» / «Apostar»).
Busca la franja verde del botón desde abajo y corta un poco por encima (el bloque del importe).
"""
from PIL import Image


def verde(px):
    r, g, b = px[:3]
    return g > 110 and g > r + 50 and g > b + 15


def recortar(origen, destino):
    im = Image.open(origen).convert("RGB")
    w, h = im.size
    px = im.load()
    cols = range(int(w * 0.15), int(w * 0.85), max(1, w // 60))
    boton = None
    for y in range(h - 1, int(h * 0.4), -1):
        if sum(verde(px[x, y]) for x in cols) / len(cols) > 0.8:
            boton = y
        elif boton is not None:
            break                      # ya hemos subido por encima del botón
    # sin botón (apuesta ya hecha): el importe va al final de la tarjeta
    corte = boton - int(w * 0.22) if boton is not None else h - int(w * 0.37)
    corte = max(int(h * 0.3), corte)
    im.crop((0, 0, w, corte)).save(destino, quality=92)
    return destino
