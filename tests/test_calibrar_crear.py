import math
import unittest

import calibrar_crear as K


class Calibrar(unittest.TestCase):
    def test_aprende_una_pareja_que_paga_menos(self):
        # 6 medidas de la misma pareja: bet365 siempre paga un 20 % menos de lo que calcula el bot
        med = [{"id": str(i), "real": 0.8 * 3.0, "multiplicando": 3.0, "aj": None,
                "parejas": [("resultado+tiros/mismo", 1.0)]} for i in range(6)]
        aj = K.ajustar(med)
        self.assertAlmostEqual(math.exp(aj["claves"]["resultado+tiros/mismo"]), 0.8, delta=0.04)
        antes, ahora = K.error_medio(med, aj)
        self.assertGreater(antes, ahora)

    def test_con_una_sola_medida_es_prudente(self):
        med = [{"id": "x", "real": 2.0, "multiplicando": 3.0, "aj": None, "parejas": [("goles+tiros/partido", 1.0)]}]
        c = K.ajustar(med)["claves"]["goles+tiros/partido"]
        self.assertTrue(math.log(2 / 3) < c < 0)   # corrige, pero no todo de golpe

    def test_lee_la_cuota_del_texto(self):
        self.assertEqual(K.de_texto("💥 Cuota total aprox.: 8,00\\n"), 8.0)
        self.assertEqual(K.de_texto("💥 Cuota total aprox.: 8"), 8.0)


if __name__ == "__main__":
    unittest.main()
