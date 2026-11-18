"""18/11 (Marcos: «una app y desde la propia app lo pueda gestionar todo»): pestaña 📲 Telegram del panel."""
import sys
import unittest
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import panel_telegram as pt  # noqa: E402

M = ZoneInfo("Europe/Madrid")
AHORA = datetime(2026, 11, 17, 22, 0, tzinfo=M)


def post(pid, fecha, texto="🍀 Gana Corea del Sur @1,40\n\n⚽ Catar – Corea del Sur · hoy 15:00", **kw):
    return dict({"id": pid, "fecha": fecha, "texto": texto}, **kw)


POSTS = [
    post("2026-11-17-pick-claude-1", "2026-11-17T14:47", enviado="2026-11-17T14:47", mensaje_id=522, solo_en=["telegram"]),
    post("2026-11-17-verde-auto-2026-11-17-escalera", "2026-11-17T21:42", "PARA DENTRO ✅\n\n✅ Denmark marca 2 o más\n\n📈 Cuota @1,73",
         enviado="2026-11-17T21:42", mensaje_id=525),
    post("2026-11-17-loca-th-1130-duelo", "2026-11-17T11:30", solo_en=["threads"], enviado=None),
    post("2026-11-17-verde-auto-2026-11-16-pick-tip-3", "2026-11-17T21:55", requiere_ok=True, aviso="Varias patas", solo_en=["telegram"]),
    post("2026-11-16-verde-auto-viejo", "2026-11-16T20:00", requiere_ok=True, aviso="Viejo"),
    post("2026-11-17-verde-auto-2026-11-17-pick-tip-3", "2026-11-17T22:15"),
    post("2026-11-17-pick-tip-2", "2026-11-17T18:00", caducada="cancelado", solo_en=["telegram"]),
    post("2026-11-17-verde-auto-2026-11-17-pick-seguro", "2026-11-17T23:22"),
    post("2026-11-17-pick-th", "2026-11-17T22:30", solo_redes=True),
    post("2026-11-17-balance-auto", "2026-11-17T23:15", enviado="2026-11-17T23:16", mensaje_id=532),
]
CONTROL = {"cancelados": ["2026-11-17-verde-auto-2026-11-17-pick-seguro"], "aprobados": {}}
VIVO = [{"id": "2026-11-17-pick-claude-1", "estado": "verde", "picks": [{"texto": "Gana el South Korea", "partido": "Qatar – South Korea",
         "estado": "verde", "marcador": [0, 1], "estado_partido": "FT", "progreso": {"texto": "Marcador: 0–1"}}]}]


class PanelTelegram(unittest.TestCase):
    def setUp(self):
        self.d = pt.datos(POSTS, CONTROL, VIVO, {}, AHORA)

    def test_solo_lo_salido_hoy_y_hasta_ahora(self):
        ids = [e["id"] for e in self.d["enviados"]]
        self.assertEqual(ids, ["2026-11-17-verde-auto-2026-11-17-escalera", "2026-11-17-pick-claude-1"])   # más nuevo arriba
        self.assertNotIn("2026-11-17-balance-auto", ids)   # sale a las 23:16: aún no

    def test_estado_en_directo_y_nombres_en_espanol(self):
        pick = self.d["enviados"][1]
        self.assertEqual(pick["directo"]["estado"], "verde")
        self.assertIn("Corea del Sur", pick["directo"]["picks"][0]["partido"])
        self.assertTrue(pick["directo"]["picks"][0]["fin"])
        self.assertEqual(self.d["picks"], 1)   # el verde no cuenta como pick
        verde = self.d["enviados"][0]
        self.assertIsNone(verde["directo"])
        self.assertEqual(verde["titulo"], "Dinamarca marca 2 o más")

    def test_por_aprobar_solo_telegram_y_reciente(self):
        self.assertEqual([a["id"] for a in self.d["aprobar"]], ["2026-11-17-verde-auto-2026-11-16-pick-tip-3"])
        self.assertEqual(self.d["aprobar"][0]["por"], "Varias patas")
        d = pt.datos(POSTS, dict(CONTROL, aprobados={"2026-11-17-verde-auto-2026-11-16-pick-tip-3": "2026-11-17T22:01"}), VIVO, {}, AHORA)
        self.assertEqual(d["aprobar"], [])   # ya aprobado: no se pide otra vez

    def test_falta_cuota(self):
        posts = POSTS + [post("2026-11-17-combi-partido-1", "2026-11-17T21:00", requiere_ok=True, pide_cuota=True)]
        a = {x["id"]: x for x in pt.datos(posts, CONTROL, VIVO, {}, AHORA)["aprobar"]}
        self.assertTrue(a["2026-11-17-combi-partido-1"]["falta_cuota"])
        self.assertFalse(a["2026-11-17-verde-auto-2026-11-16-pick-tip-3"]["falta_cuota"])

    def test_proximo_sin_threads_ni_cancelados(self):
        self.assertEqual([p["id"] for p in self.d["proximo"]], ["2026-11-17-verde-auto-2026-11-17-pick-tip-3"])

    def test_no_salen_con_motivo(self):
        n = {x["id"]: x for x in self.d["no_salen"]}
        self.assertEqual(n["2026-11-17-pick-tip-2"]["motivo"], "Cancelado")
        self.assertTrue(n["2026-11-17-verde-auto-2026-11-17-pick-seguro"]["se_puede"])   # aún no era su hora: recuperable
        self.assertFalse(n["2026-11-17-pick-tip-2"]["se_puede"])

    def test_avisos_solo_de_telegram(self):
        vig = {"abiertos": [{"clave": "redes-x-threads", "t": "Threads"}],
               "historial": [{"hora": "2026-11-17T14:53", "t": "🚫 prohibido", "k": "prohibido-2026-11-17-pick-tip-2"},
                             {"hora": "2026-11-17T14:53", "t": "🔁 repetido", "k": "repe-2026-11-17-1|BTTS|Yes"},
                             {"hora": "2026-11-17T09:00", "t": "sin clave"},
                             {"hora": "2026-11-16T10:00", "t": "ayer", "k": "prohibido-2026-11-17-pick-tip-2"}]}
        self.assertEqual([a["t"] for a in pt.datos(POSTS, CONTROL, VIVO, vig, AHORA)["avisos"]], ["🚫 prohibido"])

    def test_vigilante_guarda_la_clave(self):
        src = (Path(__file__).resolve().parent.parent / "vigilante.py").read_text(encoding="utf-8")
        self.assertIn('"t": t, "k": k} for k, t in nuevos', src)

    def test_panel_datos_lo_mete(self):
        src = (Path(__file__).resolve().parent.parent / "panel_datos.py").read_text(encoding="utf-8")
        self.assertIn('datos["telegram"] = panel_telegram.main(', src)


if __name__ == "__main__":
    unittest.main()
