import unittest
from unittest import mock

import plantillas


def pk(pid, m, o, c=1.4):
    return {"partido_id": pid, "mercado": m, "opcion": o, "cuota": c, "texto": f"{m} {o}", "detalle": "7/9",
            "fecha": "2026-10-26T21:00", "local": "A", "visitante": "B", "frecuencia": 0.8, "tipo": "goles"}


class TopePartido(unittest.TestCase):
    def test_un_partido_en_dos_combis_como_mucho(self):
        d = {"picks": [], "combis": {
            "cuota_3": {"cuota": 1.96, "picks": [pk(1, "Goals Over/Under", "Over 1.5"), pk(2, "Corners", "Over 8.5")]},
            "segura": {"cuota": 1.96, "picks": [pk(1, "Total - Home", "Over 0.5"), pk(3, "Corners", "Over 7.5")]},
            "loca": {"cuota": 1.96, "picks": [pk(1, "Cards", "Over 3.5"), pk(4, "Corners", "Over 6.5")]}}}
        with mock.patch("plantillas.leer", return_value={}), mock.patch("datos_futbol.posts_del_dia", return_value=[]):
            ids = [p["id"] for p in plantillas.posts_del_dia("2026-10-26", d)]
        self.assertIn("2026-10-26-combi-cuota_3", ids)
        self.assertIn("2026-10-26-combi-segura", ids)
        self.assertNotIn("2026-10-26-combi-loca", ids)


if __name__ == "__main__":
    unittest.main()
