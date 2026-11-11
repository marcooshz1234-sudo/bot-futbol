import unittest

from oficina_datos import pendientes_ok


class TestPendientesOficina(unittest.TestCase):
    def test_cuotaza_caducada_no_sale_como_pendiente(self):
        # 11/11: 3 cuotazas de las 09:05 caducadas seguían en la Oficina como «esperando tu OK»
        control = {"por_aprobar": {"a": "c1", "b": "c2", "c": "v1", "d": "v2", "e": "v3"},
                   "aprobados": {"v2": "x"}, "cancelados": ["v3"]}
        todos = {"c1": {"caducada": True}, "c2": {"mensaje_id": 5}, "v1": {}, "v2": {}, "v3": {}}
        self.assertEqual(pendientes_ok(control, todos), ["v1"])


if __name__ == "__main__":
    unittest.main()
