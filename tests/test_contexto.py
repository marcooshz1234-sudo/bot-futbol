import unittest

import contexto


class Contexto(unittest.TestCase):
    def test_categorias(self):
        self.assertEqual(contexto.de_pick((1, 19, 20), "local"), "mejor_abismo")
        self.assertEqual(contexto.de_pick((1, 19, 20), "visitante"), "peor_abismo")
        self.assertEqual(contexto.de_pick((5, 8, 20), None), "total_igualado")
        self.assertEqual(contexto.de_pick((4, 12, 20), "visitante"), "peor_lejos")
        self.assertIsNone(contexto.de_pick(None, "local"))

    def test_copas_sin_tabla(self):
        self.assertIsNone(contexto.posiciones(2, "2026-10-26", 1, 2))


if __name__ == "__main__":
    unittest.main()
