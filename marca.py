"""11/11 (Marcos: «metelo en todo» / «todo con este formato nuevo, que se parezca al logo»).
Estilo común de TODAS las fotos del bot, sacado del logo: estadio de noche (cielo azul marino, focos, atardecer
naranja en el horizonte, césped), oro metálico, bandas azul marino con borde dorado y el trébol verde.

Archivos en publicaciones/media/marca/: logo_completo.png (cuadrado, con estadio), logo_circulo.png (redondo,
transparente), logo_circulo_256.png (el que se incrusta) y fuentes/ (Barlow Condensed, licencia OFL).
"""
import base64
from functools import lru_cache
from pathlib import Path

CARPETA = Path(__file__).resolve().parent / "publicaciones" / "media" / "marca"
# 11/11 05:04 (Marcos): estilo «CL» verde neón (logo CL COMBILOCAS + estadio de noche de verdad), hecho con ChatGPT.
# TEMA = "oro" vuelve al estilo anterior (logo de la corona, oro y azul marino).
TEMA = "cl"
CIRCULO = CARPETA / ("logo_cl_256.png" if TEMA == "cl" else "logo_circulo_256.png")
LOGO_GRANDE = CARPETA / ("logo_cl_512.png" if TEMA == "cl" else "logo_circulo_256.png")
FONDO_FOTO = CARPETA / "fondo_estadio.jpg"
NEON = "#7ef03a"
DISENO = "diseño-5"   # va en la huella de las imágenes (imagenes.huella / redes.url_media): cambiarla rehace las pendientes
FUENTES = CARPETA / "fuentes"

ORO = "#f2c94c"
ORO_OSCURO = "#b8862b"
MARINO = "#0a1440"
VERDE = "#3ee07a"
LETRA = "'Barlow Condensed','Arial Narrow','Liberation Sans',sans-serif,'Noto Color Emoji'"


@lru_cache(maxsize=1)
def logo_b64():
    return base64.b64encode(LOGO_GRANDE.read_bytes()).decode() if LOGO_GRANDE.exists() else None


def logo_img(alto, clase="logo"):
    """<img> del logo redondo, o el nombre en letras si falta el archivo."""
    b = logo_b64()
    if not b:
        return f'<span class="oro" style="font-size:{alto // 2}px">COMBILOCAS</span>'
    return (f'<img class="{clase}" src="data:image/png;base64,{b}" alt="Combilocas" '
            f'style="height:{alto}px;width:{alto}px;display:block;margin:0 auto;'
            f'filter:drop-shadow(0 8px 18px rgba(0,0,0,.6)) drop-shadow(0 0 22px {"rgba(126,240,58,.35)" if TEMA == "cl" else "rgba(242,201,76,.35)"})">')


@lru_cache(maxsize=1)
def fuentes_css():
    out = []
    for archivo, peso, estilo in (("BarlowCondensed-BlackItalic", 900, "italic"),
                                  ("BarlowCondensed-ExtraBoldItalic", 800, "italic"),
                                  ("BarlowCondensed-Bold", 700, "normal"),
                                  ("BarlowCondensed-SemiBold", 600, "normal")):
        f = FUENTES / f"{archivo}.ttf"
        if f.exists():
            out.append(f"@font-face{{font-family:'Barlow Condensed';font-weight:{peso};font-style:{estilo};"
                       f"src:url(data:font/ttf;base64,{base64.b64encode(f.read_bytes()).decode()}) format('truetype')}}")
    return "".join(out)


def _svg(s):
    return "url(\"data:image/svg+xml;base64," + base64.b64encode(s.encode()).decode() + "\")"


# torre de focos (como las del logo)
FOCO = _svg('<svg xmlns="http://www.w3.org/2000/svg" width="150" height="230" viewBox="0 0 150 230">'
            '<rect x="70" y="80" width="10" height="150" fill="#1b2556"/>'
            '<rect x="12" y="8" width="126" height="78" rx="8" fill="#16204d" stroke="#3b4c99" stroke-width="4"/>'
            + "".join(f'<circle cx="{32 + 29 * c}" cy="{28 + 32 * f}" r="11" fill="#fffbe6"/>'
                      for f in range(2) for c in range(4)) + '</svg>')
TREBOL = ('<svg viewBox="0 0 120 150" width="{t}" height="{t2}" style="{e}"><g stroke="#053a15" stroke-width="5" '
          'fill="#2fd36a"><circle cx="60" cy="34" r="26"/><circle cx="34" cy="60" r="26"/><circle cx="86" cy="60" r="26"/>'
          '<circle cx="60" cy="86" r="26"/></g><circle cx="60" cy="60" r="10" fill="#a8ffbf"/>'
          '<path d="M62 104 Q70 128 88 144" stroke="#053a15" stroke-width="9" fill="none" stroke-linecap="round"/></svg>')


