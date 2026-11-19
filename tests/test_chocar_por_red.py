"""19/11 (Marcos: «no importa que choquen… las del Threads y las del Telegram. Las que no pueden chocar son las de la
misma red social»)."""
import unittest
from unittest import mock

import combis_dia
import comprobar_post as C

POSTS = [
    {"id": "2026-11-19-loca-th-0600-tapados", "solo_en": ["threads"], "enviado": "x", "sel": ["9|Double Chance|Draw/Away"]},
    {"id": "2026-11-19-pick-otro", "solo_en": ["telegram"], "enviado": "x", "sel": ["8|Match Winner|Home"]},
]


def leer(ruta, defecto=None):
    return POSTS if str(ruta).endswith("cola.json") else defecto


class ChocarPorRed(unittest.TestCase):
    def setUp(self):
        self.p = mock.patch.object(combis_dia, "leer", leer)
        self.p.start()

    def tearDown(self):
        self.p.stop()

    def test_por_red(self):
        self.assertIn("9|Double Chance|Draw/Away", combis_dia.ya_publicadas("2026-11-19", red="threads"))
        self.assertNotIn("9|Double Chance|Draw/Away", combis_dia.ya_publicadas("2026-11-19", red="telegram"))
        self.assertIn("9|Double Chance|Draw/Away", combis_dia.ya_publicadas("2026-11-19"))

    def test_telegram_puede_chocar_con_threads(self):
        tg = {"id": "2026-11-19-pick-claude-1", "solo_en": ["telegram"], "origen": "claude", "sel": ["9|Match Winner|Home"]}
        fallos = [f for f in C.comprobar(tg, "x") if f[0] == "choca"]
        self.assertEqual(fallos, [])

    def test_misma_red_no(self):
        th = {"id": "2026-11-19-loca-th-1200-x50", "solo_en": ["threads"], "sel": ["9|Match Winner|Home"]}
        self.assertTrue([f for f in C.comprobar(th, "x") if f[0] == "choca"])


if __name__ == "__main__":
    unittest.main()
