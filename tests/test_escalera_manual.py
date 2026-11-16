"""16/11: la escalera de Marcos (Islandia + Grecia, «manual») se cambió sola por «Gana Eslovaquia» en la recogida de
las 08:57 y salió así a las 11:00. La elegida a mano no se toca con los datos nuevos (solo si el partido se mueve)."""
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))


class EscaleraManual(unittest.TestCase):
    def _correr(self, manual):
        import escalera
        act = {"dia": "2099-01-01", "escalon": 1, "stake": 20.0, "cuota": 1.85, "hora": None,
               "picks": [{"partido_id": 1, "fecha": "2099-01-01T18:00", "mercado": "Match Winner", "opcion": "Home",
                          "texto": "Gana Islandia", "cuota": 1.85}]}
        if manual:
            act["manual"] = "Marcos"
        otro = ("x", [{"partido_id": 2, "fecha": "2099-01-01T16:00", "mercado": "Match Winner", "opcion": "Away",
                       "texto": "Gana Eslovaquia", "cuota": 1.8}], 1.8)
        picks = {"dias": {"2099-01-01": {"picks": [], "mejores_por_partido": []}}}
        with tempfile.TemporaryDirectory() as d:
            est = Path(d) / "e.json"
            est.write_text(json.dumps({"escalon": 1, "stake": 20.0, "historial": [], "actual": act}))
            leer_real = escalera.leer
            with mock.patch.object(escalera, "ESTADO", est), \
                    mock.patch.object(escalera, "resultado", lambda p: None), \
                    mock.patch.object(escalera, "elegir", lambda *a, **k: otro), \
                    mock.patch.object(escalera, "leer",
                                      lambda r, *a: picks if "picks" in str(r) else ({} if "enviados" in str(r) or "proximos" in str(r) else leer_real(r, *a))), \
                    mock.patch.dict(sys.modules, {"bot": mock.Mock(fechas_calendario=lambda: {}, CUOTA_MAXIMA_PATA=1.80)}):
                escalera.main()
            return json.loads(est.read_text())["actual"]

    def test_manual_no_se_rehace(self):
        a = self._correr(manual=True)
        self.assertEqual([p["texto"] for p in a["picks"]], ["Gana Islandia"])
        self.assertEqual(a["cuota"], 1.85)

    def test_sin_manual_se_sigue_rehaciendo(self):
        a = self._correr(manual=False)
        self.assertEqual([p["texto"] for p in a["picks"]], ["Gana Eslovaquia"])


if __name__ == "__main__":
    unittest.main()
