"""16/11: Irlanda salía con ⚽ y sin bandera en GANADORES (la API la llama «Rep. Of Ireland»)."""
import unittest

import combis_personales as C
import semana


class Irlanda16Nov(unittest.TestCase):
    def test_bandera(self):
        self.assertEqual(C.bandera("Rep. Of Ireland"), "🇮🇪")
        self.assertEqual(semana.SELECCIONES["Rep. Of Ireland"], "Ireland")


if __name__ == "__main__":
    unittest.main()
