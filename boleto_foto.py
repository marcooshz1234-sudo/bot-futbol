"""
Recorta el dinero de una captura de boleto de bet365 (27/10, Marcos): quita el bloque
«Imp: … / Ganancias …» y el botón verde de abajo («Cerrar apuesta» / «Apostar»).
Busca la franja verde del botón desde abajo y corta un poco por encima (el bloque del importe).
"""
from PIL import Image


def verde(px):
    r, g, b = px[:3]
    return g > 110 and g > r + 50 and g > b + 15


def cuota(im, desde):
    """Lee «Imp: 5,00€» y «Ganancias 168,75€» de la parte de abajo (antes de recortarla) → 33,75."""
    import re
    import subprocess
    import tempfile
    from PIL import ImageOps
    w, h = im.size
    zona = ImageOps.invert(im.crop((0, desde, w, h)).convert("L")).resize((w * 2, (h - desde) * 2))
    with tempfile.NamedTemporaryFile(suffix=".png") as f:
        zona.save(f.name)
        txt = subprocess.run(["tesseract", f.name, "-", "--psm", "6"], capture_output=True, text=True).stdout
    txt = re.sub(r"(\d),\s+(\d{2})", r"\1,\2", txt)    # «5, 00€» → «5,00€»
    cifras = [float(x.replace(".", "").replace(",", ".")) for x in re.findall(r"(\d{1,3}(?:\.\d{3})*,\d{2})\s*€?", txt)]
    cifras = [c for c in cifras if c > 0]
    imp = re.search(r"Imp[^\d]*(\d{1,3}(?:\.\d{3})*,\d{2})", txt)
    imp = float(imp.group(1).replace(".", "").replace(",", ".")) if imp else (min(cifras) if cifras else None)
    if not imp or len(cifras) < 2:
        return None
    c = max(cifras) / imp
    return round(c, 2) if c > 1.05 else None


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
    try:
        c = cuota(im, corte)
    except Exception:
        c = None
    im.crop((0, 0, w, corte)).save(destino, quality=92)
    return c
