"""22/11 (Marcos: «una del día mezclando todos los partidos que pueda, o que haga dos diferentes»)."""
import sys
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import combis_semana as C  # noqa: E402


def partido(i, hora):
    return {"id": i, "fecha": f"2026-11-22T{hora}:00+01:00", "local": f"L{i}", "visitante": f"V{i}", "competicion": "LaLiga"}


def pata(i, n):
    return {"sel": f"{i}|Match Winner|Home{n}", "texto": f"pata {i}.{n}", "cuota": 1.5 if n < 2 else 1.9,
            "nota": 1 - n / 10, "p": 0.8 - n / 10}


class TodoElDia(unittest.TestCase):
    def test_todo_y_dos_mitades(self):
        ps = [partido(i, f"{10 + i}:00") for i in range(1, 13)]
        with mock.patch.object(C, "_teams", return_value={}), \
             mock.patch.object(C, "patas_jugador", side_effect=lambda p, h: [pata(p["id"], 0), pata(p["id"], 1), pata(p["id"], 2)]), \
             mock.patch.object(C, "patas_equipo", return_value=[]), mock.patch.object(C, "patas_ganador", return_value=[]):
            out = {c["clave"]: c for c in C.generar_destacadas("2026-11-22", "2026-11-22", partidos=ps, h={})}
        todo, a, b = out["todo-2026-11-22"], out["dia-2026-11-22-a"], out["dia-2026-11-22-b"]
        self.assertEqual(len(todo["patas"]), 12)                                 # todos los partidos del día
        for c in (a, b):   # «cuotas de 30-40 con patas de 1,4-1,6»
            self.assertTrue(30 <= c["cuota"] <= 40, c["cuota"])
            self.assertTrue(all(1.4 <= x["cuota"] <= 1.6 for x in c["patas"]))
            ids = [x["partido"] for x in c["patas"]]
            self.assertTrue(all(ids.count(i) <= 2 for i in ids))
        self.assertFalse({x["sel"] for x in a["patas"]} & {x["sel"] for x in b["patas"]})   # dos diferentes
        resto = [x["sel"] for k, c in out.items() if not k.startswith(("todo-", "dia-")) for x in c["patas"]]
        self.assertFalse(set(resto) & {x["sel"] for x in a["patas"] + b["patas"]})   # sin repetir en las demás


    def test_pocos_partidos_dos_patas_por_partido(self):
        """Quedan 5 partidos: con una pata por partido no llega a @30, así que mete una 2.ª de otro mercado."""
        pool = []
        for i in range(5):
            cs = [{"sel": f"{i}|M{n}|x", "texto": "t", "cuota": 1.5, "p": 0.8 - n / 10, "partido": f"P{i}", "hora": "2026-11-22T15:00"}
                  for n in range(3)]
            pool.append(({"id": i}, cs))
        c = C.combi_30_40(pool, set())
        self.assertTrue(30 <= c["cuota"] <= 40)
        for i in range(5):
            mers = [x["sel"].split("|")[1] for x in c["patas"] if x["partido"] == f"P{i}"]
            self.assertLessEqual(len(mers), 2); self.assertEqual(len(mers), len(set(mers)))
        a = {"sel": "1|Player Fouls Committed|Pepe - 1", "texto": "Pepe: comete 1+ falta", "lado": "L"}
        self.assertFalse(C.misma_cosa(a, dict(a, sel="1|Player Fouls Committed|Juan - 1", texto="Juan: comete 1+ falta")))
        self.assertTrue(C.misma_cosa(a, dict(a, sel="1|Home Player Shots|Pepe - 1", texto="Pepe: 1+ remate")))


    def test_cambia_una_pata_si_se_queda_a_las_puertas(self):
        """7 patas @1,53 + 1 @1,40 = @27,4; meter la 2.ª del partido (@1,58) pasa de 40, cambiarla por ella da @31."""
        pata = lambda i, m, c, p: {"sel": f"{i}|{m}|x", "texto": m, "cuota": c, "p": p, "partido": f"P{i}", "hora": "h"}
        pool = [({"id": i}, [pata(i, "M", 1.53, 0.8)]) for i in range(7)]
        pool.append(({"id": 7}, [pata(7, "M", 1.40, 0.95), pata(7, "N", 1.58, 0.6)]))
        c = C.combi_30_40(pool, set())
        self.assertIsNotNone(c)
        self.assertTrue(30 <= c["cuota"] <= 40, c["cuota"])
        self.assertIn("7|N|x", [x["sel"] for x in c["patas"]])


if __name__ == "__main__":
    unittest.main()
