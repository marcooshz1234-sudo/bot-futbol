"""12/11 (Marcos: «que las publicaciones de Threads pongan más fuegos, más tics verdes y más emojis de los que usábamos
antes, que daban tantas visitas. Estás dejando de hacer muchas cosas»).

Los posts que más vistas tuvieron en Threads (quién gana Champions 28.250, resultado de la semana 25.390, ganadores
Conference 23.445, combi Barça–Villa 11.950, escalera 8.113…) tenían: cabecera en MAYÚSCULAS con emojis a los dos lados,
cada pata con ✅ delante, «🎯 CUOTA … 💎», lo que se gana con 10 € y un cierre tipo «🟢 VERDE A VERDE 🟢».
Los de ahora salían más sosos («Vamos con la combi del jueves familia 🔥», patas sin ✅, «📈 Cuota @4,98», sin los 10 €).

Esto solo cambia el TEXTO DE THREADS (Telegram e Instagram siguen igual). Los verdes/rojos, balances y ganadores
ya llevan su formato y no se tocan.
"""
import hashlib
import re

NO_TOCAR = re.compile(r"verde|rojo|balance|ganadores|lista-europa|resultado|marcadores")
BANDERA = re.compile(r"^(?:[\U0001F1E6-\U0001F1FF]{2}|🏴[\U000E0061-\U000E007A]+\U000E007F|⚽|⭐)\s")
PARTIDO = re.compile(r"^(?:⚽|⭐|[\U0001F1E6-\U0001F1FF]{2})\s*(.+?)\s+[–-]\s+(.+?)\s+·\s+(.+)$")
CUOTA = re.compile(r"^📈\s*Cuota\s*@\s*(\d+[.,]\d+)\s*$")
PATA_CUOTA = re.compile(r"@\s*(\d+[.,]\d+)")
CIERRES = ["🟢 VERDE A VERDE 🟢", "🍀 ¿LA PINTAMOS DE VERDE? 👀💚", "🔥 ¡A POR ELLA, FAMILIA! 🔥",
           "✅ ¿QUIÉN SE LA JUEGA CON NOSOTROS? 👇", "💚 ¡A POR EL VERDE! 💚"]
TIENE_CIERRE = re.compile(r"VERDE A VERDE|PINTAMOS DE VERDE|QUIÉN LA LLEVABA|A POR ELLA|A POR EL VERDE|SE LA JUEGA", re.I)


def num(x):
    return float(x.replace(",", "."))


def coma(x):
    return f"{x:.2f}".replace(".", ",")


def elegir(lista, semilla):
    return lista[int(hashlib.sha1(semilla.encode()).hexdigest(), 16) % len(lista)]


def cabecera(linea):
    """«Vamos con la combi del jueves familia 🔥» → «🔥⚽ VAMOS CON LA COMBI DEL JUEVES FAMILIA 🔥»."""
    if not linea.strip() or linea.isupper():
        return linea
    limpia = re.sub(r"[\s🔥⚽🍀👀👇📊🤪]+$", "", linea).strip()
    limpia = re.sub(r"^[🔥⚽🍀🤪📊\s]+", "", limpia)
    return re.sub(r"X(\d)", r"x\1", f"🔥⚽ {limpia.upper()} 🔥")   # «X2,82» → «x2,82»


def estilo(texto, pid=""):
    if NO_TOCAR.search(pid):
        return texto
    lineas = texto.split("\n")
    out = []
    cuota_total = None
    patas_con_cuota = []
    for i, l in enumerate(lineas):
        s = l.strip()
        if i == 0:
            out.append(cabecera(l))
            continue
        m = CUOTA.match(s)
        if m:
            cuota_total = num(m.group(1))
            out.append(f"🎯 CUOTA {coma(cuota_total)} 💎 · 10€ → {coma(cuota_total * 10)}€")
            continue
        m = PARTIDO.match(s)
        if m and not s.startswith("🍀"):
            out.append(f"⭐ {m.group(1).upper()} vs {m.group(2).upper()} ⭐ · {m.group(3)}")
            continue
        if s.startswith("🍀 ") and not TIENE_CIERRE.search(s):
            c = PATA_CUOTA.search(s)
            if c:
                patas_con_cuota.append(num(c.group(1)))
            out.append("✅ " + s[2:].strip())
            continue
        if BANDERA.match(s) and not s.startswith("✅"):
            out.append("✅ " + s)
            continue
        if s.startswith("🧠 Stake"):
            out.append(s.replace("🧠 Stake", "🧠 STAKE"))
            continue
        out.append(l)
    # combi sin línea de cuota pero con la cuota en la cabecera («NATIONS LEAGUE · 3 PARTIDOS x2,82»)
    if cuota_total is None and not patas_con_cuota:
        m = re.search(r"\bx(\d+[.,]\d+)", out[0] if out else "", re.I)
        if m:
            cuota_total = num(m.group(1))
            while out and not out[-1].strip():
                out.pop()
            fin = next((j for j in range(len(out) - 1, -1, -1) if out[j].startswith("✅")), len(out) - 1)
            out[fin + 1:fin + 1] = ["", f"🎯 CUOTA {coma(cuota_total)} 💎 · 10€ → {coma(cuota_total * 10)}€"]
    # un pick suelto (una sola cuota y sin «Cuota @»): lo que se gana con 10 € justo después de la pata
    if cuota_total is None and len(patas_con_cuota) == 1:
        c = patas_con_cuota[0]
        for j, l in enumerate(out):
            if l.startswith("✅ ") and PATA_CUOTA.search(l):
                out.insert(j + 1, f"💶 10€ → {coma(c * 10)}€")
                break
    t = "\n".join(out).rstrip()
    if not TIENE_CIERRE.search(t):
        t += "\n\n" + elegir(CIERRES, pid or t)
    return t
