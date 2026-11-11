"""11/11 (Marcos: «todo el contenido con este formato nuevo, con el logo nuevo»): las plantillas de foto con la
pinta del logo (estadio de noche, oro, bandas azul marino, trébol). El estilo común está en marca.py.

- pick_del_dia(p, w, h): el pick suelto (un partido): escudos, VS, pick con su cuota y stake.
- verde_partido(...) / verde_lista(...): el acierto (sello «✓ ACERTADO» encima del pick, marcador final).
- tarjeta_partido(...): la foto apaisada del partido (combis de un partido, Threads y Telegram).
- quien_gana(filas, titulo): «GANADORES» / quién gana hoy.
No se inventa nada: equipos, hora y cuota salen del post y de los datos del partido.
"""
import base64
import html
import re
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from marca import LETRA, ORO, base, logo_img, trebol

RAIZ = Path(__file__).resolve().parent
ESCUDOS = RAIZ / "publicaciones" / "media" / "escudos"
MADRID = ZoneInfo("Europe/Madrid")
DIAS = ["LUNES", "MARTES", "MIÉRCOLES", "JUEVES", "VIERNES", "SÁBADO", "DOMINGO"]
e = html.escape


def fem(t):
    return re.sub(r"(?<=[A-Za-zÀ-ÿ]) W(?=[\s–\-,.)!]|$)", " (fem.)", t or "")


CORTOS = {"MANCHESTER CITY": "MAN. CITY", "MANCHESTER UNITED": "MAN. UNITED", "BORUSSIA DORTMUND": "DORTMUND",
          "BORUSSIA MÖNCHENGLADBACH": "M'GLADBACH", "PARIS SAINT GERMAIN": "PSG", "PARIS SAINT-GERMAIN": "PSG",
          "BAYER LEVERKUSEN": "LEVERKUSEN", "NOTTINGHAM FOREST": "NOTT. FOREST", "WOLVERHAMPTON WANDERERS": "WOLVES"}


def mayus(t):
    return fem(t).upper()


def equipo(t):
    """Nombre de equipo para las fotos: en mayúsculas y abreviado si es muy largo (MAN. CITY (FEM.))."""
    n = mayus(t)
    for largo, corto in CORTOS.items():
        n = n.replace(largo, corto)
    return n


def nitido(f, lado):
    """11/11 (Marcos: «solo el escudo, más grande y nítido»): el PNG (150 px) ampliado al tamaño exacto con
    Lanczos y un poco de enfoque, mejor que dejar que lo estire el navegador."""
    import io
    from PIL import Image, ImageFilter
    try:
        im = Image.open(f).convert("RGBA")
        k = lado / max(im.size)
        if k > 1:
            im = im.resize((round(im.width * k), round(im.height * k)), Image.LANCZOS)
            im = im.filter(ImageFilter.UnsharpMask(radius=1.6, percent=90, threshold=2))
        b = io.BytesIO()
        im.save(b, "PNG")
        return base64.b64encode(b.getvalue()).decode()
    except Exception:
        return base64.b64encode(f.read_bytes()).decode()


def escudo(team_id=None, url=None, nombre="", lado=200):
    """Escudo dentro del círculo dorado. Guardado en escudos/<id>.png; si no está, se intenta bajar; si no, iniciales."""
    f = None
    if team_id and (ESCUDOS / f"{team_id}.png").exists():
        f = ESCUDOS / f"{team_id}.png"
    elif url:
        f = ESCUDOS / Path(url).name
        if not f.exists():
            try:
                import urllib.request
                ESCUDOS.mkdir(parents=True, exist_ok=True)
                f.write_bytes(urllib.request.urlopen(url, timeout=10).read())
            except Exception as ex:
                print(f"Escudo de {nombre}: {ex}")
                f = None
    dentro = (f'<img src="data:image/png;base64,{nitido(f, lado)}" alt="">' if f and f.exists()
              else f'<b style="font-size:{lado // 3}px">{e("".join(w[0] for w in (nombre or "?").split()[:2]).upper())}</b>')
    return f'<div class="escudo" style="width:{lado}px;height:{lado}px">{dentro}</div>'


