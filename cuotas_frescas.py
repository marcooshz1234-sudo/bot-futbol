"""
Cuotas frescas antes de publicar · que ninguna cuota publicada esté vieja.

En el bucle de publicación (cada ~5 min): para los posts automáticos que salen en los próximos
90 minutos, vuelve a pedir a la API las cuotas de bet365 de sus partidos (1 petición por partido,
como mucho una vez cada 30 min) y, si alguna selección ha cambiado, corrige su cuota, la cuota
total y el "10€ → X€" del texto, y vuelve a generar la imagen y el reel para que coincidan.
La escalera no se toca (su apuesta se fija al publicarla).
"""
import json
import os
import re
from datetime import datetime, timedelta

from bot import API, DATOS, MADRID, RAIZ, leer

AUTO = RAIZ / "publicaciones" / "auto.json"
CACHE = DATOS / "cuotas_frescas.json"
VENTANA = timedelta(minutes=90)
CADUCA = timedelta(minutes=30)
CAMBIO_MIN = 0.03


def num(c):
    return f"{c:.2f}".replace(".", ",")


def cuotas_partido(api, pid, cache, ahora):
    c = cache.get(str(pid))
    if c and datetime.fromisoformat(c["hora"]) > ahora - CADUCA:
        return c["cuotas"]
    cuotas = {}
    for item in api.get("odds", fixture=pid, bookmaker=8):
        for casa in item.get("bookmakers") or []:
            for b in casa.get("bets") or []:
                cuotas[b["name"]] = {str(v.get("value")): float(v["odd"]) for v in b.get("values") or [] if v.get("odd")}
    cache[str(pid)] = {"hora": ahora.isoformat(), "cuotas": cuotas}
    return cuotas


def main():
    clave = os.environ.get("API_FOOTBALL_KEY")
    if not clave or not AUTO.exists():
        return
    ahora = datetime.now(MADRID)
    auto = json.loads(AUTO.read_text(encoding="utf-8"))
    enviados = leer(RAIZ / "publicaciones" / "enviados.json", {}) or {}
    cache = leer(CACHE, {}) or {}
    api, cambiados = None, []
    for p in auto:
        if (enviados.get(p["id"]) or {}).get("enviado") or not p.get("sel") or "escalera" in p["id"]:
            continue
        cuando = datetime.fromisoformat(p["fecha"]).replace(tzinfo=MADRID)
        if not (ahora <= cuando <= ahora + VENTANA):
            continue
        api = api or API(clave)
        lineas = p["texto"].split("\n")
        hubo = False
        for i, l in enumerate(lineas):
            m = re.match(r"^(✅(\d+)\. .*? · )(\d+,\d\d)$", l)
            if not m or int(m.group(2)) > len(p["sel"]):
                continue
            pid, mercado, opcion = p["sel"][int(m.group(2)) - 1].split("|", 2)
            nueva = cuotas_partido(api, pid, cache, ahora).get(mercado, {}).get(opcion)
            vieja = float(m.group(3).replace(",", "."))
            if nueva and abs(nueva - vieja) >= CAMBIO_MIN:
                lineas[i] = m.group(1) + num(nueva)
                hubo = True
                print(f"Cuota corregida en {p['id']}: {opcion} {vieja} → {nueva}")
        # 27/10: los posts nuevos no llevan la cuota en cada línea; van en p["cuotas"]
        if p.get("cuotas") and len(p["cuotas"]) == len(p["sel"]) and not re.search(r" · \d+,\d\d$", p["texto"], re.M):
            for k, s in enumerate(p["sel"]):
                pid, mercado, opcion = s.split("|", 2)
                nueva = cuotas_partido(api, pid, cache, ahora).get(mercado, {}).get(opcion)
                vieja = p["cuotas"][k]
                if nueva and vieja and abs(nueva - vieja) >= CAMBIO_MIN:
                    p["cuotas"][k] = nueva
                    hubo = True
                    print(f"Cuota corregida en {p['id']}: {opcion} {vieja} → {nueva}")
        if not hubo:
            continue
        legs = [float(x.replace(",", ".")) for x in re.findall(r"^✅\d+\. .*? · (\d+,\d\d)$", "\n".join(lineas), re.M)] \
            or [x for x in (p.get("cuotas") or []) if x]
        total = 1.0
        for c in legs:
            total *= c
        # 27/10: combis de partido («[x1.40]» en cada pata) y patas del mismo partido: cuota real de «Crear apuesta»
        if p.get("cuotas") and len(p["cuotas"]) == len(p["sel"]):
            import combis_dia
            total = combis_dia.cuota_real_sel(p["sel"], p["cuotas"]) or total
            marcas = [i for i, l in enumerate(lineas) if re.search(r"\[x\d+\.\d\d\]$", l)]
            if len(marcas) == len(p["sel"]):
                for i, c in zip(marcas, p["cuotas"]):
                    lineas[i] = re.sub(r"\[x\d+\.\d\d\]$", f"[x{c:.2f}]", lineas[i])
            lineas = [re.sub(r"(Cuota total aprox\.: )\d+,\d\d", lambda m: m.group(1) + num(total), l) for l in lineas]
        # 26/10: el título también lleva la cuota ("x1,70") y se quedaba la vieja
        lineas[0] = re.sub(r"x\d+,\d\d", f"x{num(total)}", lineas[0], count=1)
        texto = "\n".join(lineas)
        texto = re.sub(r"🎯 Cuota total: \d+,\d\d", f"🎯 Cuota total: {num(total)}", texto)
        texto = re.sub(r"🎯 CUOTA \d+,\d\d", f"🎯 CUOTA {num(total)}", texto)
        texto = re.sub(r"💶 10€ → \d+,\d\d€", f"💶 10€ → {num(total * 10)}€", texto)
        p["texto"], p["cuotas_revisadas"] = texto, ahora.strftime("%Y-%m-%dT%H:%M")
        cambiados.append(p)
    CACHE.write_text(json.dumps({k: v for k, v in cache.items()
                                 if datetime.fromisoformat(v["hora"]) > ahora - timedelta(hours=6)}), encoding="utf-8")
    if not cambiados:
        return
    AUTO.write_text(json.dumps(auto, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    try:   # la imagen y el reel tienen que decir lo mismo que el texto
        import hashlib
        from playwright.sync_api import sync_playwright
        from imagenes import MEDIA, generar
        with sync_playwright() as pw:
            nav = pw.chromium.launch()
            pagina = nav.new_page()
            for p in cambiados:
                generar(p, pagina)
                (MEDIA / f"{p['id']}.huella").write_text(
                    hashlib.sha1((p["texto"] + str(p.get("foto"))).encode()).hexdigest()[:12])
            nav.close()
    except Exception as e:
        print(f"Cuotas frescas: no se pudo regenerar la imagen ({e}); Instagram esperará a tenerla")
        for p in cambiados:   # mejor sin imagen que con una imagen con cuotas viejas
            for ext in ("jpg", "mp4"):
                f = RAIZ / "publicaciones" / "media" / f"{p['id']}.{ext}"
                if f.exists():
                    f.unlink()


if __name__ == "__main__":
    main()
