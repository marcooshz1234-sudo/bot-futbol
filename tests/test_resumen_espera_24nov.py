import unittest
from datetime import datetime
from zoneinfo import ZoneInfo
import resumen_dia as R

M = ZoneInfo("Europe/Madrid")


class ResumenEspera(unittest.TestCase):
    """24/11: el resumen del lunes salió «2 de 2» sin el Brentford (aún sin resolver) y otro contó un post borrado."""
    def test_cuenta_sin_resolver(self):
        posts = [{"id": "2026-11-23-noche-levante", "fecha": "2026-11-23T13:15", "picks": [{"partido_id": 1, "estado": "verde"}]},
                 {"id": "2026-11-23-noche-brentford", "fecha": "2026-11-23T15:30", "picks": [{"partido_id": 2, "estado": "pendiente"}]},
                 {"id": "2026-11-23-verde-auto-x", "fecha": "2026-11-23T22:00", "picks": [{"partido_id": 1, "estado": "pendiente"}]}]
        self.assertEqual(R.sin_resolver(posts, "2026-11-23"), 1)
        self.assertEqual(R.sin_resolver(posts, "2026-11-23", solo={"2026-11-23-noche-levante"}), 0)

    def test_dia_del_resumen(self):
        self.assertEqual(R.dia_del_resumen(datetime(2026, 11, 23, 23, 20, tzinfo=M)), "2026-11-23")
        self.assertEqual(R.dia_del_resumen(datetime(2026, 11, 24, 1, 10, tzinfo=M)), "2026-11-23")   # tras medianoche
        self.assertIsNone(R.dia_del_resumen(datetime(2026, 11, 24, 12, 0, tzinfo=M)))

    def test_borrados_fuera(self):
        src = open(R.__file__, encoding="utf-8").read()
        self.assertIn("en_telegram(cola) - borrados", src)


if __name__ == "__main__":
    unittest.main()