def partido(p):
    """Equipos, escudos, hora y liga del (único) partido de un post, o None."""
    import json
    t = dict(p.get("tarjeta") or {})
    fid = None
    if p.get("sel"):
        fids = {str(s).split("|")[0] for s in p["sel"]}
        if len(fids) == 1:
            fid = fids.pop()
    if fid:
        for carpeta in ("proximos", "extra"):
            f = RAIZ / "datos" / carpeta / f"{fid}.json"
            if f.exists():
                try:
                    pa = json.loads(f.read_text(encoding="utf-8")).get("partido") or {}
                except Exception:
                    continue
                if pa.get("teams"):
                    h, a = pa["teams"]["home"], pa["teams"]["away"]
                    t.setdefault("local", h["name"])
                    t.setdefault("visitante", a["name"])
                    t.setdefault("id_l", h.get("id"))
                    t.setdefault("id_v", a.get("id"))
                    t.setdefault("logo_l", h.get("logo"))
                    t.setdefault("logo_v", a.get("logo"))
                    try:
                        ini = datetime.fromisoformat(pa["fixture"]["date"]).astimezone(MADRID)
                        t.setdefault("fecha", ini.strftime("%Y-%m-%dT%H:%M"))
                    except Exception:
                        pass
                    t.setdefault("liga", (pa.get("league") or {}).get("name"))
                    break
    if not (t.get("local") and t.get("visitante")):
        return None
    return t


def cuando(t, fecha_post):
    """«HOY · 21:00» / «MAÑANA · 18:30» / «SÁBADO · 16:00»."""
    try:
        ini = datetime.fromisoformat(t["fecha"])
        hoy = datetime.fromisoformat(fecha_post[:10]).date()
        d = (ini.date() - hoy).days
        return f"{'HOY' if d == 0 else 'MAÑANA' if d == 1 else DIAS[ini.weekday()]} · {ini:%H:%M}"
    except Exception:
        return ""


def _tam(texto, grande, ancho_letras):
    """Letra más pequeña si el nombre es largo."""
    n = len(texto)
    return grande if n <= ancho_letras else max(int(grande * ancho_letras / n), int(grande * .55))


# 11/11 (Marcos: «muy simple, antes tenía muchas cosas»): adornos alrededor, como la plantilla oro de antes
COPA = ('<svg viewBox="0 0 170 220" width="{w}" style="{e}"><path d="M40 20 H130 V70 C130 110 105 130 85 132 C65 130 40 110 40 70 Z" '
        'fill="url(#oroG)" stroke="#7a3d00" stroke-width="6"/><path d="M40 34 H14 C14 70 30 84 46 88 M130 34 H156 C156 70 140 84 124 88" '
        'fill="none" stroke="#ffd84a" stroke-width="10"/><rect x="74" y="132" width="22" height="34" fill="#e59b0c" stroke="#7a3d00" '
        'stroke-width="5"/><rect x="46" y="166" width="78" height="26" rx="4" fill="url(#oroG)" stroke="#7a3d00" stroke-width="6"/>'
        '<path d="M66 40 L66 90" stroke="#fff6c2" stroke-width="8" stroke-linecap="round"/>'
        '<defs><linearGradient id="oroG" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#fff3c4"/>'
        '<stop offset=".4" stop-color="#f0c24b"/><stop offset=".7" stop-color="#b8860b"/><stop offset="1" stop-color="#ffe08a"/>'
        '</linearGradient></defs></svg>')
LAUREL = ('<svg viewBox="0 0 60 600" width="60" height="{h}" preserveAspectRatio="none" style="{e}">'
          '<path d="M40 590 C10 450 10 150 40 10" fill="none" stroke="#e3a71b" stroke-width="6"/>'
          '<g fill="#f2c94c" stroke="#7a3d00" stroke-width="3">'
          + "".join(f'<ellipse cx="{cx}" cy="{cy}" rx="9" ry="20" transform="rotate({r} {cx} {cy})"/>'
                    for cx, cy, r in ((32, 40, -35), (26, 110, -28), (22, 180, -20), (20, 250, -12), (19, 320, -4),
                                      (20, 390, 6), (22, 460, 14), (27, 530, 24))) + "</g></svg>")
