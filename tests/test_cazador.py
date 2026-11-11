"""11/11: el Cazador de cuotazas."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import cazador  # noqa: E402


class TestCazador(unittest.TestCase):
    def test_justas_consenso(self):
        j = cazador.justas_consenso({"Match Winner": {"Home": "2.0", "Draw": "3.5", "Away": "4.0"},
                                     "Total - Home": {"Over 0.5": 1.25, "Under 0.5": 3.75}})
        self.assertAlmostEqual(sum(j[("Match Winner", k)] for k in ("Home", "Draw", "Away")), 1, places=6)
        self.assertAlmostEqual(j[("Double Chance", "Home/Draw")], j[("Match Winner", "Home")] + j[("Match Winner", "Draw")])
        self.assertAlmostEqual(j[("Total - Home", "Over 0.5")], (1 / 1.25) / (1 / 1.25 + 1 / 3.75))

    def test_texto(self):
        t = cazador.texto_post({"local": "City", "visitante": "Bournemouth", "inicio": "2026-11-12T21:00",
                                "texto": "Gana el City", "cuota": 1.6, "justa": 1.4})
        self.assertIn("🚨 CUOTAZA", t)
        self.assertIn("@1,60", t)
        self.assertIn("@1,40", t)
        self.assertNotIn("€", t)


if __name__ == "__main__":
    unittest.main()


class TestTipstersAuto(unittest.TestCase):
    def test_lee_picks_claros(self):
        from datetime import datetime
        import tipsters_auto as T
        from bot import MADRID
        d = datetime(2026, 11, 12, 20, 0, tzinfo=MADRID)
        c = [(1, d, "Real Betis", "Sevilla"), (3, d, "Trival Valderas", "Leganes")]
        r = lambda t: [(x["mercado"], x["opcion"], x["cuota"]) for x in T.analizar_post("X", {"id": "a", "texto": t}, c)]
        self.assertEqual(r("🍀 Betis o empate @1,45"), [("Double Chance", "Home/Draw", 1.45)])
        self.assertEqual(r("🍀 Betis marca 2 o más @1,60"), [("Total - Home", "Over 1.5", 1.6)])
        self.assertEqual(r("🍀 Sevilla marca @1,40"), [("Total - Away", "Over 0.5", 1.4)])
        self.assertEqual(r("🍀 +2.5 Trival Valderas - Lega"), [("Goals Over/Under", "Over 2.5", None)])
        self.assertEqual(r("🍀 Leganés gana y Jaén marca"), [])   # varias cosas juntas: para Claude
        self.assertEqual(r("➡️DEVIN BOOKER 25+PUNTOS\n📊CUOTA 1.71"), [])   # baloncesto
