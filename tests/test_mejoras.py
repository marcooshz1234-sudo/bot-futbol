import json
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch
import os

import app_datos
import incidencias
import publicados
import resumen_dia
import redes
import publicar_telegram as telegram


class ProgresoTest(unittest.TestCase):
    def setUp(self):
        self.d = {'estado': '2H', 'local': {'id': 1, 'nombre': 'Local'}, 'visitante': {'id': 2, 'nombre': 'Visitante'},
                  'goles': [1, 0], 'descanso': [0, 0],
                  'stats': {'1': {'corners': 3}, '2': {'corners': 2}},
                  'jugadores': {'1': [{'nombre': 'M. Portero', 'min': 80, 'paradas': 1}]}}

    def test_objetivos_de_cuota_y_jugador(self):
        for texto, actual, objetivo in [('Más de 4,5 córners', 5, 5), ('Local saca 4 o más córners', 3, 4),
                                        ('Portero: 2+ paradas', 1, 2), ('Más de 1,5 goles', 1, 2),
                                        ('Ambos marcan', 1, 2), ('Gol en la 1ª parte', 0, 1)]:
            with self.subTest(texto=texto):
                r = publicados.progreso(publicados.entender(texto)[0], self.d)
                self.assertEqual((r['actual'], r['objetivo']), (actual, objetivo))

    def test_no_inventa_ceros_si_falta_la_estadistica(self):
        self.assertIsNone(publicados.progreso({'t': 'tiros_mas', 'n': 20.5}, self.d))
        self.d['jugadores']['1'][0]['min'] = 0
        self.assertIsNone(publicados.progreso({'t': 'jugador', 'jugador': 'Portero', 'campo': 'paradas', 'n': 2}, self.d))

    def test_fecha_de_madrid_tiene_offset_explicito(self):
        self.assertEqual(app_datos.fecha_iso('2026-10-24T19:00'), '2026-10-24T19:00:00+02:00')
        self.assertEqual(app_datos.fecha_iso('2026-10-26T19:00'), '2026-10-26T19:00:00+01:00')