DESTELLO = ('<svg viewBox="0 0 40 40" width="{t}" height="{t}" style="{e}"><path d="M20 0 L24 16 L40 20 L24 24 L20 40 '
            'L16 24 L0 20 L16 16 Z" fill="#ffe58a"/></svg>')


def decoracion(alto=1350, verde=False):
    """Capa de adornos detrás del contenido: cintas doradas en las esquinas, laureles, copas, destellos y confeti."""
    import random
    rnd = random.Random(7)   # siempre igual
    cinta = ("position:absolute;width:460px;height:{h}px;background:{b};box-shadow:0 4px 10px rgba(0,0,0,.4);"
             "z-index:0;{p}")
    oro = "linear-gradient(90deg,#7a5300,#f6d46a 30%,#fff6cf 50%,#d39b1a 70%,#7a5300)"
    osc = "linear-gradient(90deg,#3a2700,#c8920e,#3a2700)"
    acento = "#3ee07a" if verde else "#ffd84a"
    out = []
    for lado, rot in (("left", -40), ("right", 40)):
        for y, h, b in ((70, 54, oro), (150, 18, osc)):
            out.append(f'<div style="{cinta.format(h=h, b=b, p=f"top:{y - 40}px;{lado}:-150px;transform:rotate({rot}deg)")}"></div>')
            out.append(f'<div style="{cinta.format(h=h, b=b, p=f"bottom:{y - 40}px;{lado}:-150px;transform:rotate({-rot}deg)")}"></div>')
    largo = alto - 760
    out.append(LAUREL.format(h=largo, e=f"position:absolute;left:8px;top:380px;z-index:0"))
    out.append(LAUREL.format(h=largo, e=f"position:absolute;right:8px;top:380px;z-index:0;transform:scaleX(-1)"))
    out.append(COPA.format(w=120, e="position:absolute;left:200px;top:60px;z-index:0;transform:rotate(-12deg);"
                                     "filter:drop-shadow(0 6px 8px rgba(0,0,0,.5))"))
    out.append(COPA.replace('id="oroG"', 'id="oroG2"').replace("url(#oroG)", "url(#oroG2)").format(
        w=120, e="position:absolute;right:200px;top:60px;z-index:0;transform:rotate(12deg);filter:drop-shadow(0 6px 8px rgba(0,0,0,.5))"))
    for x, y, t in ((150, 330, 34), (900, 300, 40), (80, 560, 26), (990, 640, 30), (120, 900, 30), (960, 980, 36),
                    (330, 40, 24), (740, 36, 28)):
        out.append(DESTELLO.format(t=t, e=f"position:absolute;left:{x}px;top:{y * alto // 1350}px;z-index:0;"
                                          "filter:drop-shadow(0 0 8px rgba(255,230,140,.9))"))
    colores = ["#ffd84a", "#fff3c4", acento, "#e3a71b", "#ffffff"]
    for _ in range(26):
        x, y = rnd.randint(40, 1040), rnd.randint(260, alto - 260)
        if 140 < x < 940:   # el confeti solo por los lados, sin tapar las filas
            x = rnd.choice((rnd.randint(30, 130), rnd.randint(950, 1050)))
        t = rnd.randint(8, 16)
        out.append(f'<span style="position:absolute;left:{x}px;top:{y}px;width:{t}px;height:{t // 2 + 3}px;'
                   f'background:{rnd.choice(colores)};transform:rotate({rnd.randint(0, 180)}deg);z-index:0;opacity:.9"></span>')
    # todo dentro de una capa del tamaño del lienzo (si no, imagenes.ajustar_al_lienzo lo ve «recortado por arriba»)
    return (f'<div class="deco" style="position:absolute;left:0;top:0;width:1080px;height:{alto}px;overflow:hidden;'
            f'z-index:0;pointer-events:none">' + "".join(out) + "</div>")


