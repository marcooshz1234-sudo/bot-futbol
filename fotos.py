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
    dentro = (f'<img src="data:image/png;base64,{base64.b64encode(f.read_bytes()).decode()}" alt="">' if f and f.exists()
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


def _html(cuerpo, w, h, verde=False, extra=""):
    return (f"<!doctype html><html><head><meta charset='utf-8'><style>{base(h, verde)}"
            f"*{{box-sizing:border-box}} body{{margin:0;width:{w}px;min-height:{h}px;font-family:{LETRA};color:#fff;"
            f"display:flex;flex-direction:column;align-items:center;position:relative}}{extra}</style></head>"
            f"<body>{cuerpo}</body></html>")


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
        f'<div style="margin-top:{90 if vertical else 40}px">{logo_img(250 if vertical else 200)}</div>'
        f'<div style="margin-top:6px">{_cinta("PICK DEL DÍA", 84)}</div>'
        f'<div style="margin-top:{70 if vertical else 44}px">{_vs(t, 230 if vertical else 200, 52)}</div>'
        f'<div style="margin-top:26px;font-weight:700;font-size:36px;letter-spacing:3px;color:#c9d4ff">{e(info)}</div>'
        f'<div class="card" style="margin-top:{60 if vertical else 40}px;width:960px;min-height:150px;display:flex;align-items:center;'
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
                           f'{escudo(i, u, n, 190)}<div class="b3d" style="font-size:{_tam(n, 46, 13)}px;line-height:1;'
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
                           f'{escudo(i, u, n, 150)}<div class="b3d" style="font-size:{_tam(n, 40, 14)}px;line-height:1;'
                           f'text-align:center">{e(n)}</div></div>')
    centro = (f'<div style="flex:1;display:flex;flex-direction:column;align-items:center;gap:10px">'
              f'{logo_img(110)}<div class="oro" style="font-size:64px;line-height:1">{e(cuando_txt)}</div>'
              + (f'<div class="pastilla" style="font-size:34px;padding:2px 20px">COMBI DEL PARTIDO · x{e(cuota)}</div>' if cuota else
                 f'<div style="font-weight:700;font-size:26px;letter-spacing:3px;color:#c9d4ff">{e(mayus(t.get("liga") or ""))}</div>')
              + "</div>")
    cuerpo = (f'<div style="display:flex;align-items:center;justify-content:space-between;width:1180px;height:340px;padding:0 40px">'
              f'{col(l, t.get("id_l"), t.get("logo_l"))}{centro}{col(v, t.get("id_v"), t.get("logo_v"))}</div>')
    return _html(cuerpo, 1180, 340, extra="html::after{inset:8px;border-width:4px;border-radius:22px}")


def quien_gana(filas, titulo, sub=None):
    """«GANADORES»: cada equipo con su escudo, bandera y la pastilla WIN (verde si acertó, roja si falló)."""
    n = len(filas)
    alto_f = 112 if n <= 6 else 96 if n <= 8 else 80
    lis = ""
    for i, f in enumerate(filas, 1):
        ok = f.get("ok")
        color = "#3ee07a" if ok is True else "#ff5a4a" if ok is False else ORO
        marca = "✓ " if ok is True else "✕ " if ok is False else ""
        esc = escudo(None, None, f["nombre"], alto_f - 14)
        if f.get("escudo") and Path(f["escudo"]).is_file():
            esc = (f'<div class="escudo" style="width:{alto_f - 14}px;height:{alto_f - 14}px;border-width:5px">'
                   f'<img src="data:image/png;base64,{base64.b64encode(Path(f["escudo"]).read_bytes()).decode()}"></div>')
        lis += (f'<div class="card" style="height:{alto_f}px;display:flex;align-items:center;gap:20px;padding:0 18px;border-width:3px;'
                f'border-color:{color}">'
                f'<span class="oro" style="font-size:{alto_f // 2}px;width:66px;text-align:center">{i}</span>'
                f'<span style="font-size:{alto_f // 2 - 6}px">{f.get("bandera", "")}</span>{esc}'
                f'<span class="b3d" style="flex:1;font-size:{_tam(mayus(f["nombre"]), alto_f // 2 + 4, 16)}px">{e(mayus(f["nombre"]))}</span>'
                f'<span class="pastilla" style="font-size:{alto_f // 2 - 4}px;padding:0 26px;height:{alto_f - 34}px;'
                + (f'background:linear-gradient(180deg,#8ff0a8,#22b14c 55%,#0d6b2a);color:#fff;' if ok is True else
                   f'background:linear-gradient(180deg,#ff9a8a,#d63a2a 55%,#8a1a10);color:#fff;' if ok is False else "")
                + f'">{marca}{e(f.get("pick", "WIN"))}</span></div>')
    cuerpo = (
        f'<div style="margin-top:36px">{logo_img(170)}</div>'
        f'<div style="margin-top:4px">{_cinta(e(titulo or "QUIÉN GANA HOY"), 70)}</div>'
        + (f'<div style="margin-top:14px;font-weight:700;font-size:32px;letter-spacing:3px;color:#c9d4ff">{e(sub)}</div>' if sub else "")
        + f'<div style="margin-top:30px;width:960px;display:flex;flex-direction:column;gap:12px">{lis}</div>'
        f'<div style="margin:36px 0 64px;display:flex;justify-content:center">{_cinta("¿LA PINTAMOS DE VERDE? 🍀", 54)}</div>')
    return _html(cuerpo, 1080, 1350)
