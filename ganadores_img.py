"""
05/11 (Marcos, viendo los «WINNERS» de otra cuenta que funcionan muy bien): imagen de «ganadores» con escudos,
con varias plantillas con detalle (no todo redondo): «oro» (marco dorado con coronas y esquinas diagonales) y
«noche» (estadio de noche, filas en diagonal y verde neón). Letras de Google Fonts (publicaciones/fuentes, OFL).

    filas = [{"bandera": "🇵🇹", "escudo": "<ruta png>", "nombre": "Benfica", "pick": "GANA", "ok": None|True|False}]
    generar(filas, titulo, salida, plantilla="oro")
"""
import base64
import html
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
FUENTES = RAIZ / "publicaciones" / "fuentes"


def _fuente(nombre, archivo):
    b = base64.b64encode((FUENTES / archivo).read_bytes()).decode()
    return f"@font-face{{font-family:'{nombre}';src:url(data:font/ttf;base64,{b});}}"


def _img(ruta):
    p = Path(ruta)
    if not p.exists():
        return '<div class="esc"></div>'
    return f'<img class="esc" src="data:image/png;base64,{base64.b64encode(p.read_bytes()).decode()}">'


CORONA = """<svg viewBox="0 0 120 110" class="{c}"><defs><linearGradient id="g{i}" x1="0" y1="0" x2="1" y2="1">
<stop offset="0" stop-color="#fff3c4"/><stop offset=".35" stop-color="#f0c24b"/><stop offset=".6" stop-color="#b8860b"/>
<stop offset="1" stop-color="#ffe08a"/></linearGradient></defs>
<path d="M8 92 L14 30 L38 58 L60 12 L82 58 L106 30 L112 92 Z" fill="url(#g{i})" stroke="#8a6508" stroke-width="3"/>
<rect x="6" y="90" width="108" height="14" rx="3" fill="url(#g{i})" stroke="#8a6508" stroke-width="3"/>
<circle cx="14" cy="28" r="7" fill="#fff3c4" stroke="#8a6508" stroke-width="2"/><circle cx="60" cy="10" r="8" fill="#fff3c4" stroke="#8a6508" stroke-width="2"/>
<circle cx="106" cy="28" r="7" fill="#fff3c4" stroke="#8a6508" stroke-width="2"/></svg>"""

ESTRELLA = """<svg viewBox="0 0 40 40" class="estrella"><path d="M20 0 L25 15 L40 20 L25 25 L20 40 L15 25 L0 20 L15 15 Z"
fill="#e3a71b" stroke="#8a6508" stroke-width="1.5"/></svg>"""


def _logo(lado):
    """05/11 (Marcos: «quita las coronas y pon algo que nos represente»): el logo de Combilocas en un aro dorado."""
    b = base64.b64encode((RAIZ / "docs" / "logo.png").read_bytes()).decode()
    return f'<div class="logo {lado}"><img src="data:image/png;base64,{b}"></div>'


