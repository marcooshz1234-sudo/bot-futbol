"""Reintentos pedidos por el dueño; se ejecutan en el único bucle publicador."""
import hashlib
import json
from datetime import datetime, timedelta

from bot import MADRID, leer

REDES = {'telegram', 'threads', 'instagram', 'facebook', 'instagram_reel'}


def identificador(pid, red):
    return hashlib.sha256(f'{pid}|{red}'.encode()).hexdigest()[:20]


def publicaciones(raiz):
    carpeta = raiz / 'publicaciones'
    cola = leer(carpeta / 'cola.json', []) or []
    tg = leer(carpeta / 'enviados.json', {}) or {}
    meta = leer(carpeta / 'enviados_redes.json', {}) or {}
    ids = {p['id'] for p in cola}
    return cola + [dict(p, **dict(tg.get(p['id'], {}), **meta.get(p['id'], {})))
                   for p in leer(carpeta / 'auto.json', []) or [] if p['id'] not in ids]


def motivo_bloqueo(p, red, control, ahora):
    if red not in REDES:
        return 'Red no reconocida'
    if control.get('pausa'):
        return 'Publicaciones en pausa'
    if p.get('borrar') or p.get('borrado') or p['id'] in control.get('cancelados', []):
        return 'Publicación cancelada o borrada'
    if (red == 'telegram' and (p.get('enviado') or p.get('mensaje_id'))) or (p.get('redes') or {}).get(red):
        return 'Ya publicada; no se volverá a enviar'
    fecha = datetime.fromisoformat(p['fecha']).replace(tzinfo=MADRID)
    limite = timedelta(minutes=55 if red == 'instagram_reel' else 45)
    if p.get('caducada') or ahora < fecha or ahora - fecha > limite:
        return 'Fuera de plazo; no se publican pronósticos antiguos'
    error = str(p.get('error') if red == 'telegram' else (p.get('errores_redes') or {}).get(red) or '')
    if not error:
        return 'No hay un fallo pendiente en esta red'
    if ambiguo(error):
        return 'Envío sin confirmación: comprueba la red antes de volver a publicar'
    if any(x in error.lower() for x in ('invalid token', 'invalid oauth', 'access blocked', 'access token', 'unauthorized', '401:')):
        return 'Hay que reconectar la cuenta antes de reintentar'
    return None


def ambiguo(error):
    return any(x in str(error).lower() for x in ('timed out', 'timeout', 'no responde', 'urlopen error',
                                                'connection reset', 'remote end closed', 'sin confirmación'))


def solicitar(raiz, clave, ahora=None):
    ahora = ahora or datetime.now(MADRID)
    control = leer(raiz / 'publicaciones/control.json', {}) or {}
    for p in publicaciones(raiz):
        for red in REDES:
            if identificador(p['id'], red) != clave:
                continue
            motivo = motivo_bloqueo(p, red, control, ahora)
            if motivo:
                return motivo
            ruta = raiz / 'publicaciones/reintentos.json'
            cola = leer(ruta, []) or []
            estado = leer(raiz / 'publicaciones/reintentos_estado.json', {}) or {}
            if any(r['clave'] == clave and r['id'] not in estado for r in cola):
                return 'Este reintento ya está solicitado'
            cola.append({'id': f'{clave}-{int(ahora.timestamp())}', 'clave': clave, 'post_id': p['id'],
                         'red': red, 'solicitado': ahora.isoformat()})
            ruta.write_text(json.dumps(cola[-100:], ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
            return 'Reintento solicitado. El publicador lo revisará en su siguiente ciclo; conservará las redes que ya recibieron el post.'
    return 'No encuentro esa incidencia; actualiza el panel'


def procesar(raiz):
    carpeta = raiz / 'publicaciones'
    ruta = carpeta / 'reintentos_estado.json'
    estado = leer(ruta, {}) or {}
    solicitudes = leer(carpeta / 'reintentos.json', []) or []
    for r in solicitudes:
        if r['id'] in estado:
            continue
        ahora = datetime.now(MADRID)
        p = next((p for p in publicaciones(raiz) if p['id'] == r['post_id']), None)
        motivo = 'Publicación no encontrada' if not p else motivo_bloqueo(p, r['red'], leer(carpeta / 'control.json', {}) or {}, ahora)
        if not motivo and ahora - datetime.fromisoformat(r['solicitado']) > timedelta(minutes=10):
            motivo = 'Solicitud caducada; revisa el estado antes de repetir'
        if not motivo:
            import os
            variable = {'telegram': 'TELEGRAM_TOKEN', 'threads': 'THREADS_TOKEN', 'facebook': 'FACEBOOK_TOKEN',
                        'instagram': 'INSTAGRAM_TOKEN', 'instagram_reel': 'INSTAGRAM_TOKEN'}[r['red']]
            if not os.environ.get(variable):
                motivo = 'Cuenta sin conectar'
        if not motivo:
            try:
                if r['red'] == 'telegram':
                    from publicar_telegram import main
                else:
                    from redes import main
                main(objetivo=(p['id'], r['red']))
                p = next(x for x in publicaciones(raiz) if x['id'] == r['post_id'])
                enviado = (p.get('mensaje_id') or p.get('enviado')) if r['red'] == 'telegram' else (p.get('redes') or {}).get(r['red'])
                motivo = 'Publicado' if enviado else 'Sigue fallando; revisa el motivo actualizado'
            except Exception:
                motivo = 'Reintento interrumpido; revisa el estado antes de repetir'
        estado[r['id']] = {'resultado': motivo, 'fecha': ahora.isoformat(), 'clave': r['clave'], 'post': r['post_id'], 'red': r['red']}
        ruta.write_text(json.dumps(estado, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


if __name__ == '__main__':
    from bot import RAIZ
    procesar(RAIZ)
