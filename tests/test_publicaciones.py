import contextlib
import copy
import io
import json
import os
from datetime import datetime, timedelta
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import aciertos
import picks
import plantillas
import publicados
import publicar_telegram as telegram
import redes


class PublicacionesTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.raiz = Path(self.tmp.name)
        self.pub = self.raiz / 'publicaciones'
        self.pub.mkdir()
        self.post = {'id': 'prueba', 'fecha': (datetime.now(redes.MADRID) - timedelta(minutes=1)).strftime('%Y-%m-%dT%H:%M'),
                     'texto': 'Texto original', 'directo': True, 'foto': None}
        self.guardar('cola.json', [self.post])
        self.guardar('auto.json', [])

    def guardar(self, nombre, datos):
        (self.pub / nombre).write_text(json.dumps(datos))

    def ejecutar_redes(self, control, automatico=False):
        self.guardar('control.json', control)
        if automatico:
            self.guardar('cola.json', [])
            self.guardar('auto.json', [self.post])
        with patch.multiple(redes, RAIZ=self.raiz, COLA=self.pub / 'cola.json', AUTO=self.pub / 'auto.json',
                            CONTROL=self.pub / 'control.json', ESTADO_AUTO=self.pub / 'enviados_redes.json'), \
                patch.dict(os.environ, {'THREADS_TOKEN': 'simulado'}, clear=True), \
                patch.object(redes, 'threads', return_value='id-publicado') as enviar, \
                contextlib.redirect_stdout(io.StringIO()):
            redes.main()
            return enviar

    def test_pausa_detiene_redes(self):
        self.ejecutar_redes({'pausa': True}).assert_not_called()

    def test_cancelacion_detiene_manual_y_automatico(self):
        for auto in (False, True):
            with self.subTest(auto=auto):
                self.ejecutar_redes({'cancelados': ['prueba']}, auto).assert_not_called()

    def test_edicion_se_envia_y_se_guarda_id_sin_reescribir_origen(self):
        enviar = self.ejecutar_redes({'textos': {'prueba': 'Texto corregido'}})
        self.assertEqual(enviar.call_args.args[0]['texto'], 'Texto corregido')
        guardado = json.loads((self.pub / 'cola.json').read_text())[0]
        self.assertEqual(guardado['texto'], 'Texto original')
        self.assertEqual(guardado['redes']['threads'], 'id-publicado')
        self.assertNotIn('_texto_cambiado', guardado)

    def test_no_se_repite_una_red_ya_publicada(self):
        self.post['redes'] = {'threads': 'ya-publicado'}
        self.guardar('cola.json', [self.post])
        self.ejecutar_redes({}).assert_not_called()

    def test_foto_anterior_no_se_usa_con_texto_corregido(self):
        media = self.pub / 'media'
        media.mkdir()
        (media / 'prueba.jpg').write_bytes(b'imagen-anterior')
        (media / 'prueba.huella').write_text('huella-antigua')
        with patch.object(redes, 'RAIZ', self.raiz):
            self.assertIsNotNone(redes.url_media(self.post, 'jpg'))
            self.assertIsNone(redes.url_media(dict(self.post, texto='Corregido', _texto_cambiado=True), 'jpg'))

    def test_telegram_no_reescribe_texto_base_al_enviar_correccion(self):
        self.guardar('control.json', {'textos': {'prueba': 'Texto corregido'}})
        with patch.multiple(telegram, COLA=self.pub / 'cola.json', AUTOS=[], CONTROL=self.pub / 'control.json',
                            ENVIADOS=self.pub / 'enviados.json'), \
                patch.dict(os.environ, {'TELEGRAM_TOKEN': 'simulado', 'TELEGRAM_CANAL': 'simulado'}, clear=True), \
                patch.object(telegram, 'comprobar'), patch.object(telegram.time, 'sleep'), \
                patch.object(telegram, 'api', return_value={'result': {'message_id': 123}}) as enviar, \
                contextlib.redirect_stdout(io.StringIO()):
            telegram.main()
        self.assertIn('Texto corregido', enviar.call_args.args[2]['text'])
        self.assertEqual(json.loads((self.pub / 'cola.json').read_text())[0]['texto'], 'Texto original')

    def test_plantilla_publicada_en_redes_no_cambia_si_telegram_fallo(self):
        datos = self.raiz / 'datos'
        datos.mkdir()
        dia = (datetime.now(redes.MADRID) + timedelta(days=2)).strftime('%Y-%m-%d')
        anterior = dict(self.post, id=f'{dia}-combi-segura', fecha=f'{dia}T12:00')
        (datos / 'picks.json').write_text(json.dumps({'dias': {dia: {}}}))
        self.guardar('auto.json', [anterior])
        self.guardar('enviados.json', {anterior['id']: {'error': 'fallo telegram'}})
        self.guardar('enviados_redes.json', {anterior['id']: {'redes': {'threads': 'publicado'}}})
        with patch.multiple(plantillas, DATOS=datos, RAIZ=self.raiz, AUTO=self.pub / 'auto.json'), \
                patch.object(plantillas, 'posts_del_dia', return_value=[dict(anterior, texto='Cuota nueva')]), \
                patch.object(plantillas, 'balance', return_value=None), contextlib.redirect_stdout(io.StringIO()):
            plantillas.main()
        self.assertEqual(json.loads((self.pub / 'auto.json').read_text()), [anterior])


