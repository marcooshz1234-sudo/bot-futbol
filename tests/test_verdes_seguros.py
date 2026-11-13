"""12/11 (Marcos: «los acertados que los suba de una ni pregunte, pero tiene que estar seguro; si no, que me lo mande
y lo corrijo contigo»)."""
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import verdes_auto as V


def pick(**k):
    return {"texto": "Gana Bélgica", "cuota": 1.8, "estado": "verde", "definitivo": True, "estado_partido": "FT", **k}


class VerdesSeguros(unittest.TestCase):
    def test_dudas(self):
        self.assertIsNone(V.dudas({"cuota": 1.6, "picks": [pick(), pick()]}))
        self.assertIn("baja", V.dudas({"cuota": 1.11, "picks": [pick()]}))            # Bélgica marca @1,11
        self.assertIn("confirmado", V.dudas({"cuota": 1.6, "picks": [pick(definitivo=False)]}))
        self.assertIn("anulada", V.dudas({"cuota": 1.6, "picks": [pick(), pick(estado="anulada")]}))
        self.assertIn("cuota", V.dudas({"cuota": None, "picks": [pick()]}))
        self.assertIn("boleto", V.dudas({"cuota": 2.0, "picks": [pick()]}, boleto=True))
        # 13/11: combi copiada con 2 patas del mismo partido (cuota multiplicada falsa @2,37)
        mismo = [pick(partido_id=9), pick(partido_id=9)]
        self.assertIn("mismo partido", V.dudas({"id": "x-combi-tip-1", "cuota": 2.37, "picks": mismo}))

    def correr(self, publicados, cola=None):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            (d / "docs").mkdir()
            (d / "publicaciones" / "media").mkdir(parents=True)
            (d / "docs" / "datos.json").write_text(json.dumps({"publicados_hoy": publicados}))
            (d / "publicaciones" / "cola.json").write_text(json.dumps(cola or []))
            with mock.patch.multiple(V, RAIZ=d, COLA=d / "publicaciones" / "cola.json", ESTADO=d / "verdes.json",
                                     ESPERA=d / "espera.json", MEDIA=d / "publicaciones" / "media", DATOS=d), \
                    mock.patch.dict(sys.modules, {"playwright.sync_api": None}):
                V.main()
            todo = json.loads((d / "publicaciones" / "cola.json").read_text())
            self.grupo = next((p for p in todo if "-verde-grupo-" in p["id"]), None)
            return {p["verde_de"]: p for p in todo if p.get("verde_de")}

    def test_seguro_sale_solo_y_dudoso_pide_ok(self):
        cola = [{"id": "2026-11-12-pick-tip-1", "texto": "🍀 Bélgica marca @1,11"},
                {"id": "2026-11-12-escalera", "texto": "🪜 Escalera\n\n🍀 Gana Bélgica @1,80"}]
        out = self.correr([
            {"id": "2026-11-12-escalera", "titulo": "Reto escalera", "estado": "verde", "picks": [pick()]},
            {"id": "2026-11-12-pick-tip-1", "titulo": "Pick", "estado": "verde",
             "picks": [pick(texto="Bélgica marca", cuota=1.11)]},
        ], cola)
        self.assertFalse(out["2026-11-12-escalera"].get("requiere_ok"))
        self.assertTrue(out["2026-11-12-pick-tip-1"]["requiere_ok"])
        self.assertIn("baja", out["2026-11-12-pick-tip-1"]["aviso"])
        self.assertIsNone(self.grupo)   # uno seguro solo: no hay grupo

    def test_varios_verdes_una_sola_foto(self):   # 12/11: «si hay varias apuestas, una foto en conjunto»
        cola = [{"id": "2026-11-12-escalera", "texto": "🍀 Gana Bélgica @1,80"},
                {"id": "2026-11-12-pick-seguro", "texto": "🍀 Gana el Albacete @1,53"}]
        out = self.correr([
            {"id": "2026-11-12-escalera", "titulo": "Reto escalera", "estado": "verde", "picks": [pick()]},
            {"id": "2026-11-12-pick-seguro", "titulo": "Pick", "estado": "verde",
             "picks": [pick(texto="Gana el Albacete", cuota=1.53)]},
        ], cola)
        sueltos = [out["2026-11-12-escalera"], out["2026-11-12-pick-seguro"]]
        self.assertTrue(all(p["solo_en"] == ["threads"] and p.get("agrupado_en") for p in sueltos))
        grupo = self.grupo
        self.assertIn("2 VERDES", grupo["texto"])
        self.assertIn("✅ Pick del día · Gana el Albacete @1,53", grupo["texto"])
        self.assertIn("✅ Reto escalera · Gana Bélgica @1,80", grupo["texto"])
        self.assertNotIn("threads", grupo["solo_en"])
        self.assertTrue(all(p["fecha"] == grupo["fecha"] for p in sueltos))   # el comentario de Threads no se queda fuera

    def test_espera_a_que_se_confirme(self):
        out = self.correr([{"id": "2026-11-12-pick-seguro", "titulo": "Pick", "estado": "verde",
                            "cuota": 1.53, "picks": [pick(definitivo=False)]}])
        self.assertEqual(out, {})   # aún no: espera a que confirmar.py lo dé por bueno


if __name__ == "__main__":
    unittest.main()
