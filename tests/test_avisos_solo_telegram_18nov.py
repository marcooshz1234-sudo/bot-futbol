"""18/11 (Marcos: «quítame los avisos… solo que me avise de lo que se elige en Telegram»)."""
import unittest

import privado as P


class AvisosSoloTelegram(unittest.TestCase):
    def test_es_tg(self):
        self.assertTrue(P.es_tg({"id": "2026-11-18-pick-seguro"}))
        self.assertTrue(P.es_tg({"id": "2026-11-18-loca-th-1200-x100", "mensaje_id": 5}))
        self.assertFalse(P.es_tg({"id": "2026-11-18-loca-th-1200-x100"}))
        self.assertFalse(P.es_tg({"id": "2026-11-18-pick-x", "solo_en": ["threads"]}))
        self.assertTrue(P.es_tg({"id": "2026-11-18-verde-auto-x", "solo_en": ["telegram"]}))
        self.assertFalse(P.es_tg(None))

    def test_vigilante(self):
        posts = {"2026-11-18-pick-seguro": {"id": "2026-11-18-pick-seguro"},
                 "2026-11-18-loca-th-1200-x100": {"id": "2026-11-18-loca-th-1200-x100"}}
        self.assertTrue(P.aviso_vigilante_tg("foto-2026-11-18-pick-seguro", posts))
        self.assertFalse(P.aviso_vigilante_tg("foto-2026-11-18-loca-th-1200-x100", posts))
        self.assertFalse(P.aviso_vigilante_tg("redes-2026-11-18-pick-seguro-threads", posts))
        self.assertFalse(P.aviso_vigilante_tg("prensa-123-abc", posts))
        self.assertTrue(P.aviso_vigilante_tg("bucle-publicar_telegram-2026111810", posts))
        self.assertFalse(P.aviso_vigilante_tg("bucle-threads_locas-2026111810", posts))
        self.assertTrue(P.aviso_vigilante_tg("escalera-2026-11-18", posts))

    def test_ajuste_por_defecto(self):
        import ajustes
        self.assertTrue(P.solo_telegram({}))
        self.assertIn("avisos_solo_telegram", ajustes.AJUSTES_ROLES)


if __name__ == "__main__":
    unittest.main()
