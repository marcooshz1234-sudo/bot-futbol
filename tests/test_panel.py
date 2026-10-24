import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from datetime import datetime, timedelta

import app_datos
import directo
import publicados


class EstadoPicksTest(unittest.TestCase):
    def setUp(self):
        self.partido = {'id': 1, 'estado': '2H', 'local': {'id': 1, 'nombre': 'Local'},
                        'visitante': {'id': 2, 'nombre': 'Visitante'}, 'goles': [2, 0], 'descanso': [1, 0], 'stats': {}}

    def test_linea_superada_se_pinta_verde_sin_esperar_al_final(self):
        self.assertEqual(app_datos.estado_seleccion({'mercado': 'Goals Over/Under', 'opcion': 'Over 1.5'}, self.partido), 'verde')

    def test_ganador_provisional_no_es_acierto_definitivo(self):
        p = {'mercado': 'Match Winner', 'opcion': 'Home'}
        self.assertEqual(app_datos.estado_seleccion(p, self.partido), 'va_bien')
        self.partido['estado'] = 'FT'
        self.assertEqual(app_datos.estado_seleccion(p, self.partido), 'verde')

    def test_gol_al_descanso_resuelto_aunque_partido_siga(self):
        self.assertEqual(app_datos.estado_seleccion({'mercado': 'Goals Over/Under First Half', 'opcion': 'Over 0.5'}, self.partido), 'verde')
        self.assertEqual(app_datos.estado_seleccion({'mercado': 'Goals Over/Under First Half', 'opcion': 'Over 1.5'}, self.partido), 'rojo')

    def test_falta_de_estadisticas_no_se_convierte_en_fallo(self):
        self.partido['estado'] = 'FT'
        self.assertEqual(publicados.evaluar({'t': 'corners_mas', 'n': 8.5}, self.partido), 'sin_datos')

    def test_ganar_una_parte_cumplido_no_espera_al_final(self):
        self.assertEqual(app_datos.estado_seleccion({'mercado': 'To Win Either Half', 'opcion': 'Home'}, self.partido), 'verde')

    def test_goles_y_corners_por_partes(self):
        self.assertEqual(publicados.evaluar({'t': 'goles_parte', 'parte': 1, 'n': 0.5}, self.partido), 'verde')
        self.assertEqual(publicados.evaluar({'t': 'goles_parte', 'parte': 2, 'n': 1.5}, self.partido), 'va_mal')
        self.partido['corners_partes'] = {'1': {'statistics_1h': 3}, '2': {'statistics_1h': 2}}
        self.assertEqual(publicados.evaluar({'t': 'corners_parte', 'parte': 1, 'n': 4.5}, self.partido), 'verde')

    def test_final_guardado_tiene_prioridad_sobre_directo_antiguo(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / 'partidos').mkdir()
            (root / 'en_directo').mkdir()
            (root / 'partidos/1.json').write_text(json.dumps(dict(self.partido, estado='FT')))
            (root / 'en_directo/1.json').write_text(json.dumps(self.partido))
            with patch.multiple(app_datos, DATOS=root, PARTIDOS=root / 'partidos'):
                self.assertEqual(app_datos.datos_partido(1)['estado'], 'FT')


