"""
Convierte un post de texto en imagen (1080x1350, feed de Instagram/Facebook) y en
reel (vídeo vertical 1080x1920, las líneas van apareciendo una a una).

Uso:  python imagenes.py publicaciones/cola.json [id ...]
Guarda en publicaciones/media/<id>.jpg y <id>.mp4

Necesita Chromium (Playwright) y ffmpeg. Si el post tiene foto (escudos), la pone arriba.
No inventa nada: solo el texto del post y, si la hay, la foto que manda el dueño.
"""

import base64
from datetime import datetime
import html
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

from playwright.sync_api import sync_playwright

from marca import DISENO, LETRA, ORO, base, logo_img

RAIZ = Path(__file__).resolve().parent
MEDIA = RAIZ / "publicaciones" / "media"

CSS = """
*{margin:0;padding:0;box-sizing:border-box}
body{width:%(w)dpx;height:%(h)dpx;font-family:%(letra)s;color:#f7f3e8;display:flex;flex-direction:column;
 padding:%(pad)dpx 76px 60px;overflow:hidden}
.marca{text-align:center;margin-bottom:14px;position:relative;z-index:1}
.titulo,.sub,.lineas,.cuota,.dato,.pie,.foto{position:relative;z-index:1}
.foto{width:100%%;border-radius:22px;margin-bottom:30px;border:4px solid %(oro)s;box-shadow:0 10px 30px rgba(0,0,0,.6)}
.titulo{font-size:%(ft)dpx;line-height:1.08;text-align:center;margin-bottom:30px;padding:0 10px}
.sub{font-size:44px;text-align:center;margin:-14px 0 28px;line-height:1.1}
.lineas{display:flex;flex-direction:column;gap:%(gap)dpx}
.l{font-size:%(fl)dpx;font-weight:600;line-height:1.2;background:linear-gradient(180deg,rgba(22,36,110,.9),rgba(8,16,52,.9));
 border:2px solid rgba(242,201,76,.55);border-left:9px solid %(oro)s;border-radius:16px;padding:14px 24px;
 box-shadow:0 6px 16px rgba(0,0,0,.4)}
.cuota{margin-top:30px;display:flex;gap:18px;justify-content:center;flex-wrap:wrap}
.cuota div{font-size:48px;padding:6px 30px}
.cuota div.b{background:linear-gradient(180deg,#8ff0a8,#22c55e 55%%,#0d6b2a);color:#fff;border-color:#d4ffe1;box-shadow:0 6px 0 #0a4d1e}
.dato{margin-top:26px;font-size:36px;font-weight:600;line-height:1.25;color:#f3e3b0;text-align:center;text-shadow:0 2px 8px #000}
.pie{margin-top:auto;display:flex;justify-content:center;padding-top:22px}
.pie .banda{padding:6px 40px 8px}
.oculto{visibility:hidden}
.v{justify-content:center}
.v .pie{position:absolute;bottom:90px;left:70px;right:70px;margin:0}
"""


CSS_CL = """
.l{background:linear-gradient(180deg,rgba(16,20,16,.9),rgba(4,6,4,.9));border:2px solid rgba(126,240,58,.75);
 border-left:9px solid #7ef03a;box-shadow:0 0 14px rgba(126,240,58,.22);color:#fff;font-style:italic}
.titulo{text-transform:uppercase}
body:not(.v) .marca{margin-top:auto}
.v .pie{position:static;margin-top:44px}
.sub{font-size:40px}
.cuota div.b{background:linear-gradient(180deg,#fff3b0,#ffd84a 45%%,#d99a10);color:#1a1200;box-shadow:0 0 20px rgba(255,216,74,.5)}
.dato{color:#f2f2f2;font-style:italic}
"""


def partes(texto):
    filas = [f.strip() for f in texto.split("\n")]
    titulo = filas[0]
    sub, lineas, cuota, dato = None, [], [], None
    for f in filas[1:]:
        if not f or f.startswith(("🔞", "🍀 ¿LA", "¡Combina", "🔔")):
            continue
        from plantillas import ES_ETIQUETA
        if f.startswith(ES_ETIQUETA):   # 11/11: la etiqueta, debajo del título
            sub = sub or f
        elif f.startswith("💥 COMBI DEL PARTIDO"):
            sub = f
        elif f.startswith(("🎯", "💶", "📈", "🧠")):
            cuota.append(f)
        elif f.startswith("📊"):
            dato = f
        elif f.startswith("🔥") and not lineas and not sub:
            sub = f
        elif f.startswith("🔥") and lineas:
            dato = dato or f
        else:
            lineas.append(f)
    return titulo, sub, lineas, cuota, dato


