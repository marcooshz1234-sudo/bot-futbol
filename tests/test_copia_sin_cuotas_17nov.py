"""17/11: el pick-tip-3 (Dinamarca–Noruega ambos marcan + más de 2,5, «Crear apuesta» copiado) llevaba sel pero
no cuotas por pata: no se seguía en el directo ni salía su verde (Marcos: «creo que hemos acertado otra»)."""
import unittest

import app_datos as A


class CopiaSinCuotas(unittest.TestCase):
    def test_sel_sin_cuotas_se_sigue(self):
        p = A.con_cuotas({"id": "x", "sel": ["1528993|Both Teams Score|Yes", "1528993|Goals Over/Under|Over 2.5"], "cuotas": []})
        self.assertEqual(p["cuotas"], [None, None])

    def test_con_cuotas_igual(self):
        p = {"id": "x", "sel": ["1|a|b"], "cuotas": [1.5]}
        self.assertIs(A.con_cuotas(p), p)

    def test_sin_sel_igual(self):
        p = {"id": "x", "sel": []}
        self.assertIs(A.con_cuotas(p), p)


if __name__ == "__main__":
    unittest.main()
