"""
09/11 (Marcos: «hacemos lo de las 2»): la imagen de los verdes.

- Opción 2 · ticket de Combilocas: imagen nuestra (no imita a bet365) con el pick o las patas, la cuota, la hora a
  la que se publicó y el resultado real de cada partido. Sale en todos los verdes (y es la de Instagram: sin dinero).
- Opción 1 · sello: si Marcos mandó al bot la captura REAL de la apuesta que echó para ese post
  (publicaciones/capturas/<id del post>.jpg), en Telegram y Threads va su captura sin tocar con una franja
  nuestra encima «✔ ACERTADO» (no tapa nada del boleto). Nunca se cambia nada del boleto.
Los verdes no salen solos: el bot se los manda a Marcos y solo se publican cuando él le da a «✅ Publicar».
"""
import base64
import html
import re

from bot import DATOS, RAIZ, leer
from marca import CIRCULO

MEDIA = RAIZ / "publicaciones" / "media"
CAPTURAS = RAIZ / "publicaciones" / "capturas"
ESCUDOS = MEDIA / "escudos"


def fem(t):
    return re.sub(r"(?<=[A-Za-zÀ-ÿ]) W(?=[\s–\-,.)!]|$)", " (fem.)", t or "")


def num(c):
    return f"{c:.2f}".replace(".", ",")


def escudo_b64(team_id):
    f = ESCUDOS / f"{team_id}.png"
    return base64.b64encode(f.read_bytes()).decode() if team_id and f.exists() else None


def equipos(partido_id):
    pa = (leer(DATOS / "proximos" / f"{partido_id}.json", {}) or {}).get("partido") or {}
    t = pa.get("teams") or {}
    return (t.get("home") or {}).get("id"), (t.get("away") or {}).get("id")


def marcador(x):
    m = x.get("marcador")
    return f"{m[0]}–{m[1]}" if isinstance(m, list) and len(m) == 2 and None not in m else ""


def documento(p, publicado, alto=1350):
    """p: la combi de docs/datos.json (publicados_hoy) ya en verde. publicado: «HH:MM».
    11/11: plantillas nuevas (fotos.py): un partido → tarjeta con escudos, marcador y sello ACERTADO; varios → lista."""
    import fotos
    patas = [x for x in p.get("picks", []) if x.get("estado") in ("verde", "anulada")]
    partidos = {x.get("partido_id") for x in patas}
    cuota = num(p["cuota"]) if p.get("cuota") else None
    if len(patas) == 1 and len(partidos) == 1 and patas[0].get("partido_id"):
        t = fotos.partido({"sel": [f"{patas[0]['partido_id']}|x|x"]})
        if t:
            return fotos.verde_partido(t, patas[0], cuota, publicado, t.get("liga"), alto)
    titulo = "PICK ACERTADO" if len(patas) == 1 else "COMBI ACERTADA"
    return fotos.verde_lista(patas, titulo, cuota, publicado, alto)


def ticket(pagina, p, publicado, destino, alto=1350):
    pagina.set_viewport_size({"width": 1080, "height": alto})
    pagina.goto("about:blank")
    pagina.set_content(documento(p, publicado, alto))
    pagina.wait_for_timeout(200)
    destino.parent.mkdir(parents=True, exist_ok=True)
    pagina.screenshot(path=str(destino), type="jpeg", quality=92, full_page=True)
    return destino


def sello(captura, destino):
    """La captura de Marcos tal cual (no se tapa nada) con una franja de Combilocas encima: «✔ ACERTADO»."""
    from PIL import Image, ImageDraw, ImageFont
    im = Image.open(captura).convert("RGB")
    w, h = im.size
    banda = max(int(w * 0.16), 120)
    out = Image.new("RGB", (w, h + banda), (11, 26, 18))
    out.paste(im, (0, banda))
    d = ImageDraw.Draw(out)
    d.rectangle([0, 0, w, banda - 1], fill=(10, 20, 64))
    d.rectangle([0, banda - max(4, w // 150), w, banda - 1], fill=(242, 201, 76))
    negrita = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
    f1 = ImageFont.truetype(negrita, int(banda * 0.42))
    f2 = ImageFont.truetype(negrita, int(banda * 0.17))
    izq = int(banda * 1.1) if CIRCULO.exists() else 0   # 11/11: el texto a la derecha del logo, sin pisarlo
    for texto, f, y, color in (("✔ ACERTADO", f1, banda * 0.14, (62, 224, 122)),
                               ("C O M B I L O C A S", f2, banda * 0.66, (242, 201, 76))):
        d.text((izq + (w - izq - d.textlength(texto, font=f)) / 2, y), texto, font=f, fill=color)
    if CIRCULO.exists():   # 11/11: el logo redondo a la izquierda de la franja
        lado = int(banda * 0.8)
        logo = Image.open(CIRCULO).convert("RGBA").resize((lado, lado), Image.LANCZOS)
        out.paste(logo, (max(10, int(banda * 0.15)), (banda - lado) // 2), logo)
    destino.parent.mkdir(parents=True, exist_ok=True)
    out.save(destino, "JPEG", quality=92)
    return destino