def trebol(t=60, estilo=""):
    return TREBOL.format(t=t, t2=int(t * 1.25), e=estilo)


def fondo(alto, verde=False):
    """CSS del lienzo (en <html>): estadio de noche con focos, gradas iluminadas, atardecer y césped a rayas,
    y el aro dorado del logo alrededor. verde=True: más brillo verde (fotos de acierto)."""
    cesped = int(alto * 0.22)
    brillo = "rgba(62,224,122,.30)" if verde else "rgba(255,138,40,.30)"
    capas = [
        f"{FOCO} left 18px top 40px/150px 230px no-repeat",
        f"{FOCO} right 18px top 40px/150px 230px no-repeat",
        "radial-gradient(ellipse 30% 14% at 10% 6%,rgba(255,250,215,.55),transparent 70%) no-repeat",
        "radial-gradient(ellipse 30% 14% at 90% 6%,rgba(255,250,215,.55),transparent 70%) no-repeat",
        "repeating-conic-gradient(from 0deg at 50% -12%,rgba(255,255,255,.055) 0deg 4deg,transparent 4deg 14deg) no-repeat",
        f"repeating-linear-gradient(90deg,rgba(255,255,255,.06) 0 90px,transparent 90px 180px) bottom/100% {cesped}px no-repeat",
        f"linear-gradient(180deg,#1f8a3c,#0f5a24 55%,#08361a) bottom/100% {cesped}px no-repeat",
        f"radial-gradient(ellipse 80% 12% at 50% {100 - 100 * cesped / alto:.0f}%,{brillo},transparent 70%) no-repeat",
        f"radial-gradient(circle,rgba(255,214,140,.55) 1.6px,transparent 2.6px) 0 {alto - cesped - 70}px/22px 13px repeat-x",
        f"radial-gradient(circle,rgba(255,214,140,.35) 1.4px,transparent 2.4px) 11px {alto - cesped - 50}px/22px 13px repeat-x",
        f"linear-gradient(180deg,#0a1440 0%,#13205a 38%,#241a4a 60%,#2a1a2c {100 - 100 * cesped / alto:.0f}%,#0f5a24 100%)",
    ]
    return (f"html{{position:relative;min-height:{alto}px;background:{','.join(capas)};"
            f"-webkit-print-color-adjust:exact}}"
            f"html::after{{content:'';position:absolute;inset:14px;border:5px solid {ORO};border-radius:34px;"
            "box-shadow:0 0 0 3px rgba(0,0,0,.45),inset 0 0 0 3px rgba(0,0,0,.4),0 0 24px rgba(242,201,76,.35);"
            "pointer-events:none;z-index:50}")


CLASES = f"""
.oro{{font-family:{LETRA};font-weight:900;font-style:italic;color:#ffd84a;
 background:linear-gradient(180deg,#fff6c2 0%,#ffd84a 45%,#e59b0c 100%);-webkit-background-clip:text;background-clip:text;
 -webkit-text-fill-color:transparent;-webkit-text-stroke:2px #5a2a00;filter:drop-shadow(0 5px 0 #2a0f00)}}
.b3d{{font-family:{LETRA};font-weight:900;font-style:italic;color:#fff;-webkit-text-stroke:2.5px #0b1550;
 filter:drop-shadow(0 5px 0 #06103a)}}
.v3d{{font-family:{LETRA};font-weight:900;font-style:italic;color:{VERDE};-webkit-text-stroke:3px #053a15;
 filter:drop-shadow(0 5px 0 #021f0b) drop-shadow(0 0 18px rgba(62,224,122,.45))}}
.banda{{display:inline-block;padding:10px 60px 14px;background:linear-gradient(180deg,#1a2c78,#0a1440 60%,#050b26);
 border:5px solid {ORO};border-radius:16px;box-shadow:0 8px 0 #050b26,0 0 30px rgba(242,201,76,.35),inset 0 2px 0 rgba(255,255,255,.25)}}
.card{{background:linear-gradient(180deg,rgba(22,36,110,.92),rgba(8,16,52,.92));border:4px solid {ORO};border-radius:24px;
 box-shadow:0 0 26px rgba(242,201,76,.25),inset 0 2px 0 rgba(255,255,255,.2)}}
.pastilla{{display:inline-flex;align-items:center;justify-content:center;border-radius:18px;padding:6px 30px;
 background:linear-gradient(180deg,#fff3b0,#ffd84a 45%,#d99a10);border:4px solid #fff6d0;color:{MARINO};
 font-family:{LETRA};font-weight:900;font-style:italic;box-shadow:0 6px 0 #6b4a10,0 0 22px rgba(242,201,76,.6)}}
.escudo{{display:flex;align-items:center;justify-content:center}}
.escudo img{{width:100%;height:100%;object-fit:contain;filter:drop-shadow(0 6px 10px rgba(0,0,0,.6)) drop-shadow(0 0 2px rgba(255,255,255,.5))}}
.escudo b{{font-family:{LETRA};font-weight:900;color:#fff;-webkit-text-stroke:2px #0b1550}}
"""


