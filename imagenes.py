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
import subprocess
import sys
import tempfile
from pathlib import Path

from playwright.sync_api import sync_playwright

RAIZ = Path(__file__).resolve().parent
MEDIA = RAIZ / "publicaciones" / "media"

CSS = """
*{margin:0;padding:0;box-sizing:border-box}
body{width:%(w)dpx;height:%(h)dpx;background:radial-gradient(120%% 80%% at 50%% 0%%,#1d3b2a 0%%,#0d1712 55%%,#070b09 100%%);
 font-family:'Liberation Sans','DejaVu Sans',sans-serif,'Noto Color Emoji';color:#f4f7f5;display:flex;flex-direction:column;
 padding:%(pad)dpx 70px 60px;overflow:hidden}
.marca{font-size:30px;letter-spacing:6px;color:#7ee2a8;font-weight:700;text-align:center;margin-bottom:26px}
.foto{width:100%%;border-radius:22px;margin-bottom:30px;box-shadow:0 10px 30px rgba(0,0,0,.5)}
.titulo{font-size:%(ft)dpx;font-weight:800;line-height:1.15;text-align:center;margin-bottom:34px}
.sub{font-size:40px;font-weight:700;text-align:center;color:#ffd84d;margin:-18px 0 30px}
.lineas{display:flex;flex-direction:column;gap:%(gap)dpx}
.l{font-size:%(fl)dpx;line-height:1.25;background:rgba(255,255,255,.06);border-left:6px solid #2ecc71;
 border-radius:14px;padding:16px 22px}
.cuota{margin-top:30px;display:flex;gap:18px;justify-content:center;flex-wrap:wrap}
.cuota div{font-size:42px;font-weight:800;background:#2ecc71;color:#06140c;border-radius:16px;padding:14px 26px}
.cuota div.b{background:#ffd84d}
.dato{margin-top:28px;font-size:33px;line-height:1.3;color:#cfe9da;text-align:center}
.pie{margin-top:auto;display:flex;justify-content:space-between;font-size:28px;color:#8fb3a0;padding-top:24px}
.oculto{visibility:hidden}
.v{justify-content:center}
.v .marca{font-size:36px}
.v .pie{position:absolute;bottom:70px;left:70px;right:70px;margin:0}
"""