class BalanceTest(unittest.TestCase):
    def test_combis_de_datos_cuentan_pero_previa_y_balance_no(self):
        base = {'fecha': '2026-10-24T18:00', 'estado': 'verde',
                'picks': [{'estado': 'verde', 'estado_partido': 'FT'}]}
        posts = [dict(base, id='datos', titulo='📊 COMBI DE DATOS'),
                 dict(base, id='estadistica', titulo='📊 COMBI ESTADÍSTICA'),
                 dict(base, id='2026-10-24-picks-manana', titulo='🔥 PICKS PARA MAÑANA'),
                 dict(base, id='balance-auto', titulo='📊 BALANCE DEL DÍA')]
        b = resumen_dia.balance(posts, '2026-10-24')
        self.assertEqual([p['id'] for p in b['combis']], ['datos', 'estadistica'])
        self.assertEqual(b['cuentas']['verde'], 2)

    def test_pendientes_no_jugados_y_sin_datos_no_son_fallos(self):
        posts = [{'id': str(i), 'fecha': '2026-10-24T18:00', 'titulo': f'Combi {i}', 'estado': estado,
                  'picks': [{'estado': leg, 'estado_partido': partido}]}
                 for i, (estado, leg, partido) in enumerate([('verde', 'verde', 'FT'), ('rojo', 'rojo', 'FT'),
                    ('pendiente', 'no_jugo', 'FT'), ('pendiente', 'sin_datos', 'FT'), ('pendiente', 'va_bien', '2H')])]
        posts += [dict(posts[0], id='otro-dia', fecha='2026-10-23T18:00')]
        b = resumen_dia.balance(posts, '2026-10-24')
        self.assertEqual(b['total'], 5)
        self.assertEqual(b['cuentas'], {'verde': 1, 'rojo': 1, 'pendiente': 1, 'no_jugo': 1, 'sin_datos': 1, 'sin_resolver': 3})
        self.assertIn('1 acertadas', b['texto'])
        self.assertIn('3 sin resolver', b['texto'])

    def test_resumen_no_se_encola_dos_veces(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); (root/'publicaciones').mkdir()
            cola = root/'publicaciones/cola.json'
            ahora = datetime(2026, 10, 24, 23, 35, tzinfo=redes.MADRID)
            (root/'docs').mkdir()
            (root/'docs/datos.json').write_text(json.dumps({'generado_iso': ahora.isoformat(), 'publicados_hoy': [
                {'id': 'uno', 'fecha': '2026-10-24T18:00', 'titulo': 'Combi', 'estado': 'verde',
                 'picks': [{'partido_id': 1, 'texto': 'Gana el Betis', 'estado': 'verde', 'estado_partido': 'FT'}]}]}))
            with patch.multiple(resumen_dia, RAIZ=root, COLA=cola), patch.object(resumen_dia, 'datetime') as dt:
                dt.now.return_value = ahora
                dt.fromisoformat.side_effect = datetime.fromisoformat
                resumen_dia.main(); resumen_dia.main()
            self.assertEqual(len(json.loads(cola.read_text())), 1)

    def test_resumen_solo_picks_sin_pendientes(self):
        pk = lambda i, t, e, ep='FT': {'partido_id': i, 'texto': t, 'estado': e, 'estado_partido': ep}
        posts = [{'id': 'loca', 'fecha': '2026-10-27T16:00', 'titulo': '🤪 LA LOCA', 'estado': 'rojo',
                  'picks': [pk(1, 'Lazio o empate', 'verde'), pk(2, 'Rayo gana alguna de las dos partes', 'rojo'),
                            pk(3, 'Monza marca', 'pendiente', None)]},
                 {'id': 'ganadores', 'fecha': '2026-10-27T01:00', 'titulo': '⚽ QUIÉN GANA HOY', 'estado': 'pendiente',
                  'picks': [pk(1, 'Lazio — Gana o empata', 'verde'), pk(4, 'Arsenal — Gana', 'rojo')]}]
        picks, en_juego = resumen_dia.picks_dia(posts, '2026-10-27')
        self.assertEqual([x['texto'] for x in picks], ['Lazio o empate', 'Rayo gana alguna de las dos partes', 'Arsenal — Gana'])
        texto, corto = resumen_dia.textos_picks(picks, '2026-10-27')
        self.assertIn('1 DE 3 EN VERDE', texto)
        self.assertNotIn('pendiente', texto.lower())
        self.assertNotIn('COMBI', texto.upper().replace('COMBILOCAS', ''))
        largo = [pk(i, f'Equipo número {i} gana el partido', 'verde') for i in range(40)]
        _, corto = resumen_dia.textos_picks(resumen_dia.picks_dia([dict(posts[0], picks=largo)], '2026-10-27')[0], '2026-10-27')
        self.assertLessEqual(len(corto), 500)
        self.assertIn('más en Telegram', corto)


class ReintentosTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name); self.pub=self.root/'publicaciones'; self.pub.mkdir()
        self.ahora = datetime.now(redes.MADRID)
        self.p = {'id': 'post', 'fecha': (self.ahora-timedelta(minutes=2)).isoformat(), 'texto': 'Combi',
                  'directo': True, 'error': 'Telegram 429: Too Many Requests',
                  'redes': {'threads': 'confirmado'}, 'errores_redes': {'facebook': '400: imagen no disponible'}}
        (self.pub/'cola.json').write_text(json.dumps([self.p]))
        self.clave = incidencias.identificador('post', 'telegram')

    def test_solicitud_se_deduplica_y_no_toca_otros_envios(self):
        self.assertIn('solicitado', incidencias.solicitar(self.root, self.clave, self.ahora))
        self.assertIn('ya está', incidencias.solicitar(self.root, self.clave, self.ahora))
        self.assertEqual(len(json.loads((self.pub/'reintentos.json').read_text())), 1)
        self.assertEqual(json.loads((self.pub/'cola.json').read_text())[0]['redes']['threads'], 'confirmado')

    def test_bloquea_envio_confirmado_pausa_y_post_antiguo(self):
        for p, control in [(dict(self.p, mensaje_id=123), {}), (self.p, {'pausa': True}),
                           (dict(self.p, fecha=(self.ahora-timedelta(hours=2)).isoformat()), {}),
                           (self.p, {'cancelados': ['post']})]:
            with self.subTest(p=p, control=control):
                self.assertIsNotNone(incidencias.motivo_bloqueo(p, 'telegram', control, self.ahora))

    def test_envio_ambiguo_no_se_reintenta(self):
        p = dict(self.p, error='Envío sin confirmación: comprueba el canal antes de repetir')
        self.assertIsNotNone(incidencias.motivo_bloqueo(p, 'telegram', {}, self.ahora))

    def test_worker_revalida_antes_de_llamar_y_registra_una_vez(self):
        incidencias.solicitar(self.root, self.clave, self.ahora)
        (self.pub/'control.json').write_text(json.dumps({'pausa': True}))
        with patch.object(telegram, 'main') as enviar:
            incidencias.procesar(self.root); incidencias.procesar(self.root)
            enviar.assert_not_called()
        estado = json.loads((self.pub/'reintentos_estado.json').read_text())
        self.assertEqual(len(estado), 1)
        self.assertEqual(next(iter(estado.values()))['resultado'], 'Publicaciones en pausa')

    def test_worker_envia_solo_el_objetivo_y_no_repite_solicitud(self):
        incidencias.solicitar(self.root, self.clave, self.ahora)
        with patch.object(telegram, 'main') as enviar, patch.dict(os.environ, {'TELEGRAM_TOKEN': 'simulado'}):
            incidencias.procesar(self.root); incidencias.procesar(self.root)
            enviar.assert_called_once_with(objetivo=('post', 'telegram'))

    def test_redes_reintenta_solo_la_red_fallida(self):
        with patch.multiple(redes, RAIZ=self.root, COLA=self.pub/'cola.json', AUTO=self.pub/'auto.json', FACEBOOK_ACTIVO=True,
                           CONTROL=self.pub/'control.json', ESTADO_AUTO=self.pub/'enviados_redes.json'), \
                patch.dict(os.environ, {'THREADS_TOKEN': 'simulado', 'FACEBOOK_TOKEN': 'simulado'}, clear=True), \
                patch.object(redes, 'threads') as threads, patch.object(redes, 'facebook', return_value='nuevo') as fb:
            redes.main(objetivo=('post', 'facebook'))
            threads.assert_not_called(); fb.assert_called_once()
        p=json.loads((self.pub/'cola.json').read_text())[0]
        self.assertEqual(p['redes'], {'threads': 'confirmado', 'facebook': 'nuevo'})
        self.assertNotIn('facebook', p.get('errores_redes', {}))


if __name__ == '__main__':
    unittest.main()

class PublicadorSeguroTest(unittest.TestCase):
    def test_timeout_de_envio_no_dispara_otra_peticion(self):
        from urllib.error import URLError
        with patch.object(telegram, 'urlopen', side_effect=URLError('timeout')) as request:
            with self.assertRaisesRegex(RuntimeError, 'sin confirmación'):
                telegram.api('simulado', 'sendMessage', {'chat_id': 1, 'text': 'prueba'})
            request.assert_called_once()

    def test_reintento_tg_conserva_id_y_no_envia_otro_post(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); pub=root/'publicaciones'; pub.mkdir()
            fecha=(datetime.now(redes.MADRID)-timedelta(minutes=1)).isoformat()
            cola=[{'id': 'objetivo', 'fecha': fecha, 'texto': 'Uno'}, {'id': 'otro', 'fecha': fecha, 'texto': 'Dos'}]
            ruta=pub/'cola.json'; ruta.write_text(json.dumps(cola))
            with patch.multiple(telegram, RAIZ=root, COLA=ruta, AUTOS=[], ENVIADOS=pub/'enviados.json', CONTROL=pub/'control.json'), \
                    patch.dict(os.environ, {'TELEGRAM_TOKEN': 'simulado', 'TELEGRAM_CANAL': 'simulado'}), \
                    patch.object(telegram, 'comprobar'), patch.object(telegram, 'time'), \
                    patch.object(telegram, 'api', return_value={'result': {'message_id': 777}}) as enviar:
                telegram.main(objetivo=('objetivo','telegram'))
                telegram.main(objetivo=('objetivo','telegram'))
                enviar.assert_called_once()
            resultado=json.loads(ruta.read_text())
            self.assertEqual(resultado[0]['mensaje_id'],777)
            self.assertNotIn('enviado',resultado[1])
