import unittest
from unittest.mock import patch

import redes


class EnlaceTelegram(unittest.TestCase):
    def test_cuando_lleva_enlace(self):
        self.assertTrue(redes.lleva_enlace({"id": "2026-10-28-verde-auto-2026-10-28-combi-tres"}))
        self.assertTrue(redes.lleva_enlace({"id": "2026-10-27-balance-picks", "texto": "x\n✅ 23 acertados · ❌ 9 fallados"}))
        self.assertFalse(redes.lleva_enlace({"id": "2026-10-27-balance-picks", "texto": "✅ 4 acertados · ❌ 9 fallados"}))
        self.assertFalse(redes.lleva_enlace({"id": "2026-10-28-combi-loca-datos", "fecha": "2026-10-28T16:00", "texto": "🤪"}))
        # 29/10 (Marcos): desde entonces también las combis, listas y boletos
        self.assertTrue(redes.lleva_enlace({"id": "2026-10-30-combi-partido-1552801", "fecha": "2026-10-30T00:30", "texto": "✅"}))
        self.assertTrue(redes.lleva_enlace({"id": "2026-10-30-picks-manana", "fecha": "2026-10-29T23:00", "texto": "🔥"}))

    def test_comentario_threads_responde_al_post(self):
        llamadas = []
        def falso(metodo, url, params):
            llamadas.append((url, params))
            return {"id": "c1"}
        with patch.object(redes, "llamar", falso), patch.object(redes.time, "sleep", lambda s: None):
            redes.comentar_threads({"redes": {"threads": "999"}}, "tok")
        self.assertEqual(llamadas[0][1]["reply_to_id"], "999")
        self.assertIn("https://t.me/+NMCCvWtZu842Mjhk", llamadas[0][1]["text"])
        self.assertIn("threads_publish", llamadas[1][0])


if __name__ == "__main__":
    unittest.main()


class Duplicados(unittest.TestCase):
    def test_misma_liga_distinto_partido(self):
        a = "✅ COMBI LOCAS | DFB-POKAL\n🇩🇪 BAYERN MÜNCHEN vs 1. FC MAGDEBURG 🇩🇪\n\n🎯 X"
        b = "✅ COMBI LOCAS | DFB-POKAL\n🇩🇪 BAYER LEVERKUSEN vs 1. FC NÜRNBERG 🇩🇪\n\n🎯 Y"
        self.assertNotEqual(redes._titulo(a), redes._titulo(b))
        self.assertEqual(redes._titulo(a), redes._titulo(a + "\notra cosa"))