def documento(p, vertical, mostrar=None, foto_b64=None):
    if p.get("ganadores_img"):   # 11/11: «Partidos de hoy» en Instagram = la misma foto (reel e historia en vertical)
        import fotos
        import ganadores_win
        filas, liga = ganadores_win.datos_imagen(p)
        return fotos.quien_gana(filas, p["ganadores_img"]["titulo"], liga=liga, alto=1920 if vertical else 1350), 1
    if re.search(r"-pick(-|$)", p.get("id", "")) and not re.search(r"verde|rojo", p.get("id", "")) and not foto_b64:
        import fotos   # 11/11: el pick suelto con su plantilla (escudos, VS, cuota)
        doc = fotos.pick_del_dia(p, 1080, 1920 if vertical else 1350)
        if doc:
            return doc, 1
    titulo, sub, lineas, cuota, dato = partes(p["texto"])
    w, h = (1080, 1920) if vertical else (1080, 1350)
    n = len(lineas)
    fl = 46 if n <= 5 else 41 if n <= 7 else 36 if n <= 12 else 30 if n <= 16 else 25   # 05/11: listas de 18 partidos
    if vertical:
        fl += 8
    gap = 14 if n <= 7 else 10 if n <= 12 else 6 if n <= 16 else 4
    if foto_b64 and not vertical:   # con foto de escudos hay menos sitio en 1080x1350
        fl -= 4
        gap = 10
    css = base(h) + CSS % {"w": w, "h": h, "pad": 80 if vertical else 56, "ft": 76 if vertical else 64, "fl": fl, "gap": gap,
                          "oro": ORO, "letra": LETRA}
    import marca
    if marca.TEMA == "cl":
        css += CSS_CL % {}
    total = 1 + n + 2
    ver = total if mostrar is None else mostrar

    def cls(i):
        return "" if i < ver else " oculto"
    e = html.escape
    tam = (220 if vertical else 180) if n <= 7 else (150 if vertical else 120) if n <= 12 else 80
    import fotos   # 11/11: los mismos adornos que el pick del día (cintas, copas, laureles, confeti)
    partes_html = [fotos.decoracion(h), f'<div class="marca">{logo_img(tam)}</div>']
    if foto_b64:
        partes_html.append(f'<img class="foto" src="data:image/jpeg;base64,{foto_b64}">')
    partes_html.append(f'<div class="titulo oro">{e(titulo)}</div>')
    if sub:
        partes_html.append(f'<div class="sub b3d">{e(sub)}</div>')
    partes_html.append('<div class="lineas">' + "".join(
        f'<div class="l{cls(1 + i)}">{e(l)}</div>' for i, l in enumerate(lineas)) + "</div>")
    if cuota:
        partes_html.append(f'<div class="cuota{cls(1 + n)}">' + "".join(
            f'<div class="pastilla{" b" if c.startswith("💶") else ""}">{e(c)}</div>' for c in cuota) + "</div>")
    if dato:
        partes_html.append(f'<div class="dato{cls(2 + n)}">{e(dato)}</div>')
    if fotos.CL:
        partes_html.append(f'<div class="pie">{fotos._firma()}</div>')
    else:
        partes_html.append('<div class="pie"><div class="banda"><span class="oro" style="font-size:40px">@COMBILOCAS</span></div></div>')
    clase = ' class="v"' if vertical else ""
    return f"<html><head><meta charset='utf-8'><style>{css}</style></head><body{clase}>{''.join(partes_html)}</body></html>", total


def ajustar_al_lienzo(pagina, alto):
    """No guardar un post o fotograma con el pie o el texto fuera del lienzo."""
    pagina.evaluate("document.fonts.ready")
    pagina.evaluate("window.scrollTo(0, 0)")
    fondo = pagina.evaluate("""() => Math.max(...Array.from(document.body.children,
        el => el.getBoundingClientRect().bottom)) + 24""")
    if fondo > alto:
        escala = (alto - 12) / fondo
        pagina.add_style_tag(content=f"body{{overflow:visible;background:none;transform:scale({escala});transform-origin:top center}}")
    pagina.evaluate("window.scrollTo(0, 0)")
    comienzo = pagina.evaluate("""() => Math.min(...Array.from(document.body.children,
        el => el.getBoundingClientRect().top))""")
    if comienzo < -1:
        raise RuntimeError(f"Texto recortado por arriba: {comienzo}")
    limite = pagina.evaluate("""() => Math.max(...Array.from(document.body.children,
        el => el.getBoundingClientRect().bottom))""")
    if limite > alto:
        raise RuntimeError(f"Texto fuera del lienzo: {limite} > {alto}")


