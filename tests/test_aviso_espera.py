"""13/11: la combi de La Fiebre en espera le llegó a Marcos como «¡VERDE! Revísalo» sin ser un verde."""
import unittest
from pathlib import Path


class AvisoEspera(unittest.TestCase):
    def test_no_verde_no_dice_verde(self):
        src = (Path(__file__).resolve().parent.parent / "asistente.py").read_text(encoding="utf-8")
        self.assertIn("Post en espera", src)
        self.assertIn('p.get("verde_de") or "verde" in p["id"]', src)


if __name__ == "__main__":
    unittest.main()
