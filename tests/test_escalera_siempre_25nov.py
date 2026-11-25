import unittest
from unittest import mock
import escalera as E


class EscaleraSiempre(unittest.TestCase):
    """25/11 (Marcos: «siempre tiene que haber escalera»): el 25/11 nada pasó el filtro y saltó al 26."""
    def test_ultimo_recurso(self):
        with mock.patch.object(E, "elegir_pool", lambda f: None), mock.patch.object(E, "elegir_", lambda *a, **k: None), \
                mock.patch.object(E, "elegir_pool_relajado", lambda f: (0.4, ["x"], 2.1)) as rel:
            self.assertEqual(E.elegir({"picks": []}, fecha="2026-11-25"), (0.4, ["x"], 2.1))

    def test_relajado_sin_fijisimo_pero_sin_dos_partes(self):
        src = open(E.__file__, encoding="utf-8").read()
        self.assertIn("C.suelto_no(p) or not (relajado or C.fijisimo(p))", src)


if __name__ == "__main__":
    unittest.main()
