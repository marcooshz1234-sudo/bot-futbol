"""19/11 (Marcos: «siempre me pones los mismos emojis»; «quiero más ticks verdes… una vez sí y otra no»)."""
import unittest

import threads_locas as T

COMBI = ("🤑 COMBI x24,20 🤑\n\n🆚 Paris FC (fem.)–Køge (fem.) 18:45\n🎯 Oceane Picard: 2+ tiros · ⚽ Ambos marcan\n"
         "🏆 SL Benfica (fem.) gana una parte\n\n🎯 CUOTA 24,20 aprox. 💎 10€ → 242€\n🙋 ¿QUIÉN SE LA JUEGA? 👇")


class EmojisVariados(unittest.TestCase):
    def test_ticks_un_post_si_otro_no(self):
        con, sin = T.vestir(COMBI, "a", True), T.vestir(COMBI, "a", False)
        self.assertEqual(con.count("✅"), 3)
        self.assertNotIn("✅", sin)
        self.assertNotIn("✅", con.split("\n")[2])          # la línea del partido no
        self.assertIn("🎯 CUOTA", con)                       # la cuota no se toca

    def test_emoji_segun_apuesta(self):
        t = T.vestir(COMBI, "b", False).split("\n")
        self.assertEqual(t[3].split()[0] in T.EMOJIS["tiros"], True)
        self.assertIn(t[4].split()[0], T.EMOJIS["gana"])

    def test_cambia_entre_posts(self):
        vistos = {T.vestir(COMBI, f"s{i}", False).split("\n")[3].split()[0] for i in range(40)}
        self.assertGreater(len(vistos), 2)

    def test_bandera_de_la_liga(self):
        self.assertEqual(T._bandera_pt({"local_en": "Mallorca", "liga": "Copa del Rey"}), "🇪🇸")
        self.assertEqual(T._bandera_pt({"local_en": "Paris FC W", "liga": "UEFA Champions League Women"}), "🆚")

    def test_cabecera_variada(self):
        cab = {T.vestir("🐶 LA DE LOS TAPADOS 🐶\n\nx", f"c{i}", False).split("\n")[0] for i in range(30)}
        self.assertGreater(len(cab), 1)


if __name__ == "__main__":
    unittest.main()
