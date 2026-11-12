"""Balance diario del panel (combis) y post nocturno con los PICKS del día (28/10: sin combis ni pendientes)."""
import json
from datetime import datetime

from bot import MADRID, RAIZ, leer

DIAS = ['LUNES', 'MARTES', 'MIÉRCOLES', 'JUEVES', 'VIERNES', 'SÁBADO', 'DOMINGO']
COLA = RAIZ / 'publicaciones' / 'cola.json'


def balance(posts, dia):
    filas, vistos = [], set()
    for p in posts:
        titulo = p['titulo'].lstrip()
        # 26/10: el mismo post repetido (o su versión corregida) cuenta una sola vez
        clave = titulo.upper()
        if 'COMBI LOCAS' in clave:   # 27/10: varias combis de partido comparten título («✅ COMBI LOCAS | SERIE A»)
            clave += '|' + ','.join(sorted({x.get('partido') or '' for x in p.get('picks', [])}))
        if clave in vistos:
            continue
        # El emoji 📊 también identifica combis reales; no descartar esas selecciones.
        # Las previas de mañana no pertenecen al balance del día en que se anuncian.
        # 27/10: «✅ COMBI LOCAS» sí cuenta; solo fuera los posts de ¡VERDE! y las listas (quién gana, exactos)
        if (p['fecha'][:10] != dia or titulo.startswith(('🔄', '📋')) or p.get('lista')
                or (titulo.startswith('✅') and 'VERDE' in titulo.upper()) or 'verde-auto' in p['id'] or 'rojo-auto' in p['id']
                or 'BALANCE' in titulo.upper() or 'picks-manana' in p['id']
                or 'PARA MAÑANA' in titulo.upper()):
            continue
        estados = [x['estado'] for x in p.get('picks', [])]
        estado = p['estado']
        if estado not in ('verde', 'rojo', 'no_jugo', 'sin_datos'):
            if 'no_jugo' in estados:
                estado = 'no_jugo'
            elif any(x.get('estado_partido') in ('FT', 'AET', 'PEN') and x['estado'] not in ('verde', 'rojo') for x in p.get('picks', [])):
                estado = 'sin_datos'
            else:
                estado = 'pendiente'
        vistos.add(clave)
        filas.append({'id': p['id'], 'titulo': p['titulo'], 'estado': estado, 'cuota': p.get('cuota')})
    cuentas = {e: sum(p['estado'] == e for p in filas) for e in ('verde', 'rojo', 'pendiente', 'sin_datos', 'no_jugo')}
    cuentas['sin_resolver'] = cuentas['pendiente'] + cuentas['sin_datos'] + cuentas['no_jugo']
    # 27/10: también las selecciones publicadas (cada una una vez aunque vaya en varias combis o listas)
    sel = {}
    for p in posts:
        t = p['titulo'].lstrip()
        if (p['fecha'][:10] != dia or 'verde-auto' in p['id'] or (t.startswith('✅') and 'VERDE' in t.upper())
                or 'picks-manana' in p['id'] or 'PARA MAÑANA' in t.upper()):
            continue
        for x in p.get('picks', []):
            if x.get('exacto'):   # 27/10 (Marcos): los resultados exactos no cuentan en acertados/fallados
                continue
            sel[clave_pick(x)] = x.get('estado')   # 28/10: el mismo pick escrito de otra forma cuenta una vez
    picks = {'verde': sum(e == 'verde' for e in sel.values()), 'rojo': sum(e == 'rojo' for e in sel.values()),
             'total': len(sel)}
    resultado = {'dia': dia, 'total': len(filas), 'cuentas': cuentas, 'combis': filas, 'picks': picks}
    resultado['texto'] = texto_balance(resultado)
    return resultado


def texto_balance(b):
    c = b['cuentas']
    iconos = {'verde': '✅', 'rojo': '❌', 'pendiente': '⏳', 'sin_datos': '❔', 'no_jugo': '➖'}
    nombres = {'pendiente': 'pendiente', 'sin_datos': 'faltan datos', 'no_jugo': 'jugador sin participación'}
    fecha = datetime.fromisoformat(b['dia'])
    resueltas = c['verde'] + c['rojo']
    lineas = [f"📊 BALANCE DEL {DIAS[fecha.weekday()]}: {c['verde']} DE {resueltas} EN VERDE 📊", '']
    for p in b['combis']:
        cuota = f" · {p['cuota']:.2f}".replace('.', ',') if p.get('cuota') else ''
        motivo = f" · {nombres[p['estado']]}" if p['estado'] in nombres else ''
        lineas.append(f"{iconos[p['estado']]} {p['titulo']}{cuota}{motivo}")
    lineas += ['', f"✅ {c['verde']} acertadas · ❌ {c['rojo']} falladas · ⏳ {c['sin_resolver']} sin resolver"]
    if c['no_jugo']:
        lineas.append('Los jugadores sin participación no se cuentan como aciertos ni fallos.')
    return '\n'.join(lineas)


