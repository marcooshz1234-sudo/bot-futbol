import unittest
from unittest import mock
import lector_canales as L


class VigilarBorrados(unittest.TestCase):
    """25/11 (Marcos: «que lea el canal, lo que hemos subido, y si se ha borrado algo, lo sepa y no lo cuente»)."""
    def test_apunta_los_que_faltan(self):
        recientes = {598: "2026-11-23-pick-seguro-3", 599: "2026-11-23-noche-levante", 600: "2026-11-23-noche-brentford"}
        b, nuevos = L.apuntar_borrados({598: False, 599: True, 600: True}, recientes, ["viejo"])
        self.assertEqual(nuevos, ["2026-11-23-pick-seguro-3"])
        self.assertEqual(b, ["viejo", "2026-11-23-pick-seguro-3"])

    def test_si_no_ve_ninguno_no_apunta(self):   # problema de acceso, no que lo haya borrado todo
        b, nuevos = L.apuntar_borrados({1: False, 2: False}, {1: "a", 2: "b"}, [])
        self.assertEqual((b, nuevos), ([], []))

    def test_no_repite(self):
        b, nuevos = L.apuntar_borrados({1: False, 2: True}, {1: "a", 2: "b"}, ["a"])
        self.assertEqual((b, nuevos), (["a"], []))

    def test_lo_llama_la_sesion(self):
        self.assertIn("vigilar_borrados(cli)", open(L.__file__, encoding="utf-8").read())


if __name__ == "__main__":
    unittest.main()