TARJETA = """<!doctype html><html><head><meta charset="utf-8"><style>
*{box-sizing:border-box}
body{margin:0;width:1180px;height:340px;background:linear-gradient(100deg,#3a2a1c 0%,#262019 30%,#1f1e1c 60%,#2a2a28 100%);
font-family:'Liberation Sans','DejaVu Sans',sans-serif;color:#fff;display:flex;align-items:center;justify-content:space-between;padding:0 52px}
.estrella{width:62px;height:62px;flex:none;margin-top:-90px}
.eq{display:flex;flex-direction:column;align-items:center;gap:22px;width:300px;margin:0 20px}
.eq img{height:140px;width:140px;object-fit:contain}
.eq b{font-size:36px;font-weight:700;text-align:center;line-height:1.1;white-space:nowrap}
.m{flex:1;text-align:center;display:flex;flex-direction:column;align-items:center;gap:6px;margin-top:-36px}
.m b{font-size:58px;font-weight:800;letter-spacing:1px}
.m span{font-size:44px;font-weight:400;color:#e8e6e3}
</style></head><body>
<svg class="estrella" viewBox="0 0 24 24"><path d="M12 2.8l2.75 5.6 6.15.9-4.45 4.35 1.05 6.1L12 16.85 6.5 19.75l1.05-6.1L3.1 9.3l6.15-.9z" fill="none" stroke="#fff" stroke-width="1.9" stroke-linejoin="round"/></svg>
<div class="eq"><img src="{logo_l}"><b>{local}</b></div>
<div class="m"><b>{hora}</b><span>{dia}</span></div>
<div class="eq"><img src="{logo_v}"><b>{visitante}</b></div>
<svg class="estrella" viewBox="0 0 24 24"><path d="M12 2.8l2.75 5.6 6.15.9-4.45 4.35 1.05 6.1L12 16.85 6.5 19.75l1.05-6.1L3.1 9.3l6.15-.9z" fill="none" stroke="#fff" stroke-width="1.9" stroke-linejoin="round"/></svg>
</body></html>"""


def escudo(url, nombre):
    """El escudo incrustado (se descarga y se guarda en publicaciones/media/escudos); si no se puede, las
    iniciales del equipo en un círculo, mejor que una imagen rota."""
    import urllib.request
    if url:
        cache = MEDIA / "escudos" / Path(url).name   # escudos.py los tiene todos guardados (<id>.png)
        try:
            if not cache.exists():
                cache.parent.mkdir(parents=True, exist_ok=True)
                cache.write_bytes(urllib.request.urlopen(url, timeout=10).read())
            return f'<img src="data:image/png;base64,{base64.b64encode(cache.read_bytes()).decode()}">'
        except Exception as e:
            print(f"Escudo de {nombre}: {e}")
    ini = "".join(w[0] for w in nombre.split()[:2]).upper()
    return (f'<div style="width:140px;height:140px;border-radius:50%;background:#3a3631;display:flex;align-items:center;'
            f'justify-content:center;font-size:56px;font-weight:800">{html.escape(ini)}</div>')


def tarjeta(p, pagina):
    """27/10: foto del partido para las combis de un solo partido (escudos, hora y día), como las que
    mejor funcionaron en Threads. → publicaciones/media/{id}.tarjeta.jpg
    11/11 (Marcos): las de UN partido se quedan SIEMPRE con este formato de antes, no se cambia."""
    import html
    t = p["tarjeta"]
    ini = datetime.fromisoformat(t["fecha"])
    hoy = datetime.fromisoformat(p["fecha"][:10])
    dias = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
    dia = "Hoy" if ini.date() == hoy.date() else "Mañana" if (ini.date() - hoy.date()).days == 1 else dias[ini.weekday()]
    doc = TARJETA
    import re
    m = re.search(r"(?:Cuota total aprox\.: |Cuota @)(\d+,\d+)", p.get("texto", ""))
    doc = doc.replace("{cuota}", f'<div class="cuota">💥 COMBI DEL PARTIDO · x{m.group(1)}</div>' if m else "")
    bandera = {"LaLiga": "🇪🇸", "Premier League": "🏴󠁧󠁢󠁥󠁮󠁧󠁿", "Serie A": "🇮🇹", "Bundesliga": "🇩🇪", "Ligue 1": "🇫🇷",
               "Champions League": "⭐", "Europa League": "🟠", "Conference League": "🟢", "Primeira Liga": "🇵🇹",
               "Eredivisie": "🇳🇱", "Championship": "🏴󠁧󠁢󠁥󠁮󠁧󠁿", "Segunda División": "🇪🇸"}.get(t.get("liga"), "⚽")
    for k, v in {"liga": f"{bandera} {(t.get('liga') or '').upper()}", "local": t["local"], "visitante": t["visitante"],
                 "hora": f"{ini:%H:%M}", "dia": dia}.items():
        doc = doc.replace("{" + k + "}", html.escape(str(v)))
    for k, nombre in (("logo_l", t["local"]), ("logo_v", t["visitante"])):
        doc = doc.replace('<img src="{' + k + '}">', escudo(t.get(k), nombre))
    pagina.set_viewport_size({"width": 1180, "height": 340})
    pagina.goto("about:blank")
    pagina.set_content(doc, wait_until="networkidle")
    pagina.wait_for_timeout(300)
    out = MEDIA / f"{p['id']}.tarjeta.jpg"
    pagina.screenshot(path=str(out), type="jpeg", quality=92)
    return out


