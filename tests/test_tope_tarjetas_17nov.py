"""17/11 (Marcos): «en Telegram ya hay dos picks de tarjetas hoy, ya no subas ninguno así»."""
import unittest

import comprobar_post as C


def post(i, texto, enviado=True, solo=None):
    return {"id": f"2026-11-17-{i}", "texto": texto, "mensaje_id": 1 if enviado else None, "solo_en": solo}


class TopeTarjetas17Nov(unittest.TestCase):
    hechos = [post("pick-seguro", "Polonia ve más de 1,5 tarjetas"), post("pick-seguro-3", "Bosnia ve más de 1,5 tarjetas")]

    def test_tercero_no_sale(self):
        self.assertTrue(C.tarjetas_tg(post("combi-tres", "Polonia ve más de 1,5 tarjetas", False), posts=self.hechos))

    def test_otro_mercado_si(self):
        self.assertIsNone(C.tarjetas_tg(post("pick-seguro-2", "Gales marca", False), posts=self.hechos))

    def test_threads_no_cuenta(self):
        self.assertIsNone(C.tarjetas_tg(post("loca", "tarjetas", False, ["threads"]), posts=self.hechos))

    def test_con_uno_si(self):
        self.assertIsNone(C.tarjetas_tg(post("combi-tres", "tarjetas", False), posts=self.hechos[:1]))


if __name__ == "__main__":
    unittest.main()


class ListasNoCuentan17Nov(unittest.TestCase):   # 17/11: «ambos marcan» de 2 listas de Threads bloqueaba el pick de Telegram
    def test_listas_no_suman(self):
        src = open(C.RAIZ / "combis_dia.py", encoding="utf-8").read()
        self.assertIn('"-lista-"', src)


class MismoPickTG17Nov(unittest.TestCase):   # 17/11: Dinamarca–Noruega iba a salir dos veces
    def test_repetido(self):
        hecho = post("pick-tip-3", "🍀 Crear apuesta: más de 2.5 goles + ambos marcan @1,57\n\n⚽ Dinamarca – Noruega · hoy 20:45")
        nuevo = post("pick-tip-2", "🍀 Ambos marcan y más de 2,5 goles (Crear apuesta) @1,57\n\n⚽ Dinamarca – Noruega · hoy 20:45", False)
        self.assertTrue(C.mismo_pick_tg(nuevo, posts=[hecho]))

    def test_otro_partido_no(self):
        hecho = post("pick-tip-3", "🍀 Ambos marcan @1,57\n\n⚽ Dinamarca – Noruega · hoy 20:45")
        nuevo = post("pick-claude-2", "🍀 Ambos marcan en Israel – Austria @1,57\n\n⚽ Israel – Austria · hoy 20:45", False)
        self.assertIsNone(C.mismo_pick_tg(nuevo, posts=[hecho]))
