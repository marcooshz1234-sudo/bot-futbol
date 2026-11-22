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
            self.assertEqual(len(ids), len(set(ids)))
        self.assertFalse({x["sel"] for x in a["patas"]} & {x["sel"] for x in b["patas"]})   # dos diferentes
        resto = [x["sel"] for k, c in out.items() if not k.startswith(("todo-", "dia-")) for x in c["patas"]]
        self.assertFalse(set(resto) & {x["sel"] for x in a["patas"] + b["patas"]})   # sin repetir en las demás


if __name__ == "__main__":
    unittest.main()