def _html(cuerpo, w, h, verde=False, extra=""):
    return (f"<!doctype html><html><head><meta charset='utf-8'><style>{base(h, verde)}"
            f"*{{box-sizing:border-box}} body{{margin:0;width:{w}px;min-height:{h}px;font-family:{LETRA};color:#fff;"
            f"display:flex;flex-direction:column;align-items:center;position:relative;overflow:hidden}}{extra}"
            f"body>*{{position:relative;z-index:1}}</style></head>"
            f"<body>{decoracion(h, verde) if w == 1080 else ''}{cuerpo}</body></html>")


def _cinta(texto, tam=54):
    return (f'<div class="banda" style="transform:rotate(-2deg)"><div class="oro" style="font-size:{tam}px;'
            f'line-height:1.05;text-align:center">{texto}</div></div>')


def _vs(t, lado, nombre_tam):
    l, v = equipo(t["local"]), equipo(t["visitante"])
    col = lambda n, i, u: (f'<div style="display:flex;flex-direction:column;align-items:center;gap:18px;width:360px">'
                           f'{escudo(i, u, n, lado)}<div class="b3d" style="font-size:{_tam(n, nombre_tam, 13)}px;'
                           f'line-height:1;text-align:center">{e(n)}</div></div>')
    return (f'<div style="display:flex;align-items:center;justify-content:space-between;width:960px">'
            f'{col(l, t.get("id_l"), t.get("logo_l"))}<div class="oro" style="font-size:110px">VS</div>'
            f'{col(v, t.get("id_v"), t.get("logo_v"))}</div>')


def datos_pick(texto):
    """Del texto de un pick: (pick, cuota, stake, razón)."""
    pick = cuota = stake = razon = None
    for l in texto.split("\n"):
        l = l.strip()
        m = re.match(r"🍀\s*(.+?)\s*@\s*(\d+[.,]\d+)", l)
        if m and not pick:
            pick, cuota = m.group(1), m.group(2).replace(".", ",")
        m = re.search(r"Stake\s*(\d+\s*/\s*10)", l)
        if m:
            stake = m.group(1).replace(" ", "")
        if l.startswith("👨‍💻") and not razon:
            razon = l.replace("👨‍💻", "").strip()
    return pick, cuota, stake, razon


def pick_del_dia(p, w=1080, h=1350):
    """HTML del pick suelto, o None si el post no es un pick de un partido conocido."""
    t = partido(p)
    pick, cuota, stake, razon = datos_pick(p.get("texto", ""))
    if not (t and pick and cuota):
        return None
    vertical = h > 1500
    liga = mayus(t.get("liga") or "")
    info = " · ".join(x for x in (cuando(t, p.get("fecha", "")), liga) if x)
    pk = mayus(pick)
    razon_html = (f'<div style="margin-top:26px;width:900px;font-weight:600;font-size:34px;line-height:1.25;'
                  f'text-align:center;color:#f3e3b0;text-shadow:0 2px 8px #000">{e(fem(razon))}</div>') if razon and len(razon) < 170 else ""
    cuerpo = (
        f'<div style="margin-top:{90 if vertical else 34}px">{logo_img(250 if vertical else 170)}</div>'
        f'<div style="margin-top:6px">{_cinta("PICK DEL DÍA", 84)}</div>'
        f'<div style="margin-top:{70 if vertical else 30}px">{_vs(t, 270 if vertical else 240, 52)}</div>'
        f'<div style="margin-top:26px;font-weight:700;font-size:36px;letter-spacing:3px;color:#c9d4ff">{e(info)}</div>'
        f'<div class="card" style="margin-top:{60 if vertical else 30}px;width:960px;min-height:150px;display:flex;align-items:center;'
        f'justify-content:space-between;gap:20px;padding:16px 16px 16px 40px">'
        f'<div class="b3d" style="font-size:{_tam(pk, 64, 18)}px;line-height:1.02">{e(pk)}</div>'
        f'<div class="pastilla" style="font-size:80px;height:118px;flex:none">@{e(cuota)}</div></div>'
        + (f'<div class="pastilla" style="margin-top:28px;font-size:42px;padding:4px 30px;border-radius:999px">'
           f'{trebol(36, "margin-right:10px")}STAKE {e(stake)}</div>' if stake else "")
        + razon_html
        + f'<div style="position:absolute;left:0;right:0;bottom:{120 if vertical else 44}px;display:flex;justify-content:center">'
        f'{_cinta("ACTIVA LAS NOTIFICACIONES<br>QUE VIENEN MÁS COMBIS", 50)}</div>')
    return _html(cuerpo, w, h)


