import unittest
from datetime import datetime
from unittest.mock import patch
from zoneinfo import ZoneInfo

import gifs

M = ZoneInfo("Europe/Madrid")


def post(pid, hora, texto=""):
    return {"id": pid, "fecha": f"2026-10-28T{hora}", "mensaje_id": 1, "enviado": f"2026-10-28T{hora}", "texto": texto}


class Gifs(unittest.TestCase):
    def momentos(self, hora, cola, app=None, est=None):
        h, m = map(int, hora.split(":"))
        return [x[1] for x in gifs.momentos(datetime(2026, 10, 28, h, m, tzinfo=M), cola, [], {}, app or {}, est or {})]

    def test_tras_cada_post(self):
        self.assertEqual(self.momentos("16:05", [post("2026-10-28-combi-loca", "16:00"), post("2026-10-28-combi-partido-1", "16:01")]), ["loca"])
        self.assertEqual(self.momentos("11:05", [post("2026-10-28-escalera", "11:00", "🪜 RETO ESCALERA · DÍA 2/7")]), ["escalera"])
        self.assertEqual(self.momentos("11:05", [post("2026-10-28-escalera", "11:00", "🪜 RETO ESCALERA · DÍA 6/7")]), ["escalera_alta"])
        self.assertEqual(self.momentos("23:35", [post("2026-10-28-balance-auto", "23:30", "✅ 20 acertados · ❌ 9 fallados")]), ["fiesta"])
        self.assertEqual(self.momentos("23:35", [post("2026-10-28-balance-auto", "23:30", "✅ 4 acertados · ❌ 9 fallados")]), [])

    def test_racha(self):
        app = {"publicados_hoy": [{"id": f"c{i}", "fecha": f"2026-10-28T1{i}:00", "estado": "verde"} for i in range(3)]}
        self.assertEqual(self.momentos("21:05", [post("2026-10-28-verde-auto-x", "21:00")], app), ["racha"])
        app["publicados_hoy"][1]["estado"] = "rojo"
        self.assertEqual(self.momentos("21:05", [post("2026-10-28-verde-auto-x", "21:00")], app), ["verde"])

    def test_hito_seguidores(self):
        app = {"redes": {"redes": {"threads": {"seguidores": 2050}}}}
        self.assertEqual(self.momentos("13:00", [], app), ["seguidores"])
        self.assertEqual(self.momentos("13:00", [], app, {"hechos": ["s-2000"]}), [])

    def test_no_dos_gif_seguidos_y_tope(self):
        ahora = datetime(2026, 10, 28, 21, 10, tzinfo=M)
        est = {"enviados": [{"fecha": "2026-10-28T21:00"}]}
        self.assertFalse(gifs.puede(ahora, est, [{"enviado": "2026-10-28T20:00"}], {}))
        self.assertTrue(gifs.puede(ahora, est, [{"enviado": "2026-10-28T21:05"}], {}))
        est = {"enviados": [{"fecha": f"2026-10-28T1{i}:00"} for i in range(4)]}
        self.assertFalse(gifs.puede(ahora, est, [{"enviado": "2026-10-28T21:05"}], {}))

    def test_votos_y_elegir_sin_repetir(self):
        v = {}
        for i in range(3):
            gifs.votar(v, "verde", f"g{i}", True, f"f{i}")
        gifs.votar(v, "verde", "g9", False)
        self.assertEqual(len(v["si"]["verde"]), 3)
        self.assertIn("g9", v["no"])
        gifs.votar(v, "verde", "g0", False)   # cambiar de opinión
        self.assertEqual([x["giphy"] for x in v["si"]["verde"]], ["g1", "g2"])
        est = {"enviados": [{"gif": "g1"}]}
        self.assertEqual(gifs.elegir(v, "verde", est)["giphy"], "g2")
        self.assertIsNone(gifs.elegir(v, "loca", est))

    def test_filtro_como_marcos(self):
        ok = {"type": "gif", "username": "dazn", "user": {"is_verified": True}, "title": "Happy Lets Go GIF by DAZN"}
        self.assertTrue(gifs.valido(ok))
        self.assertFalse(gifs.valido(dict(ok, username="spongebob")))
        self.assertFalse(gifs.valido(dict(ok, title="Brazil Flag GIF by DAZN")))
        self.assertFalse(gifs.valido(dict(ok, title="Womens Football GIF by DAZN")))
        self.assertFalse(gifs.valido(dict(ok, user={"is_verified": False})))

    def test_apagado_no_hace_nada(self):
        with patch.object(gifs, "ACTIVO", False), patch.dict("os.environ", {"TELEGRAM_TOKEN": "x", "TELEGRAM_CANAL": "y"}):
            gifs.main(enviar=lambda *a: self.fail("no debe enviar"))


if __name__ == "__main__":
    unittest.main()