@lru_cache(maxsize=1)
def _fondo_b64():
    return base64.b64encode(FONDO_FOTO.read_bytes()).decode() if FONDO_FOTO.exists() else None


def fondo_cl(alto, verde=False):
    """Estilo CL: la foto del estadio de noche, oscurecida arriba y abajo para que se lea todo."""
    b = _fondo_b64()
    foto = f",url(data:image/jpeg;base64,{b}) center top/cover no-repeat" if b else ""
    brillo = "rgba(126,240,58,.16)" if verde else "rgba(126,240,58,.07)"
    return (f"html{{position:relative;min-height:{alto}px;background:"
            f"radial-gradient(ellipse 70% 40% at 50% 62%,{brillo},transparent 70%),"
            "linear-gradient(180deg,rgba(0,0,0,.35) 0%,rgba(0,0,0,.42) 30%,rgba(0,0,0,.30) 60%,rgba(0,0,0,.55) 100%)"
            f"{foto},#050806;-webkit-print-color-adjust:exact}}")


CLASES_CL = f"""
.oro{{font-family:{LETRA};font-weight:900;font-style:italic;color:#fff;text-shadow:0 4px 0 rgba(0,0,0,.55),0 0 18px rgba(0,0,0,.6)}}
.b3d{{font-family:{LETRA};font-weight:900;font-style:italic;color:#fff;text-shadow:0 3px 0 rgba(0,0,0,.6),0 0 12px rgba(0,0,0,.6)}}
.v3d,.neon{{font-family:{LETRA};font-weight:900;font-style:italic;color:{NEON};text-shadow:0 3px 0 rgba(0,0,0,.6),0 0 18px rgba(126,240,58,.45)}}
.banda{{display:inline-block;position:relative;padding:0 30px 22px}}
.banda:after{{content:"";position:absolute;left:12%;right:12%;bottom:0;height:8px;border-radius:8px;
 background:linear-gradient(90deg,transparent,{NEON} 25%,#d6ff6a 50%,{NEON} 75%,transparent);box-shadow:0 0 14px rgba(126,240,58,.7)}}
.card{{background:linear-gradient(180deg,rgba(14,18,14,.9),rgba(4,6,4,.9));border:3px solid {NEON};border-radius:20px;
 box-shadow:0 0 22px rgba(126,240,58,.35),inset 0 1px 0 rgba(255,255,255,.12)}}
.pastilla{{display:inline-flex;align-items:center;justify-content:center;border-radius:16px;padding:6px 30px;
 background:linear-gradient(180deg,#b6ff6e,#7ef03a 50%,#4fc21a);border:none;color:#071a02;
 font-family:{LETRA};font-weight:900;font-style:italic;box-shadow:0 0 24px rgba(126,240,58,.55)}}
.escudo{{display:flex;align-items:center;justify-content:center}}
.escudo img{{width:100%;height:100%;object-fit:contain;filter:drop-shadow(0 6px 10px rgba(0,0,0,.7))}}
.escudo b{{font-family:{LETRA};font-weight:900;color:#fff}}
.brocha{{display:inline-block;padding:18px 70px;background:linear-gradient(180deg,#b6ff6e,#7ef03a 55%,#55c91c);
 clip-path:polygon(2% 18%,7% 8%,30% 12%,55% 4%,80% 10%,97% 2%,99% 30%,96% 55%,100% 80%,93% 95%,70% 88%,45% 96%,20% 90%,4% 98%,0% 70%,3% 45%);
 transform:rotate(-3deg);filter:drop-shadow(0 0 16px rgba(126,240,58,.5))}}
.brocha span{{font-family:{LETRA};font-weight:900;font-style:italic;color:#06140a;line-height:1}}
.nombre{{display:inline-block;padding:8px 26px;border:3px solid {NEON};border-radius:12px;transform:skewX(-10deg);
 background:rgba(4,6,4,.85);box-shadow:0 0 14px rgba(126,240,58,.35)}}
.nombre>*{{transform:skewX(10deg)}}
"""


def base(alto, verde=False):
    """<style> común: fuentes, lienzo de estadio y clases."""
    if TEMA == "cl":
        return fuentes_css() + fondo_cl(alto, verde) + CLASES_CL
    return fuentes_css() + fondo(alto, verde) + CLASES
