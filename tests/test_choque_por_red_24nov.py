import unittest
from unittest import mock
from collections import Counter
import comprobar_post as CP
import publicar_telegram as PT


class ChoquePorRed(unittest.TestCase):
    """24/11: el Leipzig de las 10:30 (Telegram) se cayó por un «Lens o empate» que solo iba en Threads."""
    def test_solo_choca_en_su_red(self):
        p = {"id": "2026-11-24-pick-extra-leipzig", "fecha": "2026-11-24T10:30", "origen": "claude",
             "sel": ["1635713|Match Winner|Home"], "texto": "🍀 Gana el RB Leipzig @1,38", "cuotas": [1.38]}
        def sin_este(p_, red=None):
            return {} if red == "telegram" else {"1635713|Double Chance|Draw/Away": 1}
        with mock.patch.object(CP, "_sin_este", sin_este):
            self.assertFalse([x for x in CP.comprobar(p, red="telegram") if x[0] == "choca"])
            self.assertTrue([x for x in CP.comprobar(p) if x[0] == "choca"])

    def test_combi_de_tipster_sin_sel(self):
        p = {"id": "2026-11-24-combi-tip-1", "fecha": "2026-11-24T13:42", "origen": "tipster", "sel": [], "cuotas": [],
             "texto": "Combinada para hoy ⚽\n\n🍀 Doble: Como más de 1 gol @1,25\n🍀 Doble: menos de 4,5 goles @1,36"}
        self.assertIn("solo picks sueltos", PT.combi_no_pedida(p))

    def test_trebol_en_la_entrada_no_es_combi(self):   # «Vamos con otro pick 🍀» + «🍀 Dortmund…» es UN pick
        p = {"id": "2026-11-24-pick-claude-4", "fecha": "2026-11-24T17:00", "sel": ["1|Away Player Shots Total|Over 8.5"],
             "cuotas": [1.73], "texto": "Vamos con otro pick 🍀\n\n🍀 Dortmund: más de 8,5 remates @1,73"}
        self.assertIsNone(PT.combi_no_pedida(p))


if __name__ == "__main__":
    unittest.main()
