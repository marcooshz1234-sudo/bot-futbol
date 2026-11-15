"""16/11: «Protestan en Contra de Centros de IA en Escocia (N+)» salió como razón del pick Suiza–Escocia.
Las razones de prensa solo valen si son de fútbol y la crisis solo si es del rival."""
import sys
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import noticias

NOTI = {"1545652": [
    {"titulo": "Protestan en Contra de Centros de IA en Escocia", "fuente": "N+", "equipo": "Scotland", "tipos": ["crisis"]},
    {"titulo": "Huelga de jugadores en la selección de Escocia", "fuente": "AS", "equipo": "Scotland", "tipos": ["crisis"]},
    {"titulo": "Impagos en la federación suiza: la plantilla protesta", "fuente": "Marca", "equipo": "Switzerland", "tipos": ["crisis"]},
]}
PICK = {"partido_id": 1545652, "local": "Switzerland", "visitante": "Scotland", "opcion": "Home"}


class TestRazonesPrensa(unittest.TestCase):
    def test_sin_noticias_que_no_son_de_futbol(self):
        with mock.patch.object(noticias, "leer", return_value=NOTI):
            r = noticias.razones(1545652)
        self.assertFalse(any("Centros de IA" in x for _, x in r))
        self.assertTrue(any("Huelga de jugadores" in x for _, x in r))

    def test_crisis_solo_del_rival(self):
        with mock.patch.object(noticias, "leer", return_value=NOTI):
            r = noticias.razones(1545652, PICK)
        self.assertEqual([x for _, x in r], ["Huelga de jugadores en la selección de Escocia (AS)"])


if __name__ == "__main__":
    unittest.main()
