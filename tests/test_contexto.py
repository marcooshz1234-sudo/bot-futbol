import unittest

import contexto


class Contexto(unittest.TestCase):
    def test_categorias(self):
        # 01/11: con la zona de la tabla (media de las dos posiciones)
        self.assertEqual(contexto.de_pick((1, 19, 20), "local"), "mejor_abismo_medio")
        self.assertEqual(contexto.de_pick((1, 19, 20), "visitante"), "peor_abismo_medio")
        self.assertEqual(contexto.de_pick((5, 6, 20), None), "total_igualado_arriba")
        self.assertEqual(contexto.de_pick((12, 13, 20), None), "total_igualado_medio")
        self.assertEqual(contexto.de_pick((17, 19, 20), "local"), "mejor_igualado_abajo")
        self.assertEqual(contexto.de_pick((4, 12, 20), "visitante"), "peor_lejos_medio")
        self.assertEqual(contexto.sin_zona("peor_lejos_arriba"), "peor_lejos")

    def test_forma_y_bajas(self):
        p = lambda gl, gv: {"local": {"id": 1}, "goles": [gl, gv]}
        bien, mal = [p(2, 0)] * 5, [p(0, 1)] * 5
        self.assertEqual(contexto.de_forma(bien, mal, 1, 1, "local"), "forma_mejor")
        self.assertEqual(contexto.de_forma(bien, mal, 1, 1, "visitante"), "forma_peor")
        self.assertIsNone(contexto.de_forma(bien, mal, 1, 1, None))
        self.assertEqual(contexto.de_bajas(True, False, "local"), "bajas_mias")
        self.assertEqual(contexto.de_bajas(True, False, "visitante"), "bajas_rival")
        self.assertIsNone(contexto.de_pick(None, "local"))

    def test_copas_sin_tabla(self):
        self.assertIsNone(contexto.posiciones(2, "2026-10-26", 1, 2))


if __name__ == "__main__":
    unittest.main()
