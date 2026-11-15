"""
15/11 (Marcos: «el formato INFORMACIÓN TOP me gusta, pero hay que hacerlo bien»).
Busca en las noticias (datos/noticias.json) una historia de verdad que mueva un partido de hoy o mañana: brote de
virus, plaga de bajas, impagos/huelga, juveniles o suplentes… Solo vale si la cuentan AL MENOS 2 medios distintos y
el titular nombra al equipo (ya nos colaron una falsa baja de Lamine por un titular). Entonces prepara el post
«⚠️ INFORMACIÓN TOP» a favor del rival y se lo manda a Marcos con las fuentes: SOLO sale si le da a «✅ Publicar».
Como mucho uno cada 3 días, para que no pierda fuerza.
"""
import hashlib
import json
import re
import unicodedata
from datetime import datetime, timedelta

from bot import DATOS, MADRID, RAIZ, leer

COLA = RAIZ / "publicaciones" / "cola.json"
ESTADO = DATOS / "info_top.json"
CADA = timedelta(days=3)
# familia → (expresión, titular corto del post)
CRISIS = {
    "virus": (r"virus|gastroenteritis|intoxicaci[oó]n|brote|gripe", "brote de virus en la plantilla"),
    "bajas": (r"\b(?:[6-9]|1\d|seis|siete|ocho|nueve|diez|once|doce) bajas|plaga de bajas|enfermer[ií]a llena|"
              r"plantilla diezmada|bajo m[ií]nimos|en cuadro", "plaga de bajas"),
    "impagos": (r"impago|sin cobrar|huelga|plante de la plantilla", "crisis interna: impagos y plante"),
    "rotacion": (r"juveniles|filial|equipo b\b|rotaciones masivas|todos suplentes|once alternativo", "sale con un once alternativo"),
}


def _n(t):
    return unicodedata.normalize("NFKD", t or "").encode("ascii", "ignore").decode().lower()


def candidatos(noticias, partidos, ahora):
    """Partidos con una crisis contada por ≥2 medios en las últimas 48 h, con el titular nombrando al equipo."""
    desde = (ahora - timedelta(hours=48)).strftime("%Y-%m-%dT%H:%M")
    from plantillas import es
    salida = []
    for p in partidos:
        for lado in ("local", "visitante"):
            eq = p[lado]
            nombres = {_n(eq), _n(es(eq))}
            for fam, (rx, corto) in CRISIS.items():
                hits = [x for x in noticias.get(str(p["id"]), [])
                        if x.get("fecha", "") >= desde and re.search(rx, _n(x["titulo"]))
                        and any(nm and nm in _n(x["titulo"]) for nm in nombres)]
                medios = {x.get("fuente") for x in hits}
                if len(medios) >= 2:
                    salida.append({"partido": p, "lado": lado, "familia": fam, "corto": corto, "noticias": hits})
    return salida


def pick_a_favor(p, lado_afectado):
    """A favor del rival del equipo en crisis: «Gana X» si su cuota es razonable (1,30–2,50); si no, «X o empate»."""
    from plantillas import es
    rival = "visitante" if lado_afectado == "local" else "local"
    c = p.get("cuotas_bet365") or {}
    get = lambda m, k: next((float(v) for n, v in c.get(m, []) if n == k), None)
    gana = get("Match Winner", "Home" if rival == "local" else "Away")
    dc = get("Double Chance", "Home/Draw" if rival == "local" else "Draw/Away")
    nombre = es(p[rival])
    if gana and 1.30 <= gana <= 2.50:
        return f"Gana {nombre}", gana, f"{p['id']}|Match Winner|{'Home' if rival == 'local' else 'Away'}"
    if dc and 1.30 <= dc <= 1.80:
        return f"{nombre} o empate", dc, f"{p['id']}|Double Chance|{'Home/Draw' if rival == 'local' else 'Draw/Away'}"
    return None


def main(ahora=None):
    ahora = ahora or datetime.now(MADRID)
    if not 9 <= ahora.hour < 22:
        return None
    est = leer(ESTADO, {}) or {}
    if est.get("ultimo") and ahora - datetime.fromisoformat(est["ultimo"]) < CADA:
        return None
    hoy, manana = ahora.strftime("%Y-%m-%d"), (ahora + timedelta(days=1)).strftime("%Y-%m-%d")
    d = leer(DATOS / "resumen_proximos.json", []) or []
    partidos = [p for p in (d if isinstance(d, list) else d.get("partidos", []))
                if p["fecha"][:10] in (hoy, manana) and datetime.fromisoformat(p["fecha"]).astimezone(MADRID) > ahora + timedelta(minutes=45)]
    vistos = set(est.get("vistos", []))
    from plantillas import es
    for c in candidatos(leer(DATOS / "noticias.json", {}) or {}, partidos, ahora):
        p = c["partido"]
        k = f"{p['id']}|{c['lado']}|{c['familia']}"
        if k in vistos:
            continue
        pk = pick_a_favor(p, c["lado"])
        if not pk:
            continue
        texto_pick, cuota, sel = pk
        ini = datetime.fromisoformat(p["fecha"]).astimezone(MADRID)
        cuando = "hoy" if ini.strftime("%Y-%m-%d") == hoy else "mañana"
        eq = es(p[c["lado"]])
        lineas = [f"👨‍💻 {x['titulo']}" for x in c["noticias"][:3]]
        texto = (f"⚠️ INFORMACIÓN TOP\n\n⚽ {es(p['local'])} – {es(p['visitante'])} · {cuando} {ini:%H:%M}\n\n"
                 f"🚨 {eq}: {c['corto']}\n\n" + "\n".join(lineas) +
                 f"\n\n🍀 {texto_pick} @{cuota:.2f}".replace(".", ",") + "\n\n📉 Estas cuotas bajan rápido: entrad pronto 🔥")
        fuentes = "\n".join(f"• {x.get('fuente')}: {x['titulo']}\n  {x.get('link', '')}" for x in c["noticias"][:4])
        aviso = (f"🕵️ Posible INFORMACIÓN TOP ({len({x.get('fuente') for x in c['noticias']})} medios):\n{fuentes}\n\n"
                 "Revisa que la noticia es buena y reescribe las líneas si hace falta (las 👨‍💻 son los titulares). "
                 "Solo sale si le das a Publicar.")
        pid = f"{hoy}-info-top-{p['id']}-{hashlib.md5(k.encode()).hexdigest()[:5]}"
        from plantillas import datos_tarjeta   # 15/11 (Marcos): siempre con escudos o banderas
        tarjeta = datos_tarjeta({"picks": [{"partido_id": p["id"]}], "local": p["local"], "visitante": p["visitante"],
                                 "fecha": ini.strftime("%Y-%m-%dT%H:%M"), "competicion": p.get("competicion")})
        cola = leer(COLA, []) or []
        cola.append({"id": pid, "fecha": ahora.strftime("%Y-%m-%dT%H:%M"), "texto": texto, "foto": None,
                     "origen": "info_top", "directo": True, "requiere_ok": True, "aviso": aviso,
                     "sel": [sel], "cuotas": [cuota], "partido_id": p["id"],
                     **({"tarjeta": tarjeta} if tarjeta else {})})
        COLA.write_text(json.dumps(cola, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        est = {"ultimo": ahora.isoformat(), "vistos": sorted(vistos | {k})[-200:]}
        ESTADO.write_text(json.dumps(est, ensure_ascii=False) + "\n", encoding="utf-8")
        print(f"Info top preparada (espera OK): {pid}")
        return pid
    print("Info top: nada que valga")
    return None


if __name__ == "__main__":
    main()
