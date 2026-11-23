"""21/11 (Marcos): los días de las 5 grandes, en Telegram solo picks de ellas (nada de Eredivisie), y LaLiga primero."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import grandes_ligas as G  # noqa: E402


def fx(fid, liga, fecha):
    return {"fixture": {"id": fid, "date": fecha}, "league": {"id": liga}}


class GrandesLigas(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        (self.tmp / "calendario_140.json").write_text(json.dumps([fx(1, 140, "2026-11-21T15:00:00+00:00"),
                                                                  fx(2, 140, "2026-11-21T20:00:00+00:00")]))
        (self.tmp / "calendario_39.json").write_text(json.dumps([fx(3, 39, "2026-11-25T20:00:00+00:00")]))
        G._CACHE.clear()

    def test_dia_de_grandes(self):
        self.assertTrue(G.dia_de_grandes("2026-11-21", self.tmp))
        self.assertFalse(G.dia_de_grandes("2026-11-25", self.tmp))   # 1 partido solo no basta

    def test_eredivisie_fuera_en_dia_de_grandes(self):
        ere = {"sel": ["999|To Score In Both Halves By Teams|Home"]}   # Feyenoord–Excelsior
        self.assertTrue(G.fuera_de_grandes(ere, "2026-11-21", self.tmp))
        self.assertFalse(G.fuera_de_grandes({"sel": ["1|Match Winner|Home"]}, "2026-11-21", self.tmp))
        self.assertFalse(G.fuera_de_grandes({"sel": []}, "2026-11-21", self.tmp))          # verdes, resúmenes…
        self.assertFalse(G.fuera_de_grandes(ere, "2026-11-25", self.tmp))                 # entre semana sin grandes
        self.assertTrue(G.fuera_de_grandes({"sel": ["1|a|b", "999|a|b"]}, "2026-11-21", self.tmp))   # combi mezclada

    def test_si_no_esta_en_el_calendario_mira_proximos(self):
        (self.tmp / "proximos").mkdir()
        (self.tmp / "proximos" / "1550203.json").write_text(json.dumps({"partido": {"league": {"id": 135}}}))
        self.assertEqual(G.liga_de(1550203, self.tmp), 135)
        self.assertFalse(G.fuera_de_grandes({"sel": ["1550203|a|b"]}, "2026-11-21", self.tmp))

    def test_generadores(self):
        self.assertFalse(G.liga_permitida(88, "2026-11-21", self.tmp))
        self.assertTrue(G.liga_permitida(140, "2026-11-21", self.tmp))
        self.assertTrue(G.liga_permitida(88, "2026-11-25", self.tmp))

    def test_laliga_por_delante(self):
        import combis_dia as C
        orig = G.dia_de_grandes
        G.dia_de_grandes = lambda dia, datos=None: True
        try:
            self.assertGreater(C.espana_extra({"liga_id": 140}, "2026-11-21"), 0)
            self.assertEqual(C.espana_extra({"liga_id": 39}, "2026-11-21"), 0)
        finally:
            G.dia_de_grandes = orig


if __name__ == "__main__":
    unittest.main()