def _marcador(x):
    m = x.get("marcador")
    return f"{m[0]} - {m[1]}" if isinstance(m, list) and len(m) == 2 and None not in m else ""


def _sello(tam=72):
    return (f'<div style="display:flex;align-items:center;gap:14px;padding:8px 32px;border:9px solid #3ee07a;border-radius:18px;'
            f'background:rgba(6,42,28,.8);box-shadow:0 0 30px rgba(62,224,122,.6);transform:rotate(-12deg)">'
            f'<svg width="{tam - 8}" height="{tam - 8}" viewBox="0 0 64 64"><path d="M10 34 L26 50 L56 16" fill="none" '
            f'stroke="#3ee07a" stroke-width="11" stroke-linecap="round" stroke-linejoin="round"/></svg>'
            f'<span style="font-weight:900;font-style:italic;font-size:{tam}px;line-height:1;color:#3ee07a;letter-spacing:3px">'
            f'ACERTADO</span></div>')


def _cajas(datos):
    return ('<div style="margin-top:34px;width:880px;display:grid;grid-template-columns:repeat(%d,minmax(0,1fr));gap:16px">'
            % len(datos) + "".join(
                f'<div class="card" style="padding:12px 0;display:flex;flex-direction:column;align-items:center;border-width:3px">'
                f'<span style="font-weight:700;font-size:26px;color:#c9d4ff;letter-spacing:3px">{e(a)}</span>'
                f'<span class="oro" style="font-size:{_tam(str(b), 56, 9)}px;line-height:1.08">{e(str(b))}</span></div>'
                for a, b in datos) + "</div>")


def verde_partido(t, pata, cuota, publicado, liga=None, alto=1350):
    """Acierto de UN partido: escudos, marcador final, el pick con su cuota y el sello ✓ ACERTADO (Verde B + sello C)."""
    pk = mayus(pata.get("texto", ""))
    fin = _marcador(pata)
    centro = (f'<div style="display:flex;flex-direction:column;align-items:center;gap:10px">'
              f'<span style="font-weight:800;font-style:italic;font-size:30px;letter-spacing:4px;color:#c9d4ff">FINAL</span>'
              f'<span class="pastilla" style="height:136px;width:250px;font-size:96px">{e(fin)}</span></div>') if fin else \
        '<div class="oro" style="font-size:110px">VS</div>'
    l, v = equipo(t["local"]), equipo(t["visitante"])
    col = lambda n, i, u: (f'<div style="display:flex;flex-direction:column;align-items:center;gap:14px;width:320px">'
                           f'{escudo(i, u, n, 220)}<div class="b3d" style="font-size:{_tam(n, 46, 13)}px;line-height:1;'
                           f'text-align:center">{e(n)}</div></div>')
    datos = [("CUOTA", cuota or "—"), ("PUBLICADO", publicado or "—")]
    if liga:
        datos.append(("COMPETICIÓN", mayus(liga)[:16]))
    cuerpo = (
        f'<div style="margin-top:40px">{logo_img(200)}</div>'
        f'<div style="margin-top:6px">{_cinta("PICK ACERTADO", 80)}</div>'
        f'<div class="card" style="margin-top:34px;width:960px;border-color:#3ee07a;box-shadow:0 0 50px rgba(62,224,122,.45),'
        f'inset 0 2px 0 rgba(255,255,255,.2);padding:34px 0 34px;display:flex;flex-direction:column;align-items:center">'
        f'<div style="width:100%;display:flex;align-items:center;justify-content:space-around">'
        f'{col(l, t.get("id_l"), t.get("logo_l"))}{centro}{col(v, t.get("id_v"), t.get("logo_v"))}</div>'
        f'<div style="position:relative;margin-top:120px;width:880px">'
        f'<div class="card" style="min-height:136px;display:flex;align-items:center;justify-content:space-between;gap:20px;'
        f'padding:10px 30px;border-color:#5b7bff"><span class="b3d" style="font-size:{_tam(pk, 60, 18)}px;line-height:1.02">{e(pk)}</span>'
        f'<span class="oro" style="font-size:84px;line-height:1;flex:none">@{e(cuota or "")}</span></div>'
        f'<div style="position:absolute;right:24px;top:-74px">{_sello(64)}</div></div>'
        f'{_cajas(datos)}</div>'
        f'<div style="position:absolute;left:0;right:0;bottom:56px;display:flex;justify-content:center">'
        f'{_cinta("¿QUIÉN LA LLEVABA?", 60)}</div>')
    return _html(cuerpo, 1080, alto, verde=True)