class ResultadosTest(unittest.TestCase):
    def setUp(self):
        self.partido = {'estado': 'FT', 'local': {'id': 1}, 'visitante': {'id': 2}, 'goles': [2, 0],
                        'jugadores': {'1': [{'id': 10, 'nombre': 'Ejemplo Jugador', 'min': 90, 'tiros': 3}]}}
        self.pick = {'tipo': 'jugador', 'mercado': 'Home Player Shots', 'opcion': 'E. Jugador - 2'}

    def test_jugador_antiguo_sin_metadatos_se_puede_corregir(self):
        self.assertIs(picks.evaluar_pick(self.pick, self.partido), True)
        self.partido['jugadores']['1'][0]['tiros'] = 1
        self.assertIs(picks.evaluar_pick(self.pick, self.partido), False)

    def test_identificador_distingue_jugadores(self):
        self.partido["jugadores"]["1"].append({"id": 11, "nombre": "Otro Jugador", "min": 90, "tiros": 0})
        self.assertIs(picks.evaluar_pick(dict(self.pick, jugador_id=10, campo="tiros", n=2), self.partido), True)

    def test_sin_participacion_o_dato_se_queda_pendiente(self):
        for cambios in ({'min': 0}, {'tiros': None}):
            p = copy.deepcopy(self.partido)
            p['jugadores']['1'][0].update(cambios)
            self.assertIsNone(picks.evaluar_pick(self.pick, p))
        self.partido['jugadores'] = {}
        self.assertIsNone(picks.evaluar_pick(self.pick, self.partido))

    def test_registro_devuelve_resultado_y_marcador(self):
        with patch.object(aciertos, 'leer', return_value=self.partido):
            self.assertEqual(aciertos.resultado(dict(self.pick, partido_id=1)), (True, '2-0'))

    def test_mercados_de_equipo_conservan_evaluacion(self):
        self.assertIs(picks.evaluar_pick({'mercado': 'Match Winner', 'opcion': 'Home'}, self.partido), True)

    def test_entiende_texto_generado_de_remates_y_tiros_a_puerta(self):
        for texto, campo in [('E. Jugador hace 2+ remates', 'tiros'), ('E. Jugador 1+ tiro a puerta', 'a_puerta')]:
            spec, _ = publicados.entender(texto)
            self.assertEqual(spec['t'], 'jugador')
            self.assertEqual(spec['jugador'], 'e. jugador')
            self.assertEqual(spec['campo'], campo)


if __name__ == '__main__':
    unittest.main()