def html_oro(filas, titulo):
    css = _fuente("Anton", "Anton-Regular.ttf") + _fuente("Oswald", "Oswald[wght].ttf") + _fuente("Cinzel", "Cinzel[wght].ttf") + """
body{margin:0;width:1350px;height:1000px;overflow:hidden;position:relative;font-family:Oswald;
 background:radial-gradient(ellipse at 50% 45%,#ffffff 0%,#fff9ea 45%,#f3dfae 100%)}
.rayos{position:absolute;inset:0;background:repeating-conic-gradient(from 0deg at 50% 50%,rgba(255,215,120,.16) 0 6deg,transparent 6deg 14deg)}
.esq{position:absolute;width:420px;height:70px;background:linear-gradient(90deg,#7a5300,#f6d46a 30%,#fff6cf 50%,#d39b1a 70%,#7a5300)}
.esq.b{height:22px;background:linear-gradient(90deg,#3a2700,#c8920e,#3a2700)}
.tl{top:40px;left:-120px;transform:rotate(-38deg)} .tl.b{top:130px;left:-140px}
.tr{top:40px;right:-120px;transform:rotate(38deg)} .tr.b{top:130px;right:-140px}
.bl{bottom:40px;left:-120px;transform:rotate(38deg)} .bl.b{bottom:130px;left:-140px}
.br{bottom:40px;right:-120px;transform:rotate(-38deg)} .br.b{bottom:130px;right:-140px}
.marco{position:absolute;inset:14px;border:4px solid #d4a017;border-radius:34px;box-shadow:inset 0 0 0 3px #fff3c4,inset 0 0 40px rgba(212,160,23,.5)}
.logo{position:absolute;top:410px;width:150px;height:150px;border-radius:50%;padding:7px;
 background:conic-gradient(#7a5300,#fff3c4,#d4a017,#7a5300,#ffe58a,#a66f00,#7a5300);box-shadow:0 6px 18px rgba(120,80,0,.45)}
.logo img{width:100%;height:100%;border-radius:50%;display:block} .logo.izq{left:42px} .logo.der{right:42px}
.linea{position:absolute;left:300px;right:300px;height:0;border-top:3px dashed #d4a017}
.linea.t{top:58px} .linea.bo{bottom:58px}
.estrella{position:absolute;width:44px;left:653px} .estrella.t{top:36px} .estrella.bo{bottom:36px}
.titulo{position:absolute;top:84px;left:0;right:0;text-align:center;font-family:Cinzel;font-weight:900;font-size:40px;
 letter-spacing:6px;color:#7a5300;text-shadow:0 1px 0 #fff}
.lista{position:absolute;top:146px;left:230px;right:230px}
.f{display:flex;align-items:center;height:82px;margin-bottom:8px;position:relative}
.f:before{content:"";position:absolute;left:40px;right:0;top:6px;bottom:6px;border-radius:40px;
 background:linear-gradient(180deg,#ffffff,#f7f1e3);box-shadow:0 4px 14px rgba(120,80,0,.25),inset 0 0 0 2px #f0d58a}
.n{position:relative;z-index:1;width:120px;height:72px;transform:skewX(-18deg);border-radius:12px 4px 4px 12px;
 background:linear-gradient(180deg,#ffe58a,#e3a71b 55%,#a66f00);box-shadow:0 3px 0 #7a5300;display:flex;align-items:center;justify-content:flex-start}
.n span{transform:skewX(18deg);font-family:Anton;font-size:44px;color:#fff;text-shadow:0 3px 0 #7a5300;margin-left:20px}
.fl{position:relative;z-index:1;width:84px;height:56px;margin-left:-22px;transform:skewX(-18deg);background:#fff;border:3px solid #d4a017;
 border-radius:6px;display:flex;align-items:center;justify-content:center;overflow:hidden}
.fl span{transform:skewX(18deg);font-size:46px;line-height:1}
.esc{position:relative;z-index:1;width:92px;height:92px;object-fit:contain;margin:-6px 10px -6px 18px;filter:drop-shadow(0 3px 4px rgba(0,0,0,.25))}
.nom{position:relative;z-index:1;flex:1;font-weight:700;font-size:36px;color:#16223f;text-align:center}
.flecha{position:relative;z-index:1;font-family:Anton;color:#e39a00;font-size:42px;margin-right:12px}
.pick{position:relative;z-index:1;display:flex;align-items:center;gap:12px;height:62px;padding:0 28px 0 10px;border-radius:34px;
 background:linear-gradient(180deg,#ffe58a,#e3a71b 55%,#a66f00);box-shadow:0 3px 0 #7a5300,inset 0 0 0 2px #fff3c4}
.pick b{font-family:Anton;font-size:36px;color:#fff;text-shadow:0 2px 0 #7a5300;letter-spacing:1px}
.ck{width:42px;height:42px;border-radius:50%;border:4px solid #fff;display:flex;align-items:center;justify-content:center;color:#fff;font-size:26px;font-weight:900}
.ok .pick{background:linear-gradient(180deg,#8ff0a8,#22b14c 55%,#0d6b2a);box-shadow:0 3px 0 #0a4d1e}
.ko .pick{background:linear-gradient(180deg,#ff9a8a,#d63a2a 55%,#8a1a10);box-shadow:0 3px 0 #5e0f08}
.pie{position:absolute;bottom:98px;left:0;right:0;text-align:center;font-family:Cinzel;font-weight:900;font-size:24px;letter-spacing:8px;color:#a66f00}
"""
    lis = ""
    for i, f in enumerate(filas, 1):
        cls = " ok" if f.get("ok") is True else " ko" if f.get("ok") is False else ""
        marca = "✓" if f.get("ok") is not False else "✕"
        lis += (f'<div class="f{cls}"><div class="n"><span>{i}.</span></div><div class="fl"><span>{f["bandera"]}</span></div>'
                f'{_img(f["escudo"])}<div class="nom">{html.escape(f["nombre"])}</div><div class="flecha">➜</div>'
                f'<div class="pick"><div class="ck">{marca}</div><b>{html.escape(f["pick"])}</b></div></div>')
    deco = ('<div class="rayos"></div>' + "".join(f'<div class="esq {p}"></div><div class="esq b {p}"></div>' for p in ("tl", "tr", "bl", "br"))
            + '<div class="marco"></div>' + _logo("izq") + _logo("der")
            + '<div class="linea t"></div><div class="linea bo"></div>' + ESTRELLA.replace('class="estrella"', 'class="estrella t"')
            + ESTRELLA.replace('class="estrella"', 'class="estrella bo"'))
    return (f"<html><head><meta charset='utf-8'><style>{css}</style></head><body>{deco}"
            f"<div class='titulo'>{html.escape(titulo)}</div><div class='lista'>{lis}</div><div class='pie'>@COMBILOCAS</div></body></html>")