def verde_lista(patas, titulo, cuota, publicado, alto=1350):
    """Acierto de varias patas / partidos: lista de patas con su tick y el sello."""
    n = len(patas)
    letra = 44 if n <= 3 else 38 if n <= 5 else 32 if n <= 8 else 26
    filas = ""
    for x in patas:
        anul = x.get("estado") == "anulada"
        sub = " · ".join(s for s in (fem(x.get("partido", "")), _marcador(x)) if s)
        filas += (f'<div class="card" style="display:flex;align-items:center;gap:20px;padding:14px 26px;border-width:3px;'
                  f'border-left:10px solid {"#8a8f9e" if anul else "#3ee07a"};opacity:{.55 if anul else 1}">'
                  f'<span style="font-size:{letra}px">{"⏸️" if anul else "✅"}</span><div style="flex:1">'
                  f'<div class="b3d" style="font-size:{letra}px;line-height:1.05">{e(mayus(x.get("texto", "")))}'
                  f'{" (NO SE JUGÓ)" if anul else ""}</div>'
                  + (f'<div style="font-weight:600;font-size:{max(22, letra - 14)}px;color:#cbd5e1;margin-top:4px">{e(sub)}</div>' if sub else "")
                  + "</div></div>")
    cuerpo = (
        f'<div style="margin-top:40px">{logo_img(180 if n <= 4 else 140)}</div>'
        f'<div style="margin-top:6px">{_cinta(e(titulo), 76)}</div>'
        f'<div style="margin-top:30px">{_sello(60)}</div>'
        f'<div style="margin-top:44px;width:940px;display:flex;flex-direction:column;gap:{14 if n <= 5 else 10}px">{filas}</div>'
        f'{_cajas([("CUOTA", cuota or "—"), ("PUBLICADO", publicado or "—")])}'
        f'<div style="margin:40px 0 70px;display:flex;justify-content:center">{_cinta("¿QUIÉN LA LLEVABA?", 56)}</div>')
    return _html(cuerpo, 1080, alto, verde=True)


def tarjeta_partido(t, cuando_txt, cuota=None):
    """Foto apaisada del partido (1180x340) para las combis de un partido."""
    l, v = equipo(t["local"]), equipo(t["visitante"])
    col = lambda n, i, u: (f'<div style="display:flex;flex-direction:column;align-items:center;gap:12px;width:330px">'
                           f'{escudo(i, u, n, 175)}<div class="b3d" style="font-size:{_tam(n, 40, 14)}px;line-height:1;'
                           f'text-align:center">{e(n)}</div></div>')
    centro = (f'<div style="flex:1;display:flex;flex-direction:column;align-items:center;gap:10px">'
              f'{logo_img(110)}<div class="oro" style="font-size:64px;line-height:1">{e(cuando_txt)}</div>'
              + (f'<div class="pastilla" style="font-size:34px;padding:2px 20px">COMBI DEL PARTIDO · x{e(cuota)}</div>' if cuota else
                 f'<div style="font-weight:700;font-size:26px;letter-spacing:3px;color:#c9d4ff">{e(mayus(t.get("liga") or ""))}</div>')
              + "</div>")
    cuerpo = (f'<div style="display:flex;align-items:center;justify-content:space-between;width:1180px;height:340px;padding:0 40px">'
              f'{col(l, t.get("id_l"), t.get("logo_l"))}{centro}{col(v, t.get("id_v"), t.get("logo_v"))}</div>')
    return _html(cuerpo, 1180, 340, extra="html::after{inset:8px;border-width:4px;border-radius:22px}")


