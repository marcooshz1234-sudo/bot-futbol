"""17/11: el resumen de la noche salió solo y con fallos (6 de 8 en «Para dentro», «sueltos 6 de 6», partido repetido)."""
import unittest

import resumen_dia as R


class ResumenConOk17Nov(unittest.TestCase):
    def test_sale_solo_desde_25nov(self):
        # 25/11 (Marcos: «el resumen de Telegram tampoco se sube solo»): ya no pide OK; a cambio espera a que todos los
        # picks tengan resultado y no cuenta lo borrado (test_resumen_espera_24nov)
        src = open(R.__file__, encoding="utf-8").read()
        self.assertNotIn("'requiere_ok': True", src)
        self.assertIn("sin_resolver(", src)

    def test_mismo_partido_una_vez(self):
        ps = [{"texto": "Ambos marcan en Dinamarca–Noruega"}, {"texto": "Más de 2,5 goles en Dinamarca–Noruega"}]
        self.assertEqual(R._mismo_partido(ps), "Ambos marcan + más de 2,5 goles en Dinamarca–Noruega")

    def test_distinto_partido_none(self):
        self.assertIsNone(R._mismo_partido([{"texto": "Gana Corea"}, {"texto": "Ambos marcan en A–B"}]))

    def test_lista_hasta_12(self):
        self.assertIn("verdes[:12]", open(R.__file__, encoding="utf-8").read())


if __name__ == "__main__":
    unittest.main()
