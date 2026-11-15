"""15/11 (Marcos: «sí»): las combis con escudos de un partido no esperan a la cuota de Marcos: la pone la calculadora
(«aprox.»). Las 3 del domingo (España–Inglaterra, Francia–Turquía, Croacia–Chequia) no salieron por esperarla."""
import unittest
from unittest import mock

import plantillas as P


class CrearConCalculadora(unittest.TestCase):
    def test_cuota_calculada(self):
        src = open(P.__file__, encoding="utf-8").read()
        self.assertIn('f"📈 Cuota @{num(calc)} aprox."', src)
        self.assertIn("cuota_total=calc, cuota_calculada=True", src)
        with mock.patch("crear_apuesta.cuota", return_value=3.62):
            self.assertEqual(P.cuota_crear({"sel": ["1|a|b", "1|c|d"], "cuotas": [1.4, 1.6]}), 3.62)
        self.assertIsNone(P.cuota_crear({"sel": [], "cuotas": []}))


if __name__ == "__main__":
    unittest.main()
