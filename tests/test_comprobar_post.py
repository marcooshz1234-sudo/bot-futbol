import unittest
from collections import Counter
from unittest import mock

import comprobar_post as CP


class ComprobarPost(unittest.TestCase):
    """12/11 (Marcos: «quiero que no vuelvas a cometer estos errores»): todas las reglas en un sitio."""
    def setUp(self):
        for p in (mock.patch("bot.partido_caido", lambda p: None), mock.patch.object(CP, "partido_caido", lambda p: None),
                  mock.patch("revision.lados_sin_estrella", lambda fid: set())):
            p.start()
            self.addCleanup(p.stop)

    def post(self, sels, cuotas, **kw):
        return {"id": "2026-11-12-combi-partido-1-th", "origen": "claude", "sel": sels, "cuotas": cuotas,
                "texto": "📈 Cuota @3,00", "cuota_total": 3.0, **kw}

    def reglas(self, p, otros=None):
        return {r for r, _ in CP.comprobar(p, otros=Counter(otros or {}))}

    def test_mas_de_25_y_tarjetas_totales(self):   # los dos fallos de la combi Italia–Francia
        self.assertIn("mercado", self.reglas(self.post(["1|Goals Over/Under|Over 2.5", "1|Both Teams Score|Yes"], [1.67, 1.57])))
        self.assertIn("mercado", self.reglas(self.post(["1|Cards Over/Under|Over 3.5", "1|Both Teams Score|Yes"], [1.8, 1.57])))

    def test_tres_veces_el_mismo(self):   # «Montenegro marca 2+» en multi, 2º pick y combi de Threads
        r = self.reglas(self.post(["9|Total - Home|Over 1.5", "8|Both Teams Score|Yes"], [1.5, 2.0]),
                        {"9|Total - Home|Over 1.5": 2})
        self.assertIn("repetido", r)

    def test_choca(self):
        r = self.reglas(self.post(["9|Match Winner|Away", "8|Both Teams Score|Yes"], [1.9, 1.6]), {"9|Match Winner|Home": 0})
        self.assertIn("choca", r)

    def test_combi_de_partido_sin_cuota_real(self):
        p = self.post(["1|Both Teams Score|Yes", "1|Home Corners Over/Under|Over 3.5"], [1.57, 1.73], cuota_total=None)
        with mock.patch.object(CP, "leer", lambda *a, **k: {}):
            self.assertIn("crear", self.reglas(p))

    def test_texto(self):
        self.assertIn("texto", self.reglas(self.post(["1|Both Teams Score|Yes", "2|Both Teams Score|Yes"], [1.6, 1.6],
                                                     texto="Combi segura 📈 Cuota @2,56")))

    def test_bien(self):
        p = self.post(["1|Both Teams Score|Yes", "1|Home Team Total Cards|Over 1.5"], [1.57, 1.62])
        self.assertEqual(self.reglas(p), set())

    def test_bloquea_en_publicar(self):
        from pathlib import Path
        raiz = Path(__file__).resolve().parent.parent
        self.assertIn("bloquea(p", (raiz / "publicar_telegram.py").read_text(encoding="utf-8"))
        self.assertIn("bloquea(p", (raiz / "redes.py").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
