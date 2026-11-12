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

    def test_menos_enlaces_desde_el_2_11(self):
        with patch.object(redes, "verdes_con_enlace", lambda dia, sin=None: 0):
            self.assertTrue(redes.lleva_enlace({"id": "2026-11-03-verde-auto-x", "fecha": "2026-11-03T20:00"}))
        with patch.object(redes, "verdes_con_enlace", lambda dia, sin=None: 2):
            self.assertFalse(redes.lleva_enlace({"id": "2026-11-03-verde-auto-y", "fecha": "2026-11-03T22:00"}))
        self.assertTrue(redes.lleva_enlace({"id": "2026-11-03-combi-loca", "fecha": "2026-11-03T16:00", "texto": "🤪"}))
        self.assertFalse(redes.lleva_enlace({"id": "2026-11-03-combi-partido-1", "fecha": "2026-11-03T20:00", "texto": "✅"}))
        self.assertFalse(redes.lleva_enlace({"id": "2026-11-03-picks-manana", "fecha": "2026-11-03T23:00", "texto": "🔥"}))
        self.assertFalse(redes.lleva_enlace({"id": "2026-11-03-balance-picks", "fecha": "2026-11-03T23:45",
                                             "texto": "✅ 23 acertados · ❌ 9 fallados"}))

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


class EnlaceMas(unittest.TestCase):
    """12/11 (Marcos: «pon más el enlace de Telegram en Threads»)."""
    def test_mas_posts(self):
        for pid in ("pick-seguro", "escalera", "combi-tres", "combi-multi", "combi-partido-1-th", "pick-tip-2", "pick-th-1"):
            self.assertTrue(redes.lleva_enlace({"id": f"2026-11-13-{pid}", "fecha": "2026-11-13T15:00"}), pid)
        for n in range(4):   # todos los verdes, no solo 2 al día
            self.assertTrue(redes.lleva_enlace({"id": f"2026-11-13-verde-auto-{n}", "fecha": "2026-11-13T22:00"}))
        self.assertFalse(redes.lleva_enlace({"id": "2026-11-13-ganadores-nations", "fecha": "2026-11-13T00:00"}))

    def test_frase_variada(self):
        frases = {redes.texto_enlace({"id": f"2026-11-13-pick-tip-{n}"}) for n in range(12)}
        self.assertGreater(len(frases), 1)
        self.assertTrue(all(redes.ENLACE_TELEGRAM in f for f in frases))

