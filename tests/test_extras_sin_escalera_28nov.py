"""28/11: «Le Mans marca» salió como pick suelto de las 12:30 y también en la escalera; al publicar se cayó por repetido
y el sábado se quedó con 7 picks. Los picks extra (pick-seguro-3…10) se generan ya sin lo de la escalera del día."""
import re
import unittest
from pathlib import Path

SRC = (Path(__file__).resolve().parent.parent / "combis_dia.py").read_text(encoding="utf-8")


class ExtrasSinEscalera(unittest.TestCase):
    def test_ya_x_incluye_escalera(self):
        m = re.search(r"ya_x = \[.*?\]( \+ list\(ya1\))?\n", SRC, re.S)
        self.assertIsNotNone(m)
        self.assertTrue(m.group(1), "los extras deben excluir lo de la escalera (ya1)")

    def test_ya1_tiene_la_escalera(self):
        self.assertRegex(SRC, r'ya1 = \{.*esc\.get\("picks", \[\]\)\} if esc\.get\("dia"\) == dia')

    def test_pick_extra_respeta_ya(self):
        import combis_dia as C
        p = {"partido_id": 1552832, "mercado": "Total - Home", "opcion": "Over 0.5", "cuota": 1.5,
             "prob_aprendida": 0.95, "fecha": "2026-11-28T20:45", "tipo": "goles"}
        r = C.pick_extra([[p]], "2026-11-28", (12, 30), [], ya=[("1552832", "Total - Home", "Over 0.5")], relajado=2)
        self.assertIsNone(r)


if __name__ == "__main__":
    unittest.main()