def clave_pick(x):
    """El mismo pick escrito de dos formas («Lazio o empate» / «Lazio — Gana o empata») cuenta una vez."""
    s = (x.get('texto') or '').strip().lower()
    s = s.replace(' — gana o empata', ' o empate')
    if s.endswith(' — gana'):
        s = 'gana el ' + s[:-len(' — gana')]
    return f"{x.get('partido_id')}|{s}"


def picks_dia(posts, dia):
    """28/10 (Marcos): el resumen de la noche es de PICKS, no de combis (una combi se pierde por una pata).
    Solo los picks ya resueltos (verde/rojo) de partidos terminados; nada de «pendiente»."""
    vistos, salida, en_juego = set(), [], 0
    for p in posts:
        t = p['titulo'].lstrip()
        if (p['fecha'][:10] != dia or 'verde-auto' in p['id'] or (t.startswith('✅') and 'VERDE' in t.upper())
                or 'picks-manana' in p['id'] or 'PARA MAÑANA' in t.upper() or 'BALANCE' in t.upper()):
            continue
        for x in p.get('picks', []):
            if x.get('exacto') or not x.get('partido_id'):
                continue
            k = clave_pick(x)
            if k in vistos:
                continue
            if x.get('estado') in ('verde', 'rojo') and x.get('estado_partido') in ('FT', 'AET', 'PEN'):
                vistos.add(k)
                salida.append({'texto': x['texto'], 'estado': x['estado']})
            elif x.get('estado_partido') not in (None, 'NS', 'TBD', 'PST', 'FT', 'AET', 'PEN'):
                en_juego += 1
    salida.sort(key=lambda x: x['estado'] != 'verde')   # primero los verdes
    return salida, en_juego


TIPOS = (('tarjetas', 'tarjeta'), ('córners', 'córner'), ('faltas', 'falta'), ('tiros', 'tiro'),
         ('goles', 'gol'), ('goles', 'marca'))


def tipo_pick(texto):
    s = texto.lower()
    return next((n for n, clave in TIPOS if clave in s), 'ganadores')


LISTAS = ('ganadores', 'marcadores', 'lista', 'verde', 'balance', 'rojo', 'picks-manana', 'exactos')
MIN_VERDES = 1
MIN_MOSTRAR = 0.6   # un % o un «x de y» solo sale si es bueno (60 % o más)


def _cuota_post(pid, cola):
    """La cuota publicada de un post (la de «Cuota @x» o la de su único pick «@x»)."""
    import re
    p = next((x for x in cola if x.get('id') == pid), None)
    if not p:
        return None
    m = re.search(r'Cuota @\s*(\d+[.,]\d+)', p.get('texto') or '') \
        or re.search(r'\bx(\d+[.,]\d+)', p.get('texto') or '') or re.search(r'@\s*(\d+[.,]\d+)', p.get('texto') or '')
    return float(m.group(1).replace(',', '.')) if m else None


def posts_dia(posts, dia, cola=()):
    """13/11: los posts del día (no listas ni verdes) ya resueltos: [(id, picks, estado, cuota)]."""
    out = []
    for p in posts:
        if p['fecha'][:10] != dia or p.get('lista') or any(k in p['id'] for k in LISTAS):
            continue
        ps = [x for x in p.get('picks', []) if not x.get('exacto')]
        if ps and p.get('estado') in ('verde', 'rojo'):
            out.append((p['id'], ps, p['estado'], _cuota_post(p['id'], cola) or p.get('cuota')
                        or (ps[0].get('cuota') if len(ps) == 1 else None)))
    return out


