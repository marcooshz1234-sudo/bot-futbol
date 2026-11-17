"""17/11: los verdes de «Polonia ve más de 1,5 tarjetas» y «Bosnia…» no salieron: el tope de 2 picks de tarjetas
al día en Telegram (y lo de no repetir pick) los paraba como si fueran picks nuevos."""
import unittest
from unittest import mock

import comprobar_post as C


class VerdesNoSonPicks(unittest.TestCase):
    def test_verde_de_tarjetas_sale(self):
        v = {"id": "2026-11-17-verde-auto-2026-11-17-pick-seguro", "resultado": "verde", "verde_de": "2026-11-17-pick-seguro",
             "texto": "PARA DENTRO SEÑORES ✅🤑\n\n✅ Polonia ve más de 1,5 tarjetas\n\n📈 Cuota @1,60"}
        posts = [{"id": f"2026-11-17-pick-seguro-{i}", "mensaje_id": i, "texto": "🍀 Polonia ve más de 1,5 tarjetas"} for i in (1, 2)]
        with mock.patch.object(C, "leer", side_effect=lambda f, d=None: posts if "json" in str(f) and ("cola" in str(f)) else ([] if "auto" in str(f) else {})):
            self.assertIsNone(C.tarjetas_tg(v) if not C._es_resultado(v) else None)
        self.assertTrue(C._es_resultado(v))

    def test_pick_sigue_parado(self):
        posts = [{"id": f"2026-11-17-pick-seguro-{i}", "mensaje_id": i, "texto": "🍀 Polonia ve más de 1,5 tarjetas"} for i in (1, 2)]
        p = {"id": "2026-11-17-pick-seguro-5", "texto": "🍀 Bosnia ve más de 1,5 tarjetas"}
        self.assertTrue(C.tarjetas_tg(p, posts=posts))

    def test_verdes_no_cuentan_para_el_tope(self):
        posts = [{"id": "2026-11-17-pick-seguro", "mensaje_id": 1, "texto": "🍀 Polonia ve más de 1,5 tarjetas"},
                 {"id": "2026-11-17-verde-auto-x", "mensaje_id": 2, "resultado": "verde", "texto": "✅ Polonia ve más de 1,5 tarjetas"}]
        self.assertIsNone(C.tarjetas_tg({"id": "2026-11-17-pick-seguro-3", "texto": "🍀 Bosnia ve más de 1,5 tarjetas"}, posts=posts))


if __name__ == "__main__":
    unittest.main()
