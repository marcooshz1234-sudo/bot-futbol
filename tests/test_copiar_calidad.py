"""16/11 (Marcos: «coge para el Telegram las que te gusten… buenos picks y fallar lo menos posible»): de los canales
solo se copia lo que pasa el filtro de calidad."""
import unittest
from unittest import mock

import copiar_tipsters as C


class Calidad(unittest.TestCase):
    def x(self, **k):
        base = {"tipster": "A", "dia": "2026-11-16", "local": "L", "visitante": "V", "mercado": "Match Winner",
                "opcion": "Home", "texto": "Gana L"}
        base.update(k)
        return base

    def test_poco_probable_fuera(self):
        x = self.x(analisis={"prob_cuota": 0.45})
        self.assertIn("poco probable", C.calidad_no(x, 2.1, [x]) or "")

    def test_dos_canales_lo_mismo_si(self):
        x, y = self.x(analisis={"prob_cuota": 0.45}), self.x(tipster="B")
        self.assertIsNone(C.calidad_no(x, 2.1, [x, y]))

    def test_tipster_flojo_fuera(self):
        x = self.x(analisis={"prob_cuota": 0.62})
        with mock.patch.object(C, "acierto_tipster", return_value=0.4):
            self.assertIn("acierta solo", C.calidad_no(x, 1.55, [x]) or "")

    def test_bueno_pasa(self):
        x = self.x(analisis={"prob_cuota": 0.62})
        with mock.patch.object(C, "acierto_tipster", return_value=0.7):
            self.assertIsNone(C.calidad_no(x, 1.55, [x]))


if __name__ == "__main__":
    unittest.main()