class PublicadosTest(unittest.TestCase):
    def test_jugador_sin_participacion_no_queda_pendiente_tras_final(self):
        spec, _ = publicados.entender('Vandevoordt (portero Leipzig): 2+ paradas')
        d = {'estado': 'FT', 'local': {'id': 1, 'nombre': 'RB Leipzig'},
             'visitante': {'id': 2, 'nombre': 'SV Elversberg'}, 'goles': [4, 0],
             'jugadores': {'1': [{'nombre': 'M. Vandevoordt', 'min': 0, 'paradas': 0}]}}
        self.assertEqual(publicados.evaluar(spec, d), 'no_jugo')
        d['estado'] = '2H'
        self.assertEqual(publicados.evaluar(spec, d), 'sin_datos')
        d['estado'] = 'FT'
        d['jugadores']['1'][0]['min'] = None
        self.assertEqual(publicados.evaluar(spec, d), 'sin_datos')

    def test_portero_con_dos_puntos_tras_el_nombre(self):
        spec, _ = publicados.entender('Kristof (portero Elversberg): 2+ paradas')
        d = {'estado': 'FT', 'local': {'id': 1, 'nombre': 'RB Leipzig'},
             'visitante': {'id': 2, 'nombre': 'SV Elversberg'}, 'goles': [4, 0],
             'jugadores': {'2': [{'nombre': 'N. Kristof', 'min': 90, 'paradas': 4}]}}
        self.assertEqual(publicados.evaluar(spec, d), 'verde')

    def test_formatos_reales_de_las_publicaciones(self):
        ejemplos = {'El Lazio gana alguna de las dos partes': 'gana_parte',
                    'Más de 9,5 tiros a puerta en Como–Sassuolo': 'estadistica_mas',
                    'El Elversberg saca 4 o más córners': 'eq_corners',
                    'El Frankfurt ve 2 o más tarjetas': 'eq_tarjetas',
                    'Más de 25,5 tiros en el partido': 'tiros_mas',
                    'Más de 1,5 goles en la 2ª parte': 'goles_parte',
                    'Más de 4,5 córners en la 1ª parte': 'corners_parte',
                    'Barça–Madrid → Ambos marcan y más de 2,5 goles': 'ambos_goles'}
        for texto, tipo in ejemplos.items():
            with self.subTest(texto=texto):
                self.assertEqual(publicados.entender(texto)[0]['t'], tipo)

    def test_tambien_reconoce_selecciones_sin_cuota_individual(self):
        post = {'fecha': '2026-10-24T12:00', 'texto': '🇪🇸 LOCAL 🆚 VISITANTE\n\n✅ Gana el Local\n✅ Más de 1,5 goles\n🎯 Cuota total: 3,00'}
        partidos = [{'id': 1, 'fecha': '2026-10-24T18:00', 'local': 'Local', 'visitante': 'Visitante'}]
        r = publicados.picks_de_post(post, partidos)
        self.assertEqual(len(r), 2)
        self.assertTrue(all(p['partido_id'] == 1 for p in r))
        self.assertIsNone(r[0]['cuota'])

    def test_post_de_ayer_no_se_asocia_al_partido_de_hoy(self):
        partidos = [{'id': 1, 'fecha': '2026-10-24T18:00', 'local': 'Local', 'visitante': 'Visitante'},
                    {'id': 2, 'fecha': '2026-10-25T18:00', 'local': 'Local', 'visitante': 'Visitante'}]
        p = {'fecha': '2026-10-24T12:00', 'texto': 'Combi\n✅ Gana el Local · 1,40'}
        self.assertEqual(publicados.picks_de_post(p, partidos)[0]['partido_id'], 1)
        p['texto'] = 'PICKS PARA MAÑANA\n✅ Gana el Local · 1,40'
        self.assertEqual(publicados.picks_de_post(p, partidos)[0]['partido_id'], 2)


class DirectoTest(unittest.TestCase):
    def test_actualiza_partidos_sin_picks_y_recupera_ayer(self):
        ahora = datetime.now(directo.MADRID)
        partidos = [{'id': 1, 'fecha': (ahora-timedelta(minutes=30)).isoformat(), 'liga_id': 140},
                    {'id': 2, 'fecha': (ahora-timedelta(hours=20)).isoformat(), 'liga_id': 39}]
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            with patch.multiple(directo, DATOS=root, CARPETA=root/'en_directo'), \
                    patch.dict('os.environ', {'API_FOOTBALL_KEY': 'simulada'}), \
                    patch.object(directo, 'partidos_conocidos', return_value=partidos), \
                    patch.object(directo, 'ids_publicados', return_value={}), \
                    patch.object(directo, 'API') as API:
                API.return_value.get.return_value=[]
                directo.main()
                API.return_value.get.assert_called_once_with('fixtures', ids='1-2')


if __name__ == '__main__':
    unittest.main()
