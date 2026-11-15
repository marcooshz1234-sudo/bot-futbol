import unittest
from datetime import datetime
import info_top as I
from bot import MADRID

P = {"id": 9, "fecha": "2026-11-15T13:30:00+00:00", "local": "Legnago Salus", "visitante": "Triestina",
     "cuotas_bet365": {"Match Winner": [["Home", "1.66"], ["Draw", "3.5"], ["Away", "5"]],
                       "Double Chance": [["Home/Draw", "1.15"], ["Draw/Away", "2.1"]]}}
AHORA = datetime(2026, 11, 15, 11, 0, tzinfo=MADRID)


class InfoTop(unittest.TestCase):
    def test_dos_medios_y_a_favor_del_rival(self):
        n = {"9": [{"titulo": "Virus en la Triestina: ocho jugadores afectados", "fuente": "A", "fecha": "2026-11-15T09:00"},
                   {"titulo": "La Triestina, golpeada por un brote de gastroenteritis", "fuente": "B", "fecha": "2026-11-15T10:00"}]}
        c = I.candidatos(n, [P], AHORA)
        self.assertEqual([(x["lado"], x["familia"]) for x in c], [("visitante", "virus")])
        self.assertEqual(I.pick_a_favor(P, "visitante")[:2], ("Gana Legnago Salus", 1.66))

    def test_un_solo_medio_no_vale(self):
        n = {"9": [{"titulo": "Virus en la Triestina", "fuente": "A", "fecha": "2026-11-15T09:00"},
                   {"titulo": "Brote de virus en la Triestina", "fuente": "A", "fecha": "2026-11-15T10:00"}]}
        self.assertEqual(I.candidatos(n, [P], AHORA), [])

    def test_titular_sin_el_equipo_no_vale(self):
        n = {"9": [{"titulo": "Brote de virus en un equipo de la Serie D", "fuente": "A", "fecha": "2026-11-15T09:00"},
                   {"titulo": "Virus en el vestuario", "fuente": "B", "fecha": "2026-11-15T10:00"}]}
        self.assertEqual(I.candidatos(n, [P], AHORA), [])
