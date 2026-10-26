import unittest

import datos_futbol as D


def partido(i, fecha, loc, vis, g):
    return {"id": i, "fecha": fecha, "local": {"id": loc}, "visitante": {"id": vis}, "goles": g}


class Rachas(unittest.TestCase):
    def test_racha_de_victorias(self):
        lista = [partido(1, "3", 1, 2, [2, 0]), partido(2, "2", 3, 1, [0, 1]), partido(3, "1", 1, 4, [0, 0])]
        self.assertEqual(D.racha(lista, 1, lambda f, c: f > c), 2)

    def test_posts_sin_apuesta(self):
        for _, _, texto in D.posts_del_dia("2026-10-31"):
            self.assertNotRegex(texto.lower(), r"cuota|apuesta|€|pick")


if __name__ == "__main__":
    unittest.main()