def partes(texto):
    filas = [f.strip() for f in texto.split("\n")]
    titulo = filas[0]
    sub, lineas, cuota, dato = None, [], [], None
    for f in filas[1:]:
        if not f or f.startswith(("🔞", "🍀 ¿LA", "¡Combina")):
            continue
        if f.startswith("💥 COMBI DEL PARTIDO"):
            sub = f
        elif f.startswith(("🎯", "💶")):
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
    titulo, sub, lineas, cuota, dato = partes(p["texto"])
    w, h = (1080, 1920) if vertical else (1080, 1350)
    n = len(lineas)
    fl = 40 if n <= 5 else 35 if n <= 7 else 31
    if vertical:
        fl += 8
    gap = 14 if n <= 7 else 10
    if foto_b64 and not vertical:   # con foto de escudos hay menos sitio en 1080x1350
        fl -= 4
        gap = 10
    css = CSS % {"w": w, "h": h, "pad": 70 if vertical else 50, "ft": 64 if vertical else 52, "fl": fl, "gap": gap}
    total = 1 + n + 2
    ver = total if mostrar is None else mostrar

    def cls(i):
        return "" if i < ver else " oculto"
    e = html.escape
    partes_html = ['<div class="marca">COMBILOCAS</div>']
    if foto_b64:
        partes_html.append(f'<img class="foto" src="data:image/jpeg;base64,{foto_b64}">')
    partes_html.append(f'<div class="titulo">{e(titulo)}</div>')
    if sub:
        partes_html.append(f'<div class="sub">{e(sub)}</div>')
    partes_html.append('<div class="lineas">' + "".join(
        f'<div class="l{cls(1 + i)}">{e(l)}</div>' for i, l in enumerate(lineas)) + "</div>")
    if cuota:
        partes_html.append(f'<div class="cuota{cls(1 + n)}">' + "".join(
            f'<div class="{"b" if c.startswith("💶") else ""}">{e(c)}</div>' for c in cuota) + "</div>")
    if dato:
        partes_html.append(f'<div class="dato{cls(2 + n)}">{e(dato)}</div>')
    partes_html.append('<div class="pie"><span>@combilocas</span><span>🔞 +18 · Juega con responsabilidad</span></div>')
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
        pagina.add_style_tag(content=f"html{{background:#070b09}} body{{overflow:visible;transform:scale({escala});transform-origin:top center}}")
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
body{margin:0;width:1080px;height:608px;background:#101010;display:flex;align-items:center;justify-content:center;
font-family:-apple-system,"Helvetica Neue",Arial,sans-serif}
.c{width:980px;height:470px;border-radius:44px;background:linear-gradient(180deg,#2a2622,#1d1b19);display:flex;
align-items:center;justify-content:space-between;padding:0 70px;box-sizing:border-box;color:#fff;position:relative}
.eq{display:flex;flex-direction:column;align-items:center;gap:26px;width:260px}
.eq img{width:190px;height:190px;object-fit:contain}
.eq b{font-size:36px;font-weight:600;text-align:center;line-height:1.1}
.m{text-align:center}.m b{font-size:84px;font-weight:700;display:block}.m span{font-size:38px;color:#b9b4ae}
.liga{position:absolute;top:30px;left:0;right:0;text-align:center;font-size:28px;letter-spacing:4px;color:#8f8a84}
</style></head><body><div class="c"><div class="liga">{liga}</div>
<div class="eq"><img src="{logo_l}"><b>{local}</b></div>
<div class="m"><b>{hora}</b><span>{dia}</span></div>
<div class="eq"><img src="{logo_v}"><b>{visitante}</b></div></div></body></html>"""


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
    return (f'<div style="width:190px;height:190px;border-radius:50%;background:#3a3631;display:flex;'
            f'align-items:center;justify-content:center;font-size:70px;font-weight:700">{html.escape(ini)}</div>')


def tarjeta(p, pagina):
    """27/10: foto del partido para las combis de un solo partido (escudos, hora y día), como las que
    mejor funcionaron en Threads. → publicaciones/media/{id}.tarjeta.jpg"""
    import html
    t = p["tarjeta"]
    ini = datetime.fromisoformat(t["fecha"])
    hoy = datetime.fromisoformat(p["fecha"][:10])
    dias = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
    dia = "Hoy" if ini.date() == hoy.date() else "Mañana" if (ini.date() - hoy.date()).days == 1 else dias[ini.weekday()]
    doc = TARJETA
    for k, v in {"liga": t.get("liga") or "", "local": t["local"], "visitante": t["visitante"],
                 "hora": f"{ini:%H:%M}", "dia": dia}.items():
        doc = doc.replace("{" + k + "}", html.escape(str(v)))
    for k, nombre in (("logo_l", t["local"]), ("logo_v", t["visitante"])):
        doc = doc.replace('<img src="{' + k + '}">', escudo(t.get(k), nombre))
    pagina.set_viewport_size({"width": 1080, "height": 608})
    pagina.goto("about:blank")
    pagina.set_content(doc, wait_until="networkidle")
    pagina.wait_for_timeout(300)
    out = MEDIA / f"{p['id']}.tarjeta.jpg"
    pagina.screenshot(path=str(out), type="jpeg", quality=92)
    return out


def generar(p, pagina):
    MEDIA.mkdir(parents=True, exist_ok=True)
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


def main():
    cola = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    ids = set(sys.argv[2:]) - {"--pendientes"}
    pendientes = "--pendientes" in sys.argv   # solo los que aún no han salido y cuyo texto ha cambiado
    if pendientes:
        import hashlib
        from datetime import datetime
        from zoneinfo import ZoneInfo
        ahora = datetime.now(ZoneInfo("Europe/Madrid")).strftime("%Y-%m-%dT%H:%M")
        huella = lambda p: hashlib.sha1((p["texto"] + str(p.get("foto"))).encode()).hexdigest()[:12]
        cola = [p for p in cola if p["fecha"] > ahora and not (
            (MEDIA / f"{p['id']}.mp4").exists() and (MEDIA / f"{p['id']}.huella").exists()
            and (MEDIA / f"{p['id']}.story.jpg").exists()
            and (MEDIA / f"{p['id']}.huella").read_text() == huella(p))]
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
