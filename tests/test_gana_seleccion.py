"""14/11: «Gana el Portugal» / «Gana el Kosovo»: las selecciones que se llaman igual en inglés iban con «el»."""
import unittest

import combis_dia as C


class GanaSeleccion(unittest.TestCase):
    def test_sin_el(self):
        self.assertEqual(C.texto_es("Gana el Portugal", "Portugal", "Denmark"), "Gana Portugal")
        self.assertEqual(C.texto_es("Gana el Kosovo", "Kosovo", "Israel"), "Gana Kosovo")
        self.assertEqual(C.texto_es("Gana el Sweden", "Sweden", "Bosnia & Herzegovina"), "Gana Suecia")

    def test_clubes_igual(self):
        self.assertEqual(C.texto_es("Gana el Sevilla", "Sevilla", "Betis"), "Gana el Sevilla")


if __name__ == "__main__":
    unittest.main()
