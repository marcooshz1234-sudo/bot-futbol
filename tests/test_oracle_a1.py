"""13/11 (Marcos: «reintentar el A1 solo»): oracle_a1.py no hace nada sin secretos y reconoce el «sin hueco»."""
import os
import unittest
from unittest import mock

import oracle_a1 as O


class OracleA1(unittest.TestCase):
    def test_sin_secretos_no_hace_nada(self):
        with mock.patch.dict(os.environ, {}, clear=True), mock.patch.object(O, "HECHO", O.CARPETA / "no_existe.json"):
            self.assertIsNone(O.config())
            self.assertEqual(O.main(), 0)

    def test_sin_hueco(self):
        e = type("E", (Exception,), {})("Out of host capacity.")
        e.code, e.message, e.status = "InternalError", "Out of host capacity.", 500
        self.assertTrue(O.es_sin_hueco(e))
        otro = type("E", (Exception,), {})("NotAuthorized")
        otro.code, otro.message, otro.status = "NotAuthorizedOrNotFound", "no", 404
        self.assertFalse(O.es_sin_hueco(otro))


if __name__ == "__main__":
    unittest.main()
