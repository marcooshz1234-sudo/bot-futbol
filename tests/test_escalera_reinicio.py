"""14/11 (Marcos: «cuando suba la escalera, que ponga algo como qué bien íbamos, una pena lo que ha fallado, pero
volvemos con más fuerza»): sin ❌ y variando cada día."""
import unittest

import plantillas as P


class EscaleraReinicio(unittest.TestCase):
    def test_sin_cruz_y_variado(self):
        textos = {P.intro_reinicio({"escalon": 4, "stake": 130.9}, "Ayer", f"2026-11-{d:02d}") for d in range(14, 20)}
        self.assertGreaterEqual(len(textos), 3)
        for t in textos:
            self.assertNotIn("❌", t)
            self.assertIn("20€", t)
            self.assertIn("130,90€", t)
        self.assertIn("Qué bien íbamos", P.intro_reinicio({"escalon": 4, "stake": 130.9}, "Ayer", "2026-11-14"))

    def test_cayo_pronto(self):
        t = P.intro_reinicio({"escalon": 1, "stake": 20}, "Ayer", "2026-11-14")
        self.assertNotIn("❌", t)
        self.assertNotIn("Qué bien íbamos", t)   # el día 1 no «íbamos bien»


if __name__ == "__main__":
    unittest.main()
