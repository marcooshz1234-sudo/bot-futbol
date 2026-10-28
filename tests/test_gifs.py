import unittest
from datetime import datetime
from unittest.mock import patch
from zoneinfo import ZoneInfo

import gifs

M = ZoneInfo("Europe/Madrid")


class Gifs(unittest.TestCase):
    def test_verde_recien_publicado(self):
        ahora = datetime(2026, 10, 28, 21, 10, tzinfo=M)
        cola = [{"id": "2026-10-28-verde-auto-x", "fecha": "2026-10-28T21:05", "mensaje_id": 5, "enviado": "2026-10-28T21:05"}]
        m = gifs.momentos(ahora, cola, [], {}, {}, {})
        self.assertEqual(m[0][1], "verde")
        self.assertEqual(gifs.momentos(ahora, cola, [], {}, {}, {"hechos": [m[0][0]]}), [])

    def test_no_dos_gif_seguidos_y_tope(self):
        ahora = datetime(2026, 10, 28, 21, 10, tzinfo=M)
        est = {"enviados": [{"fecha": "2026-10-28T21:00"}]}
        self.assertFalse(gifs.puede(ahora, est, [{"enviado": "2026-10-28T20:00"}], {}))
        self.assertTrue(gifs.puede(ahora, est, [{"enviado": "2026-10-28T21:05"}], {}))
        est = {"enviados": [{"fecha": f"2026-10-28T1{i}:00"} for i in range(4)]}
        self.assertFalse(gifs.puede(ahora, est, [{"enviado": "2026-10-28T21:05"}], {}))

    def test_tras_cada_tipo_de_post(self):
        ahora = datetime(2026, 10, 28, 16, 5, tzinfo=M)
        cola = [{"id": "2026-10-28-combi-loca", "mensaje_id": 1, "enviado": "2026-10-28T16:00"},
                {"id": "2026-10-28-combi-partido-1", "mensaje_id": 2, "enviado": "2026-10-28T16:01"}]
        self.assertEqual([m[1] for m in gifs.momentos(ahora, cola, [], {}, {}, {})], ["loca"])

    def test_sin_roja(self):
        app = {"publicados_hoy": [{"id": "a", "fecha": "2026-10-28T16:00", "estado": "rojo"}]}
        self.assertEqual(gifs.momentos(datetime(2026, 10, 28, 23, 0, tzinfo=M), [], [], {}, app, {}), [])

    def test_sin_clave_no_hace_nada(self):
        with patch.dict("os.environ", {}, clear=True):
            gifs.main()


if __name__ == "__main__":
    unittest.main()
