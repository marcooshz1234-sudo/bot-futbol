import unittest

import alineaciones_posts as A


class QuitarPatas(unittest.TestCase):
    def setUp(self):
        self.p = {"sel": ["1|M|a", "2|M|b", "3|M|c"], "texto": (
            "💥 COMBINADA x3,00 DEL LUNES 💥\n\n✅1. Pepe: 1+ tiros · 1,50\n✅2. Gana el A · 1,25\n✅3. B marca · 1,60\n\n"
            "🎯 Cuota total: 3,00\n💶 10€ → 30,00€\n\n📊 Pepe: 1+ tiros → Pepe 8/8 en sus últimos partidos\n\n👇 ¿Qué pata quitarías tú?")}
        self.cuotas = {"1|M|a": 1.5, "2|M|b": 1.25, "3|M|c": 1.6}

    def test_quita_y_recalcula(self):
        r = A.quitar_patas(self.p, {0}, self.cuotas)
        self.assertIn("✅1. Gana el A · 1,25\n✅2. B marca · 1,60", r["texto"])
        self.assertIn("COMBINADA x2,00", r["texto"])
        self.assertIn("🎯 Cuota total: 2,00", r["texto"])
        self.assertIn("💶 10€ → 20,00€", r["texto"])
        self.assertNotIn("📊 Pepe", r["texto"])
        self.assertEqual(r["sel"], ["2|M|b", "3|M|c"])

    def test_cancela_si_quedan_menos_de_dos(self):
        self.assertEqual(A.quitar_patas(self.p, {0, 1}, self.cuotas), "cancelar")

    def test_mismo_jugador(self):
        self.assertTrue(A.es_el("gustavo varela", "G. Varela"))
        self.assertFalse(A.es_el("gustavo varela", "Dany Mota"))


if __name__ == "__main__":
    unittest.main()
