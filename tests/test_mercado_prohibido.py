import unittest

from bot import mercado_prohibido


class MercadoProhibido(unittest.TestCase):
    """12/11 (Marcos: «no pueden haber estos errores»): metí «más de 2,5 goles» y «más de 3,5 tarjetas» en una combi
    hecha a mano. Ningún post nuestro sale con un mercado prohibido; las copias de canales sí."""
    def post(self, sel, **kw):
        return {"id": "2026-11-12-combi-partido-1-th", "sel": [sel], **kw}

    def test_prohibidos(self):
        for s in ("1|Goals Over/Under|Over 2.5", "1|Cards Over/Under|Over 3.5", "1|Goals Over/Under First Half|Over 0.5",
                  "1|First Half Winner|Home", "1|Total Shots|Over 23.5"):
            self.assertTrue(mercado_prohibido(self.post(s)), s)

    def test_permitidos(self):
        for s in ("1|Both Teams Score|Yes", "1|Home Team Total Cards|Over 1.5", "1|Goals Over/Under|Over 1.5",
                  "1|Home Corners Over/Under|Over 3.5"):
            self.assertIsNone(mercado_prohibido(self.post(s)), s)

    def test_copias_de_canales_si(self):
        self.assertIsNone(mercado_prohibido({"id": "2026-11-12-pick-tip-3", "origen": "tipster",
                                             "sel": ["1|Goals Over/Under|Over 2.5"]}))

    def test_puertas(self):
        from pathlib import Path
        raiz = Path(__file__).resolve().parent.parent
        self.assertIn("mercado_prohibido(p)", (raiz / "publicar_telegram.py").read_text(encoding="utf-8"))
        self.assertIn("mercado_prohibido(p)", (raiz / "redes.py").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
