"""17/11 (Marcos: «ha vuelto a salir sin bandera… siempre tiene que estar la bandera»): el verde de la escalera
Dinamarca–Noruega salió sin banderas. Cada fila de un verde lleva las banderas/escudos de su partido."""
import unittest
from unittest import mock

import fotos


class VerdeConBanderas(unittest.TestCase):
    def test_fila_con_banderas_de_seleccion(self):
        t = {"local": "Denmark", "visitante": "Norway", "id_l": 21, "id_v": 1090}
        with mock.patch.object(fotos, "partido", return_value=t):
            html = fotos.verde_lista([{"texto": "Dinamarca marca 2 o más", "estado": "verde", "partido_id": 1528993,
                                       "partido": "Dinamarca – Noruega"}], "ESCALERA", "1,73", "11:00")
        self.assertEqual(html.count("image/svg+xml"), 2)

    def test_insignias_vacio_sin_partido(self):
        self.assertEqual(fotos.insignias(None), "")


if __name__ == "__main__":
    unittest.main()
