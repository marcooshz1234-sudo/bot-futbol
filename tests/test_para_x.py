import unittest
from datetime import datetime
from zoneinfo import ZoneInfo

import para_x


class ParaX(unittest.TestCase):
    def test_recorta_a_280(self):
        largo = "✅ COMBI LOCAS | SERIE A\n🇮🇹 PARMA vs UDINESE 🇮🇹\n\n" + "\n".join(f"✅ PATA NÚMERO {i} MUY LARGA [x1.40]" for i in range(5)) \
            + "\n\n🔥 Resultado probable: 1-1 | 2-1 | 1-0\n💥 Cuota total aprox.: 7,00\n🟢 VERDE A VERDE 🟢"
        t = para_x.texto_x(largo)
        self.assertLessEqual(para_x.largo_x(t), 280)
        self.assertIn("Cuota total", t)
        self.assertNotIn("Resultado probable", t)

    def test_solo_lo_publicado_en_threads(self):
        ahora = datetime(2026, 10, 28, 2, 30, tzinfo=ZoneInfo("Europe/Madrid"))
        cola = [{"id": "a", "fecha": "2026-10-28T02:00", "texto": "A", "redes": {"threads": "123"}},
                {"id": "b", "fecha": "2026-10-28T02:10", "texto": "B", "redes": {"threads": None}},
                {"id": "c", "fecha": "2026-10-28T02:20", "texto": "C", "redes": {"threads": "456"}}]
        r = para_x.pendientes(ahora, cola, [], {}, {"textos": {"c": "C editado"}}, {"a"})
        self.assertEqual([(p["id"], t) for p, t in r], [("c", "C editado")])

    def test_boton(self):
        self.assertTrue(para_x.boton("Hola 🍀")["inline_keyboard"][0][0]["url"].startswith("https://x.com/intent/post?text=Hola"))


if __name__ == "__main__":
    unittest.main()
