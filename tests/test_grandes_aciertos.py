"""22/11 (Marcos): combi de @10 o más acertada → post en Telegram con sus patas y fijado. Una vez por combi."""
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import grandes_aciertos as G  # noqa: E402

V = lambda t: {"texto": t, "partido": "A – B", "estado": "verde"}
COMBI = {"id": "2026-11-20-loca-th-1300-tapados", "estado": "verde", "cuota": 20.07, "picks": [V("Gana A"), V("Ambos marcan")]}


class GrandesAciertos(unittest.TestCase):
    def test_candidatas(self):
        self.assertEqual([c["id"] for c in G.candidatas([COMBI], {})], [COMBI["id"]])
        self.assertEqual(G.candidatas([COMBI], {COMBI["id"]: {}}), [])                     # una vez
        self.assertEqual(G.candidatas([dict(COMBI, cuota=6.5)], {}), [])                   # menos de @10
        self.assertEqual(G.candidatas([dict(COMBI, estado="rojo")], {}), [])
        self.assertEqual(G.candidatas([dict(COMBI, lista=True)], {}), [])                  # listas sin cuota real
        self.assertEqual(G.candidatas([dict(COMBI, picks=[V("x")])], {}), [])              # un pick suelto no
        self.assertEqual(G.candidatas([dict(COMBI, id="2026-11-20-verde-auto-x")], {}), [])

    def test_texto(self):
        t = G.texto(COMBI)
        self.assertIn("¡COMBI ACERTADA @20,07!", t)
        self.assertIn("en Threads", t)
        self.assertIn("✅ Gana A (A – B)", t)
        self.assertIn("10€ → 200,70€", t)

    def test_publica_y_fija(self):
        tmp = Path(tempfile.mkdtemp())
        llamadas = []
        def api(token, metodo, datos=None, archivo=None, **k):
            llamadas.append(metodo)
            return {"result": {"message_id": 77}}
        app = {"publicados_hoy": [COMBI]}
        with mock.patch.dict("os.environ", {"TELEGRAM_TOKEN": "t", "TELEGRAM_CANAL": "c"}), \
             mock.patch.object(G, "ESTADO", tmp / "g.json"), \
             mock.patch.object(G, "leer", side_effect=lambda r, d=None: app if "datos.json" in str(r) else d), \
             mock.patch("publicar_telegram.api", api), mock.patch("incidencias.publicaciones", return_value=[]):
            self.assertEqual(G.main(), 1)
        self.assertEqual(llamadas, ["sendMessage", "pinChatMessage"])
        self.assertIn('"fijado": true', (tmp / "g.json").read_text())


    def test_en_el_bucle(self):
        wf = (Path(__file__).resolve().parent.parent / ".github/workflows/telegram.yml").read_text(encoding="utf-8")
        self.assertIn("paso grandes_aciertos 60 grandes_aciertos.py", wf)
        self.assertIn("datos/grandes_aciertos.json", wf)


if __name__ == "__main__":
    unittest.main()
