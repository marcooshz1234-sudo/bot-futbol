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
        with mock.patch.object(C, "acierto_tipster", return_value=0.5):
            self.assertIn("nota", C.calidad_no(x, 1.75, [x]) or "")

    def test_dos_canales_lo_mismo_si(self):
        x, y = self.x(analisis={"prob_cuota": 0.50}), self.x(tipster="B")
        with mock.patch.object(C, "acierto_tipster", return_value=0.55):
            self.assertIsNone(C.calidad_no(x, 1.75, [x, y]))

    def test_tipster_bueno_pesa_mas(self):
        # 16/11 10:29 (Marcos): el acierto del tipster pesa más que la cuota
        x = self.x(analisis={"prob_cuota": 0.45})
        with mock.patch.object(C, "acierto_tipster", return_value=0.81):   # INSIDER 11 de 12
            self.assertIsNone(C.calidad_no(x, 2.1, [x]))
        with mock.patch.object(C, "acierto_tipster", return_value=0.45):
            self.assertIsNotNone(C.calidad_no(dict(x, analisis={"prob_cuota": 0.62}), 1.55, [x]))

    def test_tipster_bueno_pasa_del_1_80(self):
        x = self.x(analisis={"prob_cuota": 0.46})
        with mock.patch.object(C, "acierto_tipster", return_value=0.81):   # INSIDER: @2,05 pasa
            self.assertTrue(C.tipster_bueno({"tipster": "INSIDER"}))
            self.assertIsNone(C.calidad_no(x, 2.05, [x]))
        with mock.patch.object(C, "acierto_tipster", return_value=0.62):   # TipsAnalistas: de 1,80 no pasa
            self.assertIn("no está entre los buenos", C.calidad_no(dict(x, analisis={"prob_cuota": 0.52}), 1.85, [x]) or "")

    def test_razones_con_otras_palabras(self):
        # 16/11 10:53 (Marcos): el argumento del analista nunca tal cual; solo el reescrito («argumento_propio»)
        from datetime import datetime
        from bot import MADRID
        ini = datetime(2026, 11, 16, 20, 30, tzinfo=MADRID)
        pk = {"dia": "2026-11-16", "tipster": "A", "local": "Albacete", "visitante": "Celta Vigo II", "texto": "Gana el Albacete",
              "cuota": 1.57, "argumento": ["El Celta Fortuna llega con diez bajas: tres sancionados y tres lesionados."]}
        self.assertNotIn("diez bajas", C.post_suelto(pk, ini, ini.replace(hour=10), 1)["texto"])
        pk2 = dict(pk, argumento=["El filial llega con casi diez ausencias entre sanciones y lesiones."], argumento_propio=True)
        self.assertIn("casi diez ausencias", C.post_suelto(pk2, ini, ini.replace(hour=10), 1)["texto"])

    def test_suelo(self):
        x = self.x(analisis={"prob_cuota": 0.30})
        with mock.patch.object(C, "acierto_tipster", return_value=0.9):
            self.assertIn("arriesgado", C.calidad_no(x, 3.2, [x]) or "")

    def test_bueno_pasa(self):
        x = self.x(analisis={"prob_cuota": 0.62})
        with mock.patch.object(C, "acierto_tipster", return_value=0.7):
            self.assertIsNone(C.calidad_no(x, 1.55, [x]))


if __name__ == "__main__":
    unittest.main()
