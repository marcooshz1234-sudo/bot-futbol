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
