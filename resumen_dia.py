"""Balance diario del panel y post nocturno; las selecciones sin resolver se indican aparte."""
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
        if titulo.upper() in vistos:
            continue
        # El emoji 📊 también identifica combis reales; no descartar esas selecciones.
        # Las previas de mañana no pertenecen al balance del día en que se anuncian.
        if (p['fecha'][:10] != dia or titulo.startswith(('✅', '🔄', '📋'))
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
        vistos.add(titulo.upper())
        filas.append({'id': p['id'], 'titulo': p['titulo'], 'estado': estado, 'cuota': p.get('cuota')})
    cuentas = {e: sum(p['estado'] == e for p in filas) for e in ('verde', 'rojo', 'pendiente', 'sin_datos', 'no_jugo')}
    cuentas['sin_resolver'] = cuentas['pendiente'] + cuentas['sin_datos'] + cuentas['no_jugo']
    resultado = {'dia': dia, 'total': len(filas), 'cuentas': cuentas, 'combis': filas}
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
    b = balance(datos.get('publicados_hoy', []), hoy)
    if not b['total'] or (b['cuentas']['sin_resolver'] and ahora.strftime('%H:%M') < '23:30'):
        return
    cola.append({'id': pid, 'fecha': ahora.strftime('%Y-%m-%dT%H:%M'), 'texto': b['texto'], 'foto': None,
                 'origen': 'bot', 'directo': True, 'facebook': 'texto', 'sin_instagram': True})
    COLA.write_text(json.dumps(cola, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print('Resumen del día en cola')


if __name__ == '__main__':
    main()
