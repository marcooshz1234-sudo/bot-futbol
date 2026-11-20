import unittest
from unittest import mock
import threads_locas as T


class EscudosEnGanadores(unittest.TestCase):
    """20/11 (Marcos: «en Threads más fotos con escudos, sobre todo donde haya varios quién gana»)."""
    def setUp(self):
        self.teams = {"home": {"id": 1, "name": "Athletic Club", "logo": "a.png"}, "away": {"id": 2, "name": "Espanyol", "logo": "e.png"}}

    def _con(self, sel):
        p = {"id": "x-loca-th-1930-ganaambos", "texto": "👑⚽ GANA Y AMBOS MARCAN 👑⚽\n\n…", "sel": sel, "sin_foto": True}
        with mock.patch.object(T, "leer", lambda f, d=None: {"partido": {"teams": self.teams}}):
            return T.con_escudos(p)

    def test_todos_de_equipo_llevan_foto(self):
        q = self._con(["1|Match Winner|Home", "2|Results/Both Teams Score|Away/Yes", "3|Total - Home|Over 1.5"])
        self.assertNotIn("sin_foto", q)
        self.assertEqual([f["pick"] for f in q["ganadores_img"]["filas"]], ["WIN", "WIN + BTTS", "MARCA 2+"])
        self.assertEqual(q["ganadores_img"]["filas"][1]["escudo_url"], "e.png")
        self.assertEqual(q["ganadores_img"]["titulo"], "GANA Y AMBOS MARCAN")

    def test_mezcla_con_jugador_sigue_en_texto(self):
        q = self._con(["1|Match Winner|Home", "2|Match Winner|Away", "3|Player Fouls Committed|Pepe - 1"])
        self.assertTrue(q.get("sin_foto") and "ganadores_img" not in q)


if __name__ == "__main__":
    unittest.main()
