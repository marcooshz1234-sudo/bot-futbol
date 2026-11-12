"""12/11: prepara un logo de competición que manda Marcos (JPG/PNG con fondo blanco) para las fotos
(fondo de estadio de noche) y lo guarda en publicaciones/media/escudos/liga-<id>-hd.png.

Cómo (sin cortes bruscos, que dejaban restos y bordes feos):
- «color a alfa» contra el blanco (como el de GIMP): el blanco pasa a transparente y los bordes suaves se
  conservan, con su color real.
- MONO (logos de una tinta: Copa, Premier, Champions, Europa, Conference, Ligue 1, Champions fem.): se aplica a
  todo el logo, y lo muy oscuro pasa a blanco (si no, desaparece sobre el fondo oscuro). Los colores vivos se quedan.
- COLOR (Nations, LaLiga, Serie A, Bundesliga): solo se quita el blanco de FUERA (el de dentro del logo es parte
  del dibujo) y solo el texto gris/negro pasa a blanco.
Uso: python preparar_logo.py origen.jpg destino.png <id>
"""
import sys

import numpy as np
from PIL import Image

MONO = {143, 39, 2, 3, 848, 61, 525}


def color_a_alfa(a):
    """a: float 0-255 (h, w, 3) → (rgb sin mezclar con blanco, alfa 0-1)."""
    alfa = np.clip((255 - a).max(axis=2) / 255, 0, 1)
    seguro = np.where(alfa > 0, alfa, 1)[..., None]
    rgb = np.clip(255 - (255 - a) / seguro, 0, 255)
    return rgb, alfa


def preparar(src, dst, lid):
    from scipy import ndimage
    a = np.asarray(Image.open(src).convert("RGB")).astype(float)
    if lid == 39:   # el «transparente falso» de cuadros grises → blanco
        cuadros = ((a.max(axis=2) - a.min(axis=2)) < 14) & (a.min(axis=2) > 175)
        a[cuadros] = 255
    rgb, alfa = color_a_alfa(a)
    if lid not in MONO:   # solo el blanco de fuera (y 3 px de borde); lo de dentro, opaco y tal cual
        claro = a.min(axis=2) > 200
        etq, _ = ndimage.label(claro)
        borde = set(np.unique(np.concatenate([etq[0], etq[-1], etq[:, 0], etq[:, -1]]))) - {0}
        fuera = ndimage.binary_dilation(np.isin(etq, list(borde)), iterations=3)
        alfa = np.where(fuera, alfa, 1.0)
        rgb = np.where(fuera[..., None], rgb, a)
    mx, mn = rgb.max(axis=2), rgb.min(axis=2)
    sat = (mx - mn) / 255   # croma absoluto (el negro casi puro también es «neutro»)
    if lid in MONO:
        blanco = mx < 120                       # lo muy oscuro (negro, azul marino, morado) → blanco
    else:
        blanco = (sat < 0.18) & (mx < 140)      # solo el texto gris/negro
        if lid == 135:                          # Serie A: solo las letras (abajo), no los triángulos de la A
            filas = np.arange(a.shape[0])[:, None] > a.shape[0] * 0.72
            blanco = ((mx < 120) & filas) | blanco
    rgb[blanco] = 245
    if lid in MONO and blanco.any():   # que el blanco salga blanco del todo (no gris translúcido)
        tope = np.percentile(alfa[blanco & (alfa > 0.5)], 90) if (blanco & (alfa > 0.5)).any() else 1
        alfa = np.where(blanco, np.clip(alfa / max(tope, 0.5), 0, 1), alfa)
    if lid == 525:   # la original es pequeña y con ruido de JPG: bordes suavizados
        from PIL import ImageFilter
        alfa = np.asarray(Image.fromarray((alfa * 255).astype("uint8")).filter(ImageFilter.MedianFilter(3))) / 255
    if lid == 61:   # fuera el patrocinador (amarillo, debajo)
        amar = (a[..., 0] > 190) & (a[..., 1] > 130) & (a[..., 2] < 110)
        filas = np.where(amar.any(axis=1))[0]
        if len(filas):
            alfa[max(0, filas.min() - 12):] = 0
    im = Image.fromarray(np.dstack([rgb, alfa * 255]).round().astype("uint8"), "RGBA")
    caja = Image.fromarray((alfa > 0.04).astype("uint8") * 255).getbbox()
    im = im.crop(caja)
    im.thumbnail((800, 800), Image.LANCZOS)
    im.save(dst, optimize=True)
    return im.size


if __name__ == "__main__":
    print(preparar(sys.argv[1], sys.argv[2], int(sys.argv[3])))
