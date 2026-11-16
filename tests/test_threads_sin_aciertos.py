"""16/11 (Marcos): en Threads e Instagram no se sube cuánto hemos acertado (verdes, rojos, balances), salvo un verde
de cuota 10 o más («señores, acertamos tal»)."""
import unittest

import redes as R


class ThreadsSinAciertos(unittest.TestCase):
    def test_verde_normal_no(self):
        self.assertTrue(R.resultado_sin_cuoton({"id": "2026-11-16-verde-auto-a", "resultado": "verde",
                                                "texto": "PARA DENTRO ✅\n📈 Cuota @1,57"}))

    def test_cuoton_si(self):
        self.assertFalse(R.resultado_sin_cuoton({"id": "2026-11-16-verde-auto-a", "resultado": "verde",
                                                 "texto": "PARA DENTRO ✅\n📈 Cuota @14,20"}))

    def test_cuoton_con_x(self):
        self.assertFalse(R.resultado_sin_cuoton({"id": "2026-11-16-verde-auto-a", "texto": "✅💚 ¡VERDE x12,00! 💚✅"}))
        self.assertTrue(R.resultado_sin_cuoton({"id": "2026-11-16-verde-auto-a", "texto": "✅💚 ¡VERDE x3,00! 💚✅"}))

    def test_rojo_y_balance_no(self):
        self.assertTrue(R.resultado_sin_cuoton({"id": "2026-11-16-rojo-auto-a", "texto": "@25"}))
        self.assertTrue(R.resultado_sin_cuoton({"id": "2026-11-16-balance", "texto": "✅ 3 · ❌ 2"}))
        self.assertTrue(R.resultado_sin_cuoton({"id": "2026-11-16-resumen-dia", "texto": ""}))

    def test_resto_igual(self):
        self.assertFalse(R.resultado_sin_cuoton({"id": "2026-11-16-combi-tres", "texto": "@3,19"}))
        self.assertFalse(R.resultado_sin_cuoton({"id": "2026-11-16-escalera", "texto": "@1,85"}))


if __name__ == "__main__":
    unittest.main()
