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
                or (titulo.startswith('✅') and 'VERDE' in titulo.upper()) or 'verde-auto' in p['id']
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


def textos_picks(picks, dia):
    """28/10 (Marcos): sin la lista de picks; % de acierto y lo mejor y lo peor por tipo de apuesta.
    El mismo texto para Telegram y Threads (cabe en 500 caracteres)."""
    v, n = sum(x['estado'] == 'verde' for x in picks), len(picks)
    tipos = {}
    for x in picks:
        c = tipos.setdefault(tipo_pick(x['texto']), [0, 0])
        c[0] += x['estado'] == 'verde'
        c[1] += 1
    pct = lambda k: tipos[k][0] / tipos[k][1]
    fmt = lambda k: f"{k} {tipos[k][0]}/{tipos[k][1]}"
    fecha = datetime.fromisoformat(dia)
    lineas = [f"📊 BALANCE DEL {DIAS[fecha.weekday()]} · {v} DE {n} PICKS EN VERDE 🍀", '',
              f"🎯 {round(100 * v / n)} % de acierto", f"✅ {v} acertados · ❌ {n - v} fallados", '']
    mejores = sorted((k for k in tipos if k != 'ganadores' and pct(k) >= 0.5), key=lambda k: (-pct(k), -tipos[k][1]))[:2]
    if mejores:
        lineas.append("🔥 Lo mejor: " + " · ".join(fmt(k) for k in mejores))
    if 'ganadores' in tipos:
        lineas.append(f"⚽ Ganadores: {tipos['ganadores'][0]}/{tipos['ganadores'][1]}")
    peores = sorted((k for k in tipos if tipos[k][1] >= 2 and pct(k) < 0.5 and k not in mejores), key=lambda k: (pct(k), -tipos[k][1]))
    if peores:
        lineas.append(f"😤 Lo peor: {fmt(peores[0])}")
    lineas += ['', '💚 Mañana más picks GRATIS en @combilocas', '🍀 ¿Cuántos llevabas tú? 👇']
    texto = '\n'.join(l for i, l in enumerate(lineas) if l or (i and lineas[i - 1]))
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
    texto, _ = textos_picks(picks, hoy)
    cola.append({'id': pid, 'fecha': ahora.strftime('%Y-%m-%dT%H:%M'), 'texto': texto,
                 'foto': None, 'origen': 'bot', 'directo': True, 'facebook': 'texto', 'sin_instagram': True})
    COLA.write_text(json.dumps(cola, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print('Resumen de picks del día en cola')


if __name__ == '__main__':
    main()
