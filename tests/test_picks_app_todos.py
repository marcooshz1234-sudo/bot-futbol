"""23/11 (Marcos: «en picks de la app quiero los de todos estos partidos»): la lista de la app no pasa el filtro
del día (5 grandes / día bueno), que es solo para lo que se publica."""
import sys
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import combis_dia as C  # noqa: E402


class PicksAppTodos(unittest.TestCase):
    def test_filtro_solo_para_publicar(self):
        pa = {"fixture": {"id": 1}, "league": {"id": 283}}
        with mock.patch.object(C, "fuera_por_dia_bueno", return_value=True):
            self.assertEqual(C.pool_partido({"partido": pa}, {}, {}), [])          # para publicar: fuera
            C._PARA_APP = True
            try:
                with mock.patch.object(C, "leer", return_value={}):
                    try:
                        C.pool_partido({"partido": pa}, {}, {})                     # para la app: no corta aquí
                    except Exception:
                        pass
            finally:
                C._PARA_APP = False
        src = Path(C.__file__).read_text(encoding="utf-8")
        self.assertIn("guardar_picks_partidos(dia, pools + extra, hist)", src)


if __name__ == "__main__":
    unittest.main()


class NoSeCaeHoy(unittest.TestCase):
    def test_poda_solo_lo_pasado(self):
        src = Path(C.__file__).read_text(encoding="utf-8")
        self.assertIn("for d in [d for d in todo if d < ayer]", src)
        self.assertNotIn("for d in sorted(todo)[:-4]", src)
