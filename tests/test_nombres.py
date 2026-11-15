import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import nombres


class Espanol(unittest.TestCase):
    """15/11 (Marcos): «El Belarus o el Albania no puede ser… Es todo en español siempre»."""
    def test_pick_del_dia_de_hoy(self):
        t = nombres.espanol("🍀 Belarus marca @1,67\n\n👨‍💻 El Belarus jugó hace 2 días: puede llegar cansado\n"
                            "👨‍💻 El Albania jugó hace 2 días: puede llegar cansado")
        self.assertNotIn("Belarus", t)
        self.assertNotIn("El Albania", t)
        self.assertIn("Bielorrusia marca", t)
        self.assertIn("Albania jugó", t)
        self.assertEqual(nombres.fallos(t), [])

    def test_articulos(self):
        self.assertEqual(nombres.espanol("Gana el Portugal"), "Gana Portugal")
        self.assertEqual(nombres.espanol("el gol del Kosovo"), "el gol de Kosovo")
        self.assertEqual(nombres.espanol("que gane el Latvia"), "que gane Letonia")
        self.assertEqual(nombres.espanol("Combi del Spain – England"), "Combi de España – Inglaterra")

    def test_clubes_igual(self):
        self.assertEqual(nombres.espanol("Gana el Real Madrid"), "Gana el Real Madrid")
        self.assertEqual(nombres.espanol("Gana el Almería"), "Gana el Almería")

    def test_publicar_y_threads_lo_corrigen(self):
        import publicar_telegram, redes
        self.assertEqual(publicar_telegram.preparar_texto("🇨🇾 Cyprus marca"), "🇨🇾 Chipre marca")
        self.assertIn("Letonia marca", redes.texto_final({"texto": "🇱🇻 Latvia marca"}))


if __name__ == "__main__":
    unittest.main()
