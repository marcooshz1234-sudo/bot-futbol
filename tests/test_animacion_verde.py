import unittest
from unittest import mock

import publicar_telegram as P


class AnimacionVerde(unittest.TestCase):
    """12/11 (Marcos: «la del verde solo para buenas cuotas acertadas»)."""
    def correr(self, p, texto):
        llamadas = []
        with mock.patch.object(P, "api", lambda *a, **k: llamadas.append((a, k)) or {"result": {}}):
            P.animacion_verde("t", "c", p, texto)
        return llamadas

    def test_verde_buena_cuota(self):
        ll = self.correr({"id": "2026-11-12-verde-auto-x", "resultado": "verde"}, "✅💚 ¡VERDE x3,42! COMBI 💚✅")
        self.assertEqual(len(ll), 1)
        self.assertEqual(ll[0][0][1], "sendAnimation")
        self.assertEqual(ll[0][1]["campo"], "animation")

    def test_verde_cuota_baja_no(self):
        self.assertEqual(self.correr({"id": "2026-11-12-verde-auto-y", "resultado": "verde"}, "¡VERDE x1,57!"), [])

    def test_no_verde_no(self):
        self.assertEqual(self.correr({"id": "2026-11-12-combi-tres"}, "Cuota @4,98"), [])


if __name__ == "__main__":
    unittest.main()
