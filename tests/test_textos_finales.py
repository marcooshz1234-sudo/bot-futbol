import unittest

import publicados


class TextosFinalesTest(unittest.TestCase):
    def setUp(self):
        self.d = {'estado': '1H', 'goles': [1, 0], 'descanso': [0, 0],
                  'local': {'id': 1, 'nombre': 'Barcelona'},
                  'visitante': {'id': 2, 'nombre': 'Real Madrid'},
                  'stats': {'1': {'corners': 6, 'tiros': 16, 'a_puerta': 6, 'amarillas': 1, 'rojas': 0},
                            '2': {'corners': 2, 'tiros': 11, 'a_puerta': 4, 'amarillas': 1, 'rojas': 0}},
                  'corners_partes': {'1': {'statistics_1h': 2}, '2': {'statistics_1h': 1}}}

    def spec(self, linea):
        texto = publicados.lineas(linea)[0]['texto']
        return publicados.entender(texto)[0]

    def test_lineas_reales_con_contexto_y_cuota(self):
        ejemplos = [
            ('✅ Athletic–Getafe: más de 23,5 remates · 1,73', 'tiros_mas'),
            ('✅ Monaco–Lille: menos de 4,5 córners en la 1ª parte · 1,75', 'corners_parte'),
            ('✅ Rennes–Strasbourg: más de 2,5 goles · 1,44', 'goles_mas'),
            ('✅ Freiburg 3+ córners', 'eq_corners'),
            ('✅ Barça menos de 7 córners', 'eq_corners_menos'),
            ('✅ Menos de 32,5 remates totales', 'estadistica_menos'),
            ('✅ Más de 26,5 remates totales', 'tiros_mas'),
            ('✅ Más de 9,5 remates a puerta totales', 'estadistica_mas'),
            ('✅ Menos de 4,5 tarjetas', 'estadistica_menos'),
            ('✅ Matanović 1+ remate a puerta', 'jugador'),
            ('✅ De Lange (Marsella): 2+ paradas, solo si es titular', 'jugador')]
        for linea, tipo in ejemplos:
            with self.subTest(linea=linea):
                self.assertEqual(self.spec(linea)['t'], tipo)

    def test_menos_corners_no_es_verde_antes_del_final_y_falla_en_el_limite(self):
        s = self.spec('✅ Barça menos de 7 córners')
        self.assertEqual(publicados.evaluar(s, self.d), 'va_bien')
        self.d['estado'] = 'FT'
        self.assertEqual(publicados.evaluar(s, self.d), 'verde')
        self.d['stats']['1']['corners'] = 7
        self.assertEqual(publicados.evaluar(s, self.d), 'rojo')
        self.d['stats']['1']['corners'] = None
        self.assertEqual(publicados.evaluar(s, self.d), 'sin_datos')

    def test_portero_marsella_se_asocia_a_su_partido_con_avisos_de_titularidad(self):
        post = {'fecha': '2026-10-25T11:30', 'texto':
                '📊 COMBI DE DATOS\n✅ De Lange (Marsella): 2+ paradas, solo si es titular'}
        partidos = [{'id': 10, 'local': 'Marseille', 'visitante': 'Le Havre', 'fecha': '2026-10-25T17:15'}]
        picks = publicados.picks_de_post(post, partidos)
        self.assertEqual(picks[0]['partido_id'], 10)
        self.assertEqual(picks[0]['spec']['campo'], 'paradas')

    def test_menos_corners_primera_parte_se_resuelve_al_descanso(self):
        s = self.spec('✅ Menos de 4,5 córners en la 1ª parte')
        self.assertEqual(publicados.evaluar(s, self.d), 'va_bien')
        self.d['estado'] = 'HT'
        self.assertEqual(publicados.evaluar(s, self.d), 'verde')
        self.d['estado'] = '1H'
        self.d['corners_partes']['1']['statistics_1h'] = 4
        self.assertEqual(publicados.evaluar(s, self.d), 'rojo')

    def test_apellido_compuesto_del_portero_se_resuelve_y_evitar_ambiguos(self):
        s = self.spec('✅ De Lange (Marsella): 2+ paradas, solo si es titular')
        self.d['jugadores'] = {'1': [{'nombre': 'J. de Lange', 'min': 90, 'paradas': 2}]}
        self.assertEqual(publicados.evaluar(s, self.d), 'verde')
        self.assertEqual(publicados.progreso(s, self.d)['actual'], 2)
        self.d['jugadores']['1'].append({'nombre': 'Otro de Lange', 'min': 90, 'paradas': 3})
        self.assertEqual(publicados.evaluar(s, self.d), 'sin_datos')

    def test_totales_y_progreso_de_menos_no_inventan_datos(self):
        mas = self.spec('✅ Más de 26,5 remates totales')
        menos = self.spec('✅ Menos de 32,5 remates totales')
        tarjetas = self.spec('✅ Menos de 4,5 tarjetas')
        self.assertEqual(publicados.evaluar(mas, self.d), 'verde')
        self.assertEqual(publicados.evaluar(menos, self.d), 'va_bien')
        self.assertEqual(publicados.evaluar(tarjetas, self.d), 'va_bien')
        progreso = publicados.progreso(menos, self.d)
        self.assertEqual(progreso['actual'], 27)
        self.assertTrue(progreso['sin_barra'])
        self.assertIn('menos de 32.5', progreso['texto'])
        self.d['stats']['2']['tiros'] = None
        self.assertEqual(publicados.evaluar(menos, self.d), 'sin_datos')
        self.assertIsNone(publicados.progreso(menos, self.d))


if __name__ == '__main__':
    unittest.main()
