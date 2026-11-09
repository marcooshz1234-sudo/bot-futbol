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
    """p: la combi de docs/datos.json (publicados_hoy) ya en verde. publicado: «HH:MM»."""
    patas = [x for x in p.get("picks", []) if x.get("estado") in ("verde", "anulada")]
    partidos = {x.get("partido_id") for x in patas}
    uno = len(partidos) == 1
    titulo = "PICK ACERTADO" if len(patas) == 1 else "COMBI ACERTADA"
    cab = ""
    if uno:
        l, v = equipos(next(iter(partidos)))
        el, ev = escudo_b64(l), escudo_b64(v)
        if el and ev:
            cab = (f'<div class="esc"><img src="data:image/png;base64,{el}"><span>vs</span>'
                   f'<img src="data:image/png;base64,{ev}"></div>')
        else:
            cab = f'<div class="partido">{html.escape(fem(patas[0].get("partido", "")))}</div>'
    filas = ""
    for x in patas:
        anul = x.get("estado") == "anulada"
        extra = "" if uno else f'<small>{html.escape(fem(x.get("partido", "")))} · {marcador(x)}</small>'
        filas += (f'<div class="pata{" anul" if anul else ""}"><b>{"⏸️" if anul else "✅"}</b>'
                  f'<div>{html.escape(fem(x.get("texto", "")))}{" (no se jugó)" if anul else ""}{extra}</div></div>')
    datos = [("Cuota", num(p["cuota"]) if p.get("cuota") else "—"), ("Publicado", publicado or "—")]
    if uno and marcador(patas[0]):
        datos.append(("Final", marcador(patas[0])))
    cajas = "".join(f"<div>{a}<b>{b}</b></div>" for a, b in datos)
    letra = 40 if len(patas) <= 3 else 32 if len(patas) <= 5 else 26
    return f"""<html><head><meta charset="utf-8"><style>
body{{margin:0;width:1080px;height:{alto}px;font-family:Arial,'Noto Color Emoji',sans-serif;color:#fff;
background:linear-gradient(160deg,#14532d,#0b1a12 60%);display:flex;flex-direction:column;justify-content:center;
box-sizing:border-box;padding:70px;border:8px solid #22c55e}}
.m{{color:#86efac;letter-spacing:12px;font-weight:bold;font-size:30px;text-align:center}}
.big{{font-size:86px;font-weight:900;text-align:center;margin:24px 0 10px;color:#22c55e;line-height:1}}
.esc{{display:flex;justify-content:center;align-items:center;gap:50px;margin:40px 0;font-size:40px;font-weight:bold}}
.esc img{{height:170px}}.partido{{text-align:center;font-size:40px;font-weight:bold;margin:34px 0}}
.pata{{display:flex;gap:18px;align-items:flex-start;background:#ffffff14;border-radius:18px;padding:20px 26px;
margin:12px 0;font-size:{letra}px;font-weight:bold}}.pata small{{display:block;font-size:24px;color:#cbd5e1;
font-weight:normal;margin-top:6px}}.anul{{opacity:.55}}
.q{{display:flex;justify-content:space-around;margin-top:40px;font-size:30px;color:#cbd5e1;text-align:center}}
.q b{{display:block;font-size:56px;color:#fff;margin-top:8px}}
.pie{{text-align:center;margin-top:50px;font-size:28px;color:#86efac}}
</style></head><body><div class="m">COMBILOCAS</div><div class="big">✅ {titulo}</div>{cab}{filas}
<div class="q">{cajas}</div><div class="pie">🔔 Activad las notificaciones, que vienen más combis 👀</div></body></html>"""


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
    d.rectangle([0, 0, w, banda - 1], fill=(20, 83, 45))
    d.rectangle([0, banda - max(4, w // 150), w, banda - 1], fill=(34, 197, 94))
    negrita = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
    f1 = ImageFont.truetype(negrita, int(banda * 0.42))
    f2 = ImageFont.truetype(negrita, int(banda * 0.17))
    for texto, f, y, color in (("✔ ACERTADO", f1, banda * 0.14, (255, 255, 255)),
                               ("C O M B I L O C A S", f2, banda * 0.66, (134, 239, 172))):
        d.text(((w - d.textlength(texto, font=f)) / 2, y), texto, font=f, fill=color)
    destino.parent.mkdir(parents=True, exist_ok=True)
    out.save(destino, "JPEG", quality=92)
    return destino