def sin_dinero(texto):
    """27/10 (norma de Marcos): en las imágenes de Instagram nunca sale dinero. Se quitan «20,00€ → 38,40€»,
    las líneas de 💶 y cualquier línea que siga llevando €. El texto del post (Telegram, Threads) no se toca."""
    t = re.sub(r"\s*·?\s*\d+(?:[.,]\d+)?\s*€\s*→\s*\d+(?:[.,]\d+)?\s*€", "", texto)
    t = re.sub(r"desde \d+(?:[.,]\d+)?\s*€", "desde el día 1", t)
    filas = t.split("\n")
    if filas and "€" in filas[0]:   # 11/11: el título se queda (sin el dinero); antes caía y la 1ª pata hacía de título
        filas[0] = re.sub(r"¡?\s*(?:DE|DESDE)?\s*\d+(?:[.,]\d+)?\s*€(?:\s*(?:A|→)\s*\d+(?:[.,]\d+)?\s*€)?\s*!?", " ",
                          filas[0], flags=re.I)
        filas[0] = re.sub(r"\s*—\s*(?=x\d)", " · ", re.sub(r"\s{2,}", " ", filas[0])).strip()
    t = "\n".join([filas[0]] * bool(filas) + [re.sub(r":\s*$", "", l) for l in filas[1:]
                   if "€" not in l and not l.startswith("💶")])
    return re.sub(r"\n{3,}", "\n\n", t).strip()


def generar(p, pagina):
    MEDIA.mkdir(parents=True, exist_ok=True)
    # Instagram: ni dinero ni la foto de un boleto de bet365
    # (el reto escalera sí lleva el dinero: en eso consiste, Marcos 27/10)
    p = dict(p, texto=p["texto"] if "escalera" in p.get("id", "") else sin_dinero(p["texto"]),
             foto=None if "boleto" in p.get("id", "") else p.get("foto"))
    if p.get("tarjeta"):
        try:
            tarjeta(p, pagina)
        except Exception as e:
            print(f"Tarjeta de {p['id']}: {e}")
    foto = None
    if p.get("foto"):
        foto = base64.b64encode((RAIZ / p["foto"]).read_bytes()).decode()
    # imagen de feed
    doc, total = documento(p, False, foto_b64=foto)
    pagina.set_viewport_size({"width": 1080, "height": 1350})
    pagina.goto("about:blank")
    pagina.set_content(doc)
    pagina.wait_for_timeout(150)
    ajustar_al_lienzo(pagina, 1350)
    img = MEDIA / f"{p['id']}.jpg"
    pagina.screenshot(path=str(img), type="jpeg", quality=92)
    # reel: un fotograma por línea que aparece
    pagina.set_viewport_size({"width": 1080, "height": 1920})
    with tempfile.TemporaryDirectory() as tmp:
        lista = []
        # 1º fotograma = el post entero (es la portada que se ve en el perfil de Instagram);
        # luego las líneas van apareciendo una a una y al final se queda entero
        doc, _ = documento(p, True, mostrar=total, foto_b64=foto)
        pagina.goto("about:blank")
        pagina.set_content(doc)
        pagina.wait_for_timeout(80)
        ajustar_al_lienzo(pagina, 1920)
        portada = Path(tmp) / "f00.png"
        pagina.screenshot(path=str(portada))
        # la misma portada vertical sirve de historia de Instagram (redes.py → instagram_story)
        pagina.screenshot(path=str(MEDIA / f"{p['id']}.story.jpg"), type="jpeg", quality=90)
        lista.append(f"file '{portada}'\nduration 1.5")
        for k in range(1, total + 1):
            doc, _ = documento(p, True, mostrar=k, foto_b64=foto)
            pagina.goto("about:blank")
            pagina.set_content(doc)
            pagina.wait_for_timeout(80)
            ajustar_al_lienzo(pagina, 1920)
            f = Path(tmp) / f"f{k:02d}.png"
            pagina.screenshot(path=str(f))
            dur = 1.2 if k == 1 else 0.7
            if k == total:
                dur = 3.5
            lista.append(f"file '{f}'\nduration {dur}")
        lista.append(f"file '{Path(tmp) / f'f{total:02d}.png'}'")
        (Path(tmp) / "lista.txt").write_text("\n".join(lista))
        mp4 = MEDIA / f"{p['id']}.mp4"
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(Path(tmp) / "lista.txt"),
                        "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo", "-shortest",
                        "-vf", "fps=30,format=yuv420p", "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
                        "-c:a", "aac", "-b:a", "96k", "-movflags", "+faststart", str(mp4)], check=True)
    return img, mp4


