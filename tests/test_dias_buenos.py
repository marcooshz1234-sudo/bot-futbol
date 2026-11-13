"""12/11 (Marcos: «los días que haya partidos buenos, como hoy la Nations League o como mucho la Champions femenina,
solo céntrate en eso; el del Levante te lo podías haber quitado»)."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import combis_dia as C


def pa(liga, local, visitante, dia="2026-11-12"):
    return {"fixture": {"id": hash((local, visitante)) % 10**6, "date": f"{dia}T20:45:00+01:00",
                        "status": {"short": "NS"}},
            "league": {"id": liga, "name": "x"}, "teams": {"home": {"name": local}, "away": {"name": visitante}}}


class DiasBuenos(unittest.TestCase):
    def correr(self, partidos, prueba):
        with tempfile.TemporaryDirectory() as d:
            for i, p in enumerate(partidos):
                Path(d, f"{i}.json").write_text(json.dumps({"partido": p}))
            with mock.patch.object(C, "EXTRA", Path(d)), mock.patch.object(C, "_DIAS_BUENOS", {}):
                return prueba()

    def test_dia_de_nations_fuera_la_copa(self):
        nations = [pa(5, f"A{i}", f"B{i}") for i in range(4)]
        levante = pa(143, "Tarancón", "Levante")
        madrid = pa(143, "Navalcarnero", "Real Madrid")
        fem_liga = pa(142, "Barcelona W", "Eibar W")
        champions_fem = pa(525, "Barcelona W", "Arsenal W")
        todos = nations + [levante, madrid, fem_liga, champions_fem]
        r = self.correr(todos, lambda: [C.fuera_por_dia_bueno(p) for p in (levante, madrid, fem_liga, champions_fem,
                                                                             nations[0])])
        self.assertEqual(r, [True, False, True, False, False])   # el Madrid de Copa sí; la Champions femenina sí
        with mock.patch.object(C, "_pool_partido", lambda *a: [{"x": 1}]):
            self.assertEqual(self.correr(todos, lambda: C.pool_partido({"partido": levante}, {}, {})), [])

    def test_dia_flojo_todo_vale(self):
        pocos = [pa(5, "A", "B"), pa(5, "C", "D"), pa(141, "Leganés", "Burgos")]
        self.assertFalse(self.correr(pocos, lambda: C.fuera_por_dia_bueno(pocos[2])))


if __name__ == "__main__":
    unittest.main()


class EscaleraDiaBueno(unittest.TestCase):
    def test_escalon_con_partido_menor_se_cambia(self):   # 13/11: la del 13 era de Salamanca–Celta (Copa)
        import escalera as E
        nations = [pa(5, f"A{i}", f"B{i}") for i in range(4)]
        copa = pa(143, "Salamanca UDS", "Celta Vigo")
        with tempfile.TemporaryDirectory() as d:
            prox = Path(d, "proximos")
            prox.mkdir()
            for p in nations + [copa]:
                (prox / f"{p['fixture']['id']}.json").write_text(json.dumps({"partido": p}))
            with mock.patch.object(C, "EXTRA", prox), mock.patch.object(C, "_DIAS_BUENOS", {}), \
                    mock.patch.object(E, "DATOS", Path(d)):
                self.assertTrue(E.partido_menor({"picks": [{"partido_id": copa["fixture"]["id"]}]}))
                self.assertFalse(E.partido_menor({"picks": [{"partido_id": nations[0]["fixture"]["id"]}]}))