QG_CSS = """
.f{display:flex;align-items:center;height:%(h)dpx;position:relative;width:1000px}
.f:before{content:"";position:absolute;left:44px;right:0;top:7px;bottom:7px;border-radius:50px;
 background:linear-gradient(180deg,#ffffff,#f3eee2);box-shadow:0 6px 18px rgba(0,0,0,.45),inset 0 0 0 3px #f2c94c}
.n{position:relative;z-index:1;width:126px;height:%(nh)dpx;transform:skewX(-18deg);border-radius:14px 4px 4px 14px;
 background:linear-gradient(180deg,#ffe58a,#e3a71b 55%%,#a66f00);box-shadow:0 4px 0 #7a5300;display:flex;align-items:center}
.n span{transform:skewX(18deg);font-family:%(letra)s;font-weight:900;font-style:italic;font-size:%(nf)dpx;color:#fff;
 text-shadow:0 3px 0 #7a5300;margin-left:24px}
.fl{position:relative;z-index:1;width:%(fw)dpx;height:%(fh)dpx;margin-left:14px;background:#fff;border-radius:8px;
 overflow:hidden;box-shadow:0 0 0 4px #f2c94c,0 5px 10px rgba(0,0,0,.35);display:flex;align-items:center;justify-content:center;flex:none}
.fl svg{width:100%%;height:100%%;display:block}
.fl img.real{width:100%%;height:100%%;object-fit:cover;display:block}
.fl span{font-size:%(fe)dpx;line-height:1}
.es{position:relative;z-index:1;width:%(eh)dpx;height:%(eh)dpx;margin:0 6px 0 22px;display:flex;align-items:center;justify-content:center;flex:none}
.es img{width:100%%;height:100%%;object-fit:contain;filter:drop-shadow(0 3px 4px rgba(0,0,0,.3))}
.nom{position:relative;z-index:1;flex:1;font-family:%(letra)s;font-weight:900;font-style:italic;font-size:%(nomf)dpx;color:#0a1440;
 text-align:center;line-height:1;padding:0 6px}
.flecha{position:relative;z-index:1;font-family:%(letra)s;font-weight:900;color:#e39a00;font-size:%(nf)dpx;margin-right:12px}
.pick{position:relative;z-index:1;display:flex;align-items:center;gap:12px;height:%(ph)dpx;padding:0 30px 0 10px;border-radius:40px;margin-right:10px;
 background:linear-gradient(180deg,#ffe58a,#e3a71b 55%%,#a66f00);box-shadow:0 4px 0 #7a5300,inset 0 0 0 2px #fff3c4}
.pick b{font-family:%(letra)s;font-weight:900;font-style:italic;font-size:%(pf)dpx;color:#fff;text-shadow:0 2px 0 #7a5300;letter-spacing:1px}
.ck{width:%(ck)dpx;height:%(ck)dpx;border-radius:50%%;border:4px solid #fff;display:flex;align-items:center;justify-content:center;
 color:#fff;font-size:%(ckf)dpx;font-weight:900;font-family:Arial,sans-serif}
.ok .pick{background:linear-gradient(180deg,#8ff0a8,#22b14c 55%%,#0d6b2a);box-shadow:0 4px 0 #0a4d1e}
.ko .pick{background:linear-gradient(180deg,#ff9a8a,#d63a2a 55%%,#8a1a10);box-shadow:0 4px 0 #5e0f08}
"""


BANDERAS = RAIZ / "publicaciones" / "media" / "marca" / "banderas"