def textos_picks(picks, dia, posts=(), cola=()):
    """13/11 (Marcos: «poner no sé cuántos fallados queda muy feo… busca una manera para que quede bien» y luego «los
    fallados tienen que salir, pero no pongas la ❌»). Todo como «x de y» (sin ❌ ni «fallados»), el % solo si es bueno
    (≥ 60 %), los picks sueltos aparte de las combis y la lista de lo que salió en verde con su cuota."""
    v, n = sum(x['estado'] == 'verde' for x in picks), len(picks)
    if v < MIN_VERDES:   # un día con 1 o 2 verdes no luce: mejor no sacar resumen
        return None, None
    tipos = {}
    for x in picks:
        c = tipos.setdefault(tipo_pick(x['texto']), [0, 0])
        c[0] += x['estado'] == 'verde'
        c[1] += 1
    bueno = lambda a, b: b and a / b >= MIN_MOSTRAR
    fecha = datetime.fromisoformat(dia)
    # 13/11 (Marcos: «los fallados tienen que salir, pero no pongas la ❌: que no se vea tan mal»): «x de y», sin ❌
    lineas = [f"📊 RESUMEN DEL {DIAS[fecha.weekday()]} 🍀", '',
              f"✅ {v} de {n} picks en verde" + (f" · {round(100 * v / n)} %" if bueno(v, n) else '')]
    rp = posts_dia(posts, dia, cola)
    sueltos = [x for x in rp if len(x[1]) == 1]
    sv = sum(x[2] == 'verde' for x in sueltos)
    if sueltos:
        lineas.append(f"🎯 Picks sueltos: {sv} de {len(sueltos)}")
    mejores = sorted((k for k in tipos if k != 'ganadores' and tipos[k][1] >= 2 and bueno(*tipos[k])),
                     key=lambda k: (-tipos[k][0] / tipos[k][1], -tipos[k][1]))[:2]
    if mejores:
        lineas.append("🔥 Lo mejor: " + " · ".join(f"{k} {tipos[k][0]}/{tipos[k][1]}" for k in mejores))
    if 'ganadores' in tipos and tipos['ganadores'][1] >= 3:
        lineas.append(f"⚽ Ganadores: {tipos['ganadores'][0]}/{tipos['ganadores'][1]}")
    verdes = sorted((x for x in rp if x[2] == 'verde'), key=lambda x: -(x[3] or 0))
    if verdes:
        lineas += ['', '💚 Para dentro:']
        for _, ps, _, cuota in verdes[:6]:
            t = ps[0]['texto'] if len(ps) == 1 else (" + ".join(x['texto'] for x in ps) if len(ps) == 2
                                                       else f"Combi de {len(ps)} partidos")
            c = f" @{cuota:.2f}".replace('.', ',') if cuota else ''
            lineas.append(f"✅ {t}{c}")
    lineas += ['', '🔔 Mañana más: activad las notificaciones 👀']
    texto = '\n'.join(lineas)
    if len(texto) > 490:   # Threads: 500 caracteres
        texto = '\n'.join(l for l in lineas if not l.startswith('✅ ') or l.startswith('✅ ' + str(v)))
    return texto, texto


def main():
    ahora = datetime.now(MADRID)
    hoy = ahora.strftime('%Y-%m-%d')
    pid = f'{hoy}-balance-auto'
    cola = leer(COLA, []) or []
    if ahora.strftime('%H:%M') < '23:15' or any(p['id'] in (pid, f'{hoy}-balance') for p in cola):
        return
    datos = leer(RAIZ / 'docs/datos.json', {}) or {}
    # No publicar un balance basado en una copia antigua del panel.
    generado = datos.get('generado_iso')
    if not generado or (ahora - datetime.fromisoformat(generado)).total_seconds() > 20 * 60:
        return
    picks, en_juego = picks_dia(datos.get('publicados_hoy', []), hoy)
    if not picks or (en_juego and ahora.strftime('%H:%M') < '23:45'):
        return
    texto, _ = textos_picks(picks, hoy, datos.get('publicados_hoy', []), cola)
    if not texto:   # 13/11: si no hay nada en verde, no sale
        return
    cola.append({'id': pid, 'fecha': ahora.strftime('%Y-%m-%dT%H:%M'), 'texto': texto,
                 'foto': None, 'origen': 'bot', 'directo': True, 'facebook': 'texto', 'sin_instagram': True})
    COLA.write_text(json.dumps(cola, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print('Resumen de picks del día en cola')


if __name__ == '__main__':
    main()
