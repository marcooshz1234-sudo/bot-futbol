import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import revision as R

PARTIDO = {"fixture": {"id": 7, "date": "2026-11-12T19:45:00+00:00", "status": {"short": "NS"}},
           "teams": {"home": {"id": 1, "name": "Italy"}, "away": {"id": 2, "name": "France"}}}


class TestRevision(unittest.TestCase):
    """12/11 (Marcos): bajas de selecciones en prensa, estrellas, cuotas movidas y revisión de la mañana."""

    def datos(self, noticias, cuotas=None):
        d = tempfile.TemporaryDirectory()
        self.addCleanup(d.cleanup)
        p = Path(d.name)
        (p / "proximos").mkdir()
        (p / "proximos" / "7.json").write_text(json.dumps({"partido": PARTIDO, "cuotas": cuotas or {}}))
        (p / "noticias.json").write_text(json.dumps({"7": noticias}))
        (p / "goleadores.json").write_text(json.dumps({"ligas": {"LaLiga": {"goles": [{"jugador": "Kylian Mbappé"}]}}}))
        self.enterContext(mock.patch.object(R, "DATOS", p))

    def test_rival_no_cuenta_como_lado(self):
        self.assertEqual(R.lado_de("Mbappé out against Italy", PARTIDO), "away")   # solo el rival → es del otro
        self.assertEqual(R.lado_de("Mbappé se perderá el duelo ante Italia", PARTIDO), "away")
        self.assertEqual(R.lado_de("Alarmas en Francia: Mbappé no se entrena", PARTIDO), "away")
        self.assertIsNone(R.lado_de("Italia y Francia, sin dudas", PARTIDO))

    def test_favorece(self):
        self.assertTrue(R.favorece("7|Match Winner|Away", "away"))
        self.assertTrue(R.favorece("7|To Win Either Half|Away", "away"))
        self.assertTrue(R.favorece("7|Total - Away|Over 1.5", "away"))
        self.assertTrue(R.favorece("7|Double Chance|Draw/Away", "away"))
        self.assertFalse(R.favorece("7|Total - Home|Over 0.5", "away"))
        self.assertFalse(R.favorece("7|Both Teams Score|Yes", "away"))

    def test_baja_de_estrella_con_su_equipo(self):
        self.datos([{"titulo": "Se encienden todas las alarmas en Francia: Mbappé no se entrena", "fuente": "X"},
                    {"titulo": "Aymeric Laporte, baja de última hora en España", "fuente": "Y"},   # otro partido
                    {"titulo": "Italia vs Francia: previa y alineaciones", "fuente": "Z"}])        # no es baja
        b = R.bajas_partido(7)
        self.assertEqual(len(b), 1)
        self.assertTrue(b[0]["estrella"])
        self.assertEqual(b[0]["lado"], "away")
        self.assertEqual(R.lados_sin_estrella(7), {"away"})

    def test_mismo_jugador_hereda_equipo(self):
        self.datos([{"titulo": "Zidane descarta a Mbappé por precaución", "fuente": "X"},
                    {"titulo": "Alarmas en Francia: Mbappé no se entrena", "fuente": "Y"}])
        self.assertEqual({b["lado"] for b in R.bajas_partido(7)}, {"away"})

    def test_titulares_de_mbappe(self):   # 12/11: estos no los entendía el bot
        import noticias
        for t in ("Zidane descarta a Mbappé para el duelo ante Italia", "Mbappé se perderá el duelo ante Italia",
                  "Zidane Confirma Que Mbappé No Podrá Jugar Contra Italia"):
            self.assertIn("baja", noticias.tipos(t), t)
        self.assertRegex(noticias.norm("Italia vs Francia: Momios y pronóstico"), noticias.RUIDO)

    def test_titular_de_otro_partido(self):   # 12/11: propuso quitar la escalera de Bélgica por Mbappé
        self.datos([{"titulo": "Mbappé, baja para Francia vs Italia: ¿juega ante Turquía?", "fuente": "X"}])
        with mock.patch.object(R, "_TODOS", {"turquia", "belgica", "francia", "italia", "italy", "france"}), \
                mock.patch.object(R, "nombres_equipo", lambda n: {"turquia"} if n == "Italy" else {"belgica"}):
            self.assertEqual(R.bajas_partido(7), [])

    def test_protagonistas(self):
        self.assertIn("tchouameni", R.protagonistas("Aurélien Tchouaméni es baja por lesión"))
        self.assertIn("tchouameni", R.protagonistas("Tchouaméni vuelve a lesionarse y abandona Francia"))

    def test_prensa_inglesa(self):
        self.datos([{"titulo": "Virgil van Dijk Withdraws From France Squad", "fuente": "X"}])
        self.assertEqual(R.bajas_partido(7)[0]["tipo"], "baja")

    def test_vuelve_no_es_baja(self):
        self.datos([{"titulo": "Mbappé vuelve a entrenar con Francia tras su lesión", "fuente": "X"}])
        self.assertEqual(R.bajas_partido(7), [])

    def test_cuota_movida(self):
        self.datos([], cuotas={"Match Winner": [["Away", "2.10"]], "Total - Home": [["Over 0.5", "1.38"]]})
        p = {"sel": ["7|Match Winner|Away", "7|Total - Home|Over 0.5"], "cuotas": [1.70, 1.36]}
        mov = R.cuotas_movidas(p)
        self.assertEqual(len(mov), 1)
        self.assertEqual(mov[0][0], "7|Match Winner|Away")
        self.assertAlmostEqual(mov[0][3], 2.10 / 1.70 - 1)

    def test_vigilante_propone_quitar(self):
        import vigilante
        from datetime import datetime
        from bot import MADRID
        self.datos([{"titulo": "Alarmas en Francia: Mbappé no se entrena", "fuente": "X"}])
        post = {"id": "2026-11-12-combi-partido-7", "fecha": "2026-11-12T19:00", "texto": "Combi Italia–Francia",
                "directo": True, "sel": ["7|To Win Either Half|Away"], "cuotas": [1.5], "requiere_ok": True}
        otro = dict(post, id="2026-11-12-pick", sel=["7|Total - Home|Over 0.5"], requiere_ok=False)
        vigilante.BOTONES.clear()
        with tempfile.TemporaryDirectory() as d, mock.patch.object(vigilante, "todos", lambda: [post, otro]), \
                mock.patch.object(vigilante, "PUB", Path(d)), mock.patch("bot.partido_caido", lambda p: None), \
                mock.patch.object(vigilante, "ESTADO", Path(d) / "v.json"):
            (Path(d) / "control.json").write_text("{}")
            claves = [k for k, _ in vigilante.revisar(datetime(2026, 11, 12, 9, 0, tzinfo=MADRID))]
        self.assertTrue(any(k.startswith("estrella-2026-11-12-combi-partido-7") for k in claves))
        self.assertIn("2026-11-12-combi-partido-7", vigilante.BOTONES.values())
        self.assertNotIn("2026-11-12-pick", vigilante.BOTONES.values())   # el de Italia no va a favor de Francia

    def test_combis_nuevas_sin_picks_a_favor(self):
        src = (Path(R.__file__).parent / "combis_dia.py").read_text(encoding="utf-8")
        self.assertIn("revision.lados_sin_estrella(pa[\"fixture\"][\"id\"])", src)

    def test_informe_manana(self):
        import vigilante
        from datetime import datetime
        from bot import MADRID
        self.datos([])
        with tempfile.TemporaryDirectory() as d, mock.patch.object(vigilante, "todos", lambda: []), \
                mock.patch.object(vigilante, "PUB", Path(d)):
            (Path(d) / "control.json").write_text("{}")
            t = R.informe(datetime(2026, 11, 12, 9, 0, tzinfo=MADRID))
        self.assertIn("Revisión de la mañana", t)
        self.assertIn("Todo en orden", t)

    def test_informe_una_vez_a_las_9(self):
        import vigilante
        from datetime import datetime
        from bot import MADRID
        enviados = []
        with tempfile.TemporaryDirectory() as d, mock.patch.object(vigilante, "ESTADO", Path(d) / "v.json"), \
                mock.patch.object(vigilante, "revisar", lambda a: []), mock.patch.object(vigilante, "PUB", Path(d)), \
                mock.patch.object(vigilante, "dm_botones", lambda t, b: enviados.append(t)), \
                mock.patch.object(R, "informe", lambda a: "☀️ informe"):
            for h, m in ((8, 50), (9, 0), (9, 10), (10, 0)):
                vigilante.main(datetime(2026, 11, 12, h, m, tzinfo=MADRID))
        self.assertEqual(enviados, ["☀️ informe"])


if __name__ == "__main__":
    unittest.main()
