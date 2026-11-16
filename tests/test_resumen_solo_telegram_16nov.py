"""16/11 (Marcos): el resumen de Telegram decía «5 de 33»: contaba también las locas y boletos de Threads."""
import unittest

import resumen_dia as R


def post(pid, estado, picks, titulo="Pick"):
    return {"id": pid, "titulo": titulo, "fecha": "2026-11-16T10:00", "estado": estado,
            "picks": [{"texto": t, "estado": e, "partido_id": i, "estado_partido": "FT"} for i, (t, e) in enumerate(picks, 1)]}


class ResumenSoloTelegram16Nov(unittest.TestCase):
    def test_solo_cuenta_lo_de_telegram(self):
        posts = [post("2026-11-16-pick-tip-1", "verde", [("Gana Eslovenia", "verde")]),
                 post("2026-11-16-loca-th-0400-x100", "rojo", [("A", "rojo"), ("B", "rojo"), ("C", "verde")]),
                 post("2026-11-16-balance-auto", "verde", [("Gana Eslovenia @1,53", "verde")], "📊 RESUMEN DEL LUNES")]
        solo = {"2026-11-16-pick-tip-1", "2026-11-16-balance-auto"}
        picks, _ = R.picks_dia(posts, "2026-11-16", solo)
        self.assertEqual([p["texto"] for p in picks], ["Gana Eslovenia"])
        texto, _ = R.textos_picks(picks, "2026-11-16", posts, [], solo)
        self.assertIn("1 de 1 picks en verde", texto)

    def test_en_telegram_lee_mensajes(self):
        self.assertEqual(R.en_telegram([{"id": "a", "mensaje_id": 5}, {"id": "b"}]) >= {"a"}, True)
        self.assertNotIn("b", R.en_telegram([{"id": "b"}]))


if __name__ == "__main__":
    unittest.main()


class FallosConDato16Nov(unittest.TestCase):   # 16/11 (Marcos): los fallados, con un dato del partido y sin ❌
    def test_fallo_con_marcador(self):
        p = post("2026-11-16-pick-m2", "rojo", [("Grecia marca 2 o más", "rojo")])
        p["picks"][0].update(partido="Grecia – Serbia", marcador=[1, 0])
        v = post("2026-11-16-pick-m1", "verde", [("Gana Eslovenia", "verde")])
        picks, _ = R.picks_dia([v, p], "2026-11-16")
        texto, _ = R.textos_picks(picks, "2026-11-16", [v, p], [])
        self.assertIn("Se nos escaparon", texto)
        self.assertIn("Grecia marca 2 o más · Grecia 1–0 Serbia", texto)
        self.assertNotIn("❌", texto)