def bandera_real(pais):
    """11/11 (Marcos: «las banderas originales, como los escudos»): la bandera de verdad (flag-icons, MIT) o None."""
    import json
    if not hasattr(bandera_real, "cod"):
        f = BANDERAS / "paises.json"
        bandera_real.cod = json.loads(f.read_text()) if f.exists() else {}
    c = bandera_real.cod.get(pais or "")
    svg = BANDERAS / f"{c}.svg" if c else None
    if not (svg and svg.exists()):
        return None
    return f'<img class="real" src="data:image/svg+xml;base64,{base64.b64encode(svg.read_bytes()).decode()}" alt="">'


def es_seleccion(f):
    """¿La fila es una selección? Entonces solo va su bandera (Marcos: no repetir bandera y escudo)."""
    if f.get("seleccion"):
        return True
    pais = f.get("pais")
    if not pais:
        return False
    try:
        from combis_dia import nombre_es
        nombres = {pais, pais.replace("-", " "), nombre_es(pais), nombre_es(pais.replace("-", " "))}
    except Exception:
        nombres = {pais, pais.replace("-", " ")}
    return fem(f.get("nombre", "")).replace(" (fem.)", "") in nombres


def quien_gana(filas, titulo, sub=None):
    """«GANADORES» (11/11, Marcos: «lo más parecido a como lo teníamos antes»): como la plantilla oro (número dorado,
    bandera dibujada, escudo, flecha y WIN) sobre el fondo del logo nuevo. Selecciones: solo su bandera (no se repite)."""
    from ganadores_img import BANDERAS_SVG, _bandera
    n = len(filas)
    h = 112 if n <= 6 else 100 if n <= 8 else 84
    css = QG_CSS % {"h": h, "nh": h - 26, "nf": h // 2 - 6, "fw": int((h - 32) * 4 / 3), "fh": h - 32, "fe": h // 2,
                    "eh": h - 22, "nomf": h // 2 - 4, "ph": h - 36, "pf": h // 2 - 12, "ck": h // 2 - 12, "ckf": h // 4 + 2,
                    "letra": LETRA}
    lis = ""
    for i, f in enumerate(filas, 1):
        ok = f.get("ok")
        cls = " ok" if ok is True else " ko" if ok is False else ""
        marca = "✕" if ok is False else "✓"
        esc = '<div class="es"></div>'   # hueco igual para que los nombres queden alineados
        if not es_seleccion(f) and f.get("escudo") and Path(f["escudo"]).is_file():
            esc = f'<div class="es"><img src="data:image/png;base64,{nitido(Path(f["escudo"]), h - 22)}"></div>'
        if bandera_real(f.get("pais")) or (f.get("pais") or "") in BANDERAS_SVG:
            bandera = f'<div class="fl">{bandera_real(f.get("pais")) or _bandera(f)}</div>'
        else:   # sin país conocido (p. ej. equipos femeninos): hueco del mismo tamaño, nada de ⚽
            bandera = '<div class="fl" style="visibility:hidden"></div>'
        nombre = equipo(f["nombre"])
        lis += (f'<div class="f{cls}"><div class="n"><span>{i}.</span></div>{bandera}{esc}'
                f'<div class="nom" style="font-size:{_tam(nombre, h // 2 - 4, 14)}px">{e(nombre)}</div><div class="flecha">➜</div>'
                f'<div class="pick"><div class="ck">{marca}</div><b>{e(f.get("pick", "WIN"))}</b></div></div>')
    cuerpo = (
        f'<div style="margin-top:{36 if n > 5 else 0}px">{logo_img(170 if n > 5 else 220)}</div>'
        f'<div style="margin-top:4px">{_cinta(e(titulo or "QUIÉN GANA HOY"), 70)}</div>'
        + (f'<div style="margin-top:14px;font-weight:700;font-size:32px;letter-spacing:3px;color:#c9d4ff">{e(sub)}</div>' if sub else "")
        + f'<div style="margin-top:30px;display:flex;flex-direction:column;gap:8px">{lis}</div>'
        f'<div style="margin:36px 0 64px;display:flex;justify-content:center">{_cinta("¿LA PINTAMOS DE VERDE? 🍀", 54)}</div>')
    centrar = "body{justify-content:center;height:1350px}" if n <= 5 else ""   # pocas filas: todo centrado
    return _html(cuerpo, 1080, 1350, extra=css + centrar)
