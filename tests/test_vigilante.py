import json
import sys
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import vigilante
from bot import MADRID

AHORA = datetime(2026, 11, 12, 12, 0, tzinfo=MADRID)


def post(i, fecha, **k):
    base = {"id": f"2026-11-12-{i}", "fecha": fecha, "texto": f"Post {i}\n\n⚽ Gana el Betis", "directo": True,
            "sel": [f"{i}|Match Winner|Home"], "cuotas": [1.6]}
    base.update(k)
    return base


class TestVigilante(unittest.TestCase):
    def revisar(self, posts, control=None, caido=None, escalera=True):
        if escalera:   # la escalera de hoy ya está (si no, a las 12:00 siempre avisa)
            posts = posts + [post("escalera", "2026-11-12T11:00", sel=[], cuotas=[], enviado="x",
                                  redes={"threads": "1", "instagram": "2"})]
        with tempfile.TemporaryDirectory() as d:
            pub = Path(d)
            (pub / "media").mkdir()
            (pub / "control.json").write_text(json.dumps(control or {}))
            with mock.patch.object(vigilante, "todos", lambda: posts), mock.patch.object(vigilante, "PUB", pub), \
                    mock.patch("bot.partido_caido", caido or (lambda p: None)), \
                    mock.patch.object(vigilante, "DATOS", pub):
                return [k.split("-")[0] for k, _ in vigilante.revisar(AHORA)]

    def test_todo_bien(self):
        self.assertEqual(self.revisar([post(1, "2026-11-12T20:00"),
                                       post(2, "2026-11-12T10:00", redes={"threads": "1", "instagram": "2"}, enviado="x")]), [])

    def test_publicado_con_partido_aplazado(self):
        p = post(1, "2026-11-12T10:00", enviado="x", redes={"threads": "1", "instagram": "2"})
        self.assertIn("publicado", self.revisar([p], caido=lambda p: "partido 1 aplazado o suspendido (PST)"))
        self.assertNotIn("publicado", self.revisar([p], caido=lambda p: "partido 1 ya terminado"))

    def test_no_salio_en_redes(self):
        self.assertIn("redes", self.revisar([post(1, "2026-11-12T11:00", enviado="x", redes={"threads": "1"})]))
        # sin Instagram a propósito, o pendiente de OK: no es un fallo
        self.assertEqual(self.revisar([post(1, "2026-11-12T11:00", redes={"threads": "1"}, sin_instagram=True, enviado="x")]), [])
        self.assertEqual(self.revisar([post(1, "2026-11-12T11:00", requiere_ok=True)]), [])

    def test_cola_sin_directo(self):
        self.assertIn("directo", self.revisar([post(1, "2026-11-12T20:00", directo=False, _cola=True)]))

    def test_foto_sin_hacer(self):
        self.assertIn("foto", self.revisar([post(1, "2026-11-12T12:10")]))

    def test_falta_tarjeta(self):
        self.assertIn("tarjeta", self.revisar([post(1, "2026-11-12T12:10", tarjeta={"x": 1})]))

    def test_mercado_prohibido(self):
        self.assertIn("prohibido", self.revisar([post(1, "2026-11-12T20:00", sel=["1|Goals Over/Under|Over 2.5"])]))

    def test_texto(self):
        r = self.revisar([post(1, "2026-11-12T20:00", texto="Pick de Tipster Pérez\n⚽ x"),
                          post(2, "2026-11-12T20:00", texto="Gana None @1,50"),
                          post(3, "2026-11-12T20:00", texto="Combi\n\n✅ Gana el Betis\n⚽ Marca el Sevilla")])
        self.assertEqual(sorted(r), ["check", "resto", "tipster"])
        self.assertEqual(self.revisar([post(4, "2026-11-12T20:00", texto="🪜 Escalera\n\n✅ Día 1 superado")]), [])

    def test_sin_cuotas(self):
        self.assertIn("cuotas", self.revisar([post(1, "2026-11-12T20:00", cuotas=[])]))

    def test_repetido(self):
        posts = [post(i, "2026-11-12T20:00", sel=["9|Match Winner|Home"]) for i in range(1, 4)]
        self.assertIn("repe", self.revisar(posts))
        self.assertNotIn("repe", self.revisar(posts[:2] + [dict(posts[2], id="2026-11-12-ganadores-win-1")]))

    def test_escalera(self):
        self.assertIn("escalera", self.revisar([], escalera=False))

    def test_aviso_una_sola_vez(self):
        with tempfile.TemporaryDirectory() as d:
            est = Path(d) / "v.json"
            avisos = []
            with mock.patch.object(vigilante, "ESTADO", est), \
                    mock.patch.object(vigilante, "revisar", lambda a: [("x-1", "fallo")]), \
                    mock.patch("alineaciones_posts.dm", avisos.append):
                vigilante.main(AHORA)
                vigilante.main(AHORA)
            self.assertEqual(len(avisos), 1)
            self.assertEqual(json.loads(est.read_text())["abiertos"][0]["t"], "fallo")

    def test_en_el_bucle(self):
        wf = (Path(__file__).resolve().parent.parent / ".github/workflows/telegram.yml").read_text(encoding="utf-8")
        self.assertIn("paso vigilante", wf)


if __name__ == "__main__":
    unittest.main()