def html_noche(filas, titulo):
    css = _fuente("Bebas", "BebasNeue-Regular.ttf") + _fuente("Teko", "Teko[wght].ttf") + _fuente("Russo", "RussoOne-Regular.ttf") + """
body{margin:0;width:1080px;height:1350px;overflow:hidden;position:relative;font-family:Teko;color:#fff;
 background:linear-gradient(180deg,#05110b 0%,#0b2a18 55%,#05110b 100%)}
.cesped{position:absolute;inset:0;background:repeating-linear-gradient(90deg,rgba(46,204,113,.05) 0 90px,transparent 90px 180px)}
.foco{position:absolute;top:-120px;width:520px;height:900px;background:linear-gradient(180deg,rgba(220,255,230,.28),transparent 70%);
 clip-path:polygon(45% 0,55% 0,100% 100%,0 100%)}
.foco.a{left:-160px;transform:rotate(-22deg)} .foco.b{right:-160px;transform:rotate(22deg)}
.marco{position:absolute;inset:22px;border:3px solid #2ecc71;
 clip-path:polygon(60px 0,100% 0,100% calc(100% - 60px),calc(100% - 60px) 100%,0 100%,0 60px)}
.cor{position:absolute;width:150px;height:150px;border:10px solid #2ecc71}
.cor.tl{top:22px;left:22px;border-right:none;border-bottom:none} .cor.br{bottom:22px;right:22px;border-left:none;border-top:none}
.titulo{position:absolute;top:60px;left:0;right:0;text-align:center;font-family:Bebas;font-size:110px;letter-spacing:4px;line-height:1;
 color:#fff;text-shadow:0 0 18px rgba(46,204,113,.8)}
.sub{position:absolute;top:172px;left:0;right:0;text-align:center;font-family:Russo;font-size:30px;letter-spacing:10px;color:#2ecc71}
.lista{position:absolute;top:250px;left:70px;right:70px}
.f{display:flex;align-items:center;height:108px;margin-bottom:14px;transform:skewX(-10deg);
 background:linear-gradient(90deg,rgba(46,204,113,.28),rgba(10,40,24,.9) 40%);border-left:10px solid #2ecc71}
.f>*{transform:skewX(10deg)}
.n{font-family:Bebas;font-size:96px;width:100px;text-align:center;color:transparent;-webkit-text-stroke:3px #2ecc71}
.fl{font-size:48px;margin:0 16px}
.esc{width:76px;height:76px;object-fit:contain;margin-right:18px;filter:drop-shadow(0 0 6px rgba(255,255,255,.35))}
.nom{flex:1;font-weight:600;font-size:54px;letter-spacing:1px;text-transform:uppercase}
.pick{font-family:Russo;font-size:30px;color:#05110b;background:#2ecc71;padding:14px 26px;margin-right:20px;
 clip-path:polygon(14px 0,100% 0,calc(100% - 14px) 100%,0 100%)}
.ok .pick{background:#7CFF9E} .ko .pick{background:#ff5c4d}
.pie{position:absolute;bottom:52px;left:0;right:0;text-align:center;font-family:Russo;font-size:28px;letter-spacing:10px;color:#2ecc71}
"""
    lis = ""
    for i, f in enumerate(filas, 1):
        cls = " ok" if f.get("ok") is True else " ko" if f.get("ok") is False else ""
        marca = "✅ " if f.get("ok") is True else "❌ " if f.get("ok") is False else ""
        lis += (f'<div class="f{cls}"><div class="n">{i}</div><div class="fl">{f["bandera"]}</div>{_img(f["escudo"])}'
                f'<div class="nom">{html.escape(f["nombre"])}</div><div class="pick">{marca}{html.escape(f["pick"])}</div></div>')
    return (f"<html><head><meta charset='utf-8'><style>{css}</style></head><body><div class='cesped'></div>"
            f"<div class='foco a'></div><div class='foco b'></div><div class='marco'></div><div class='cor tl'></div><div class='cor br'></div>"
            f"<div class='titulo'>{html.escape(titulo)}</div><div class='sub'>GANADORES · COMBILOCAS</div>"
            f"<div class='lista'>{lis}</div><div class='pie'>@COMBILOCAS 🍀</div></body></html>")


PLANTILLAS = {"oro": (html_oro, (1350, 1000)), "noche": (html_noche, (1080, 1350))}


def generar(filas, titulo, salida, plantilla="oro"):
    from playwright.sync_api import sync_playwright
    hacer, (w, h) = PLANTILLAS[plantilla]
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={"width": w, "height": h})
        pg.set_content(hacer(filas, titulo))
        pg.wait_for_timeout(800)
        pg.screenshot(path=str(salida), type="jpeg", quality=92)
        b.close()
    return salida
