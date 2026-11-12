import unittest

from estilo_threads import estilo


class EstiloThreads(unittest.TestCase):
    """12/11 (Marcos: «más fuegos, más tics verdes y más emojis, como antes, que daban tantas visitas»)."""
    def test_combi(self):
        t = estilo("Vamos con la combi del jueves familia 🔥\n\n🇹🇷 Ambos marcan en Turquía–Bélgica\n"
                   "🇦🇱 Albania gana alguna parte\n\n📈 Cuota @4,98", "2026-11-12-combi-tres")
        self.assertTrue(t.startswith("🔥⚽ VAMOS CON LA COMBI DEL JUEVES FAMILIA 🔥"))
        self.assertIn("✅ 🇹🇷 Ambos marcan en Turquía–Bélgica", t)
        self.assertIn("🎯 CUOTA 4,98 💎 · 10€ → 49,80€", t)

    def test_pick_con_10_euros(self):
        t = estilo("Pick de hoy 👀\n\n⚽ Navalcarnero – Real Betis · 19:00\n\n🍀 Real Betis marca 3 o más @1,62",
                   "2026-11-12-pick-th-2")
        self.assertIn("⭐ NAVALCARNERO vs REAL BETIS ⭐ · 19:00", t)
        self.assertIn("✅ Real Betis marca 3 o más @1,62\n💶 10€ → 16,20€", t)

    def test_cuota_en_cabecera(self):
        t = estilo("🔥⚽ COMBILOCAS — ¡NATIONS · 3 PARTIDOS x2,82! 🍀\n\n🇨🇾 Chipre marca", "2026-11-12-combi-nations-th-1")
        self.assertIn("🎯 CUOTA 2,82 💎 · 10€ → 28,20€", t)

    def test_cierre_siempre_y_variado(self):
        cierres = {estilo("Pick 👀\n\n🍀 A @1,50", f"id-{n}").split("\n")[-1] for n in range(20)}
        self.assertGreater(len(cierres), 2)

    def test_verdes_y_ganadores_no_se_tocan(self):
        for pid in ("2026-11-12-verde-auto-x", "2026-11-12-ganadores-nations", "2026-11-12-marcadores-nations-th"):
            self.assertEqual(estilo("hola\n🍀 A @1,50", pid), "hola\n🍀 A @1,50")

    def test_nunca_seguro(self):
        import estilo_threads as E
        self.assertFalse(any("segur" in c.lower() or "cobra" in c.lower() for c in E.CIERRES))


if __name__ == "__main__":
    unittest.main()
