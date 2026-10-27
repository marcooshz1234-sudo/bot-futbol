import unittest
from unittest.mock import patch

import modelo_goles as MG


class ModeloGoles(unittest.TestCase):
    def setUp(self):
        for f in (MG._escenarios, MG._cumple, MG._ajuste):
            f.cache_clear()
        self.p = patch.object(MG, "lambdas", lambda pid: (1.85, 0.9))   # Milan–Bologna 28/10
        self.p.start()

    def tearDown(self):
        self.p.stop()
        for f in (MG._escenarios, MG._cumple, MG._ajuste):
            f.cache_clear()

    def pk(self, m, o):
        return {"partido_id": "x", "mercado": m, "opcion": o}

    def test_en_contra_paga_mas(self):
        # gana el Milan + Bologna marca: casi se contradicen → bet365 paga más que multiplicar (10,50 vs ~8,6)
        aj = MG.ajuste([self.pk("Match Winner", "Home"), self.pk("Total - Away", "Over 0.5")])
        self.assertGreater(aj, 1.1)

    def test_juntas_paga_menos(self):
        aj = MG.ajuste([self.pk("Goals Over/Under", "Over 2.5"), self.pk("Both Teams Score", "Yes")])
        self.assertLess(aj, 0.85)

    def test_tarjetas_no_se_modelan(self):
        self.assertFalse(MG.modelable(self.pk("Home Team Total Cards", "Over 1.5")))
        self.assertTrue(MG.modelable(self.pk("To Win Either Half", "Home")))


if __name__ == "__main__":
    unittest.main()
