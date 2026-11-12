import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from plantillas import choca, compatibles


class TestChoques(unittest.TestCase):
    """12/11 (Marcos): los picks de un mismo partido nunca pueden contradecirse."""
    def test_ganadores_opuestos(self):
        self.assertTrue(choca("1|Match Winner|Home", ["1|Match Winner|Away"]))
        self.assertTrue(choca("1|Match Winner|Home", ["1|Match Winner|Draw"]))

    def test_otro_partido_no_cuenta(self):
        self.assertFalse(choca("1|Match Winner|Home", ["2|Match Winner|Away"]))

    def test_compatibles(self):
        self.assertFalse(choca("1|Match Winner|Home", ["1|Goals Over/Under|Over 1.5"]))
        self.assertFalse(choca("1|Match Winner|Home", ["1|Double Chance|Home/Draw"]))
        self.assertFalse(choca("1|Match Winner|Home", ["1|Both Teams Score|Yes"]))

    def test_doble_oportunidad_contraria(self):
        self.assertTrue(choca("1|Match Winner|Home", ["1|Double Chance|Draw/Away"]))

    def test_goles_imposibles(self):
        self.assertTrue(choca("1|Goals Over/Under|Under 1.5", ["1|Both Teams Score|Yes"]))
        self.assertTrue(compatibles([{"mercado": "Goals Over/Under", "opcion": "Over 1.5"},
                                     {"mercado": "Both Teams Score", "opcion": "No"}]))

    def test_mercados_sin_marcador_no_limitan(self):
        self.assertFalse(choca("1|Match Winner|Home", ["1|Cards Over/Under|Over 3.5"]))


class TestMaxDosConCola(unittest.TestCase):
    """12/11: los posts de la cola a mano aún sin salir también cuentan (Montenegro 2+ salía en 3 posts)."""
    def test_cola_programada_cuenta(self):
        import json, tempfile
        from unittest import mock
        import combis_dia as C
        import bot
        with tempfile.TemporaryDirectory() as d:
            pub = Path(d) / "publicaciones"
            pub.mkdir()
            (pub / "cola.json").write_text(json.dumps([
                {"id": "2026-11-12-pick-th-1", "sel": ["1|Total - Home|Over 1.5"]},
                {"id": "2026-11-12-ganadores-x", "sel": ["1|Match Winner|Home"], "enviado": True},
                {"id": "2026-11-12-cancelado", "sel": ["2|Match Winner|Home"]}]))
            (pub / "auto.json").write_text("[]")
            (pub / "control.json").write_text(json.dumps({"cancelados": ["2026-11-12-cancelado"]}))
            with mock.patch.object(bot, "RAIZ", Path(d)):
                u = C.ya_publicadas("2026-11-12")
        self.assertEqual(u["1|Total - Home|Over 1.5"], 1)
        self.assertIn("1|Match Winner|Home", u)          # cuenta para no chocar…
        self.assertEqual(u["1|Match Winner|Home"], 0)    # …pero no para el máx. 2
        self.assertNotIn("2|Match Winner|Home", u)


if __name__ == "__main__":
    unittest.main()