def huella(p):
    import hashlib
    # «diseño-4»: 11/11 estilo CL; «diseño-3»: 11/11, plantillas con el logo nuevo y tarjeta de 1 partido con el formato de antes → se rehacen las imágenes de los posts que aún no han salido
    return hashlib.sha1((p["texto"] + str(p.get("foto")) + DISENO).encode()).hexdigest()[:12]


def pendientes_de(cola, ahora, control=None, estado=None):
    """Posts cuya imagen falta o no cuadra con su texto. 28/10: con el texto EDITADO desde el bot del móvil
    (control.json) y también los que ya tocaba publicar hace menos de 45 min y aún no han salido en Instagram
    (si se editó justo antes, la imagen vieja no valía y Instagram fallaba)."""
    from datetime import timedelta
    raiz = MEDIA.parent.parent
    if control is None:
        f = raiz / "publicaciones" / "control.json"
        control = json.loads(f.read_text(encoding="utf-8")) if f.exists() else {}
    if estado is None:
        f = raiz / "publicaciones" / "enviados_redes.json"
        estado = json.loads(f.read_text(encoding="utf-8")) if f.exists() else {}
    textos = control.get("textos", {})
    ya = ahora.strftime("%Y-%m-%dT%H:%M")
    hace45 = (ahora - timedelta(minutes=45)).strftime("%Y-%m-%dT%H:%M")
    salida = []
    for p in cola:
        if p.get("caducada") or p.get("solo_en") or p.get("sin_instagram"):
            continue
        p = dict(p, texto=textos.get(p["id"], p["texto"]))
        redes = dict(estado.get(p["id"], {}).get("redes") or {}, **(p.get("redes") or {}))
        if not (p["fecha"] > ya or (p["fecha"] >= hace45 and not redes.get("instagram"))):
            continue
        hecha = all((MEDIA / f"{p['id']}.{e}").exists() for e in ("mp4", "story.jpg", "huella"))
        if hecha and (MEDIA / f"{p['id']}.huella").read_text().strip() == huella(p):
            continue
        salida.append(p)
    return salida


def main():
    cola = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    # 05/11: «GANADORES» (solo Threads): su tarjeta con la plantilla oro, si aún no está
    for p in cola:
        if p.get("ganadores_img") and not p.get("enviado") and not (MEDIA / f"{p['id']}.tarjeta.jpg").exists():
            try:
                import ganadores_win
                print("Ganadores:", ganadores_win.hacer_imagen(p))
            except Exception as e:
                print("ganadores (imagen):", str(e)[:150])
    ids = set(sys.argv[2:]) - {"--pendientes"}
    pendientes = "--pendientes" in sys.argv   # solo los que aún no han salido y cuyo texto ha cambiado
    if pendientes:
        from datetime import datetime
        from zoneinfo import ZoneInfo
        cola = pendientes_de(cola, datetime.now(ZoneInfo("Europe/Madrid")))
    if not cola:
        print("Imágenes: nada que generar")
        return
    with sync_playwright() as pw:
        nav = pw.chromium.launch()
        pagina = nav.new_page()
        for p in cola:
            if ids and p["id"] not in ids:
                continue
            img, mp4 = generar(p, pagina)
            if pendientes:
                (MEDIA / f"{p['id']}.huella").write_text(huella(p))
            print(img.name, mp4.name)
        nav.close()


if __name__ == "__main__":
    main()
