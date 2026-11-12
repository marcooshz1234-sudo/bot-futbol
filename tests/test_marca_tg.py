import json
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest import mock

import marca_tg as M
from bot import MADRID

POSTS = [{"id": "2026-11-12-pick-seguro", "fecha": "2026-11-12T10:30", "enviado": "2026-11-12T10:30",
          "sel": ["1|Match Winner|Home"], "texto": "Pick de hoy"},
         {"id": "2026-11-12-escalera", "fecha": "2026-11-12T11:00", "enviado": "2026-11-12T11:00",
          "sel": ["2|Match Winner|Away"], "texto": "🪜 Reto escalera"},
         {"id": "2026-11-12-combi-tres", "fecha": "2026-11-12T13:30", "enviado": "2026-11-12T13:30",
          "sel": ["3|Both Teams Score|Yes"], "texto": "Combi"}]


class MarcaTG(unittest.TestCase):
    """12/11 (Marcos: «activa todo menos el balance de la noche»)."""
    def setUp(self):
        self.enviados = []
        for p in (mock.patch.object(M, "enviar", lambda f, t, animacion=False: self.enviados.append((f.name, t))),
                  mock.patch.object(M, "posts_de", lambda dia: POSTS)):
            p.start()
            self.addCleanup(p.stop)

    def test_buenos_dias_una_vez_y_en_su_hora(self):
        est = {}
        self.assertIsNone(M.buenos_dias(datetime(2026, 11, 12, 8, 0, tzinfo=MADRID), est))
        t = M.buenos_dias(datetime(2026, 11, 12, 9, 35, tzinfo=MADRID), est)
        self.assertIn("⏰ 10:30 · Pick del día", t)
        self.assertIn("⏰ 11:00 · Reto escalera", t)
        self.assertIn("lo que vaya saliendo, lo iremos subiendo también", t)   # Marcos 12/11
        self.assertIsNone(M.buenos_dias(datetime(2026, 11, 12, 9, 50, tzinfo=MADRID), est))
        self.assertTrue(self.enviados[0][0].startswith("buenos-dias-"))

    def test_foto_buenos_dias_cambia(self):
        fotos = set()
        for d in range(10, 14):
            self.enviados.clear()
            M.buenos_dias(datetime(2026, 11, d, 9, 35, tzinfo=MADRID), {})
            fotos.add(self.enviados[0][0])
        self.assertEqual(len(fotos), 3)

    def test_noche_europea_solo_dias_europeos(self):
        pa = lambda liga: {"league": {"id": liga, "name": "UEFA Champions League"},
                           "fixture": {"date": "2026-11-12T20:00:00+00:00"},
                           "teams": {"home": {"name": "Inter"}, "away": {"name": "Barcelona"}}}
        with mock.patch.object(M, "partidos_hoy", lambda d: [pa(5)]):
            self.assertIsNone(M.noche_europea(datetime(2026, 11, 12, 17, 30, tzinfo=MADRID), {}))
        with mock.patch.object(M, "partidos_hoy", lambda d: [pa(2)]):
            self.assertIn("NOCHE EUROPEA", M.noche_europea(datetime(2026, 11, 12, 17, 30, tzinfo=MADRID), {}))

    def test_pleno(self):
        with tempfile.TemporaryDirectory() as d, mock.patch.object(M, "RAIZ", Path(d)):
            (Path(d) / "docs").mkdir()
            datos = {"publicados_hoy": [{"id": p["id"], "estado": "verde"} for p in POSTS]}
            (Path(d) / "docs" / "datos.json").write_text(json.dumps(datos))
            self.assertIn("PLENO", M.pleno(datetime(2026, 11, 12, 23, 0, tzinfo=MADRID), {}))
            datos["publicados_hoy"][0]["estado"] = "rojo"
            (Path(d) / "docs" / "datos.json").write_text(json.dumps(datos))
            self.assertIsNone(M.pleno(datetime(2026, 11, 12, 23, 0, tzinfo=MADRID), {}))

    def test_sin_muneco(self):   # «el muñeco no me gusta, quítalo»
        nombres = {f.name for f in M.MARCA.iterdir()}
        self.assertFalse(any("mascota" in n or "la-loca" in n for n in nombres))

    def test_fotos_de_marca_en_telegram(self):
        import publicar_telegram as P
        self.assertTrue(P.foto_de_marca({"id": "2026-11-12-escalera"}, "x").endswith("escalera.jpg"))
        self.assertTrue(P.foto_de_marca({"id": "2026-11-12-pick-seguro"}, "x").endswith("pick-del-dia.jpg"))
        self.assertIsNone(P.foto_de_marca({"id": "2026-11-12-combi-tres"}, "x"))


if __name__ == "__main__":
    unittest.main()
