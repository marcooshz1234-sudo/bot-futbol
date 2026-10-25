import unittest

import picks as P


def pk(i, mercado, opcion, cuota, tipo="goles", liga="LaLiga", campo=None):
    return {"partido_id": i, "mercado": mercado, "opcion": opcion, "cuota": cuota, "tipo": tipo, "campo": campo,
            "competicion": liga, "frecuencia": 0.85, "ventaja": 0.1, "fecha": "2026-10-31T16:00"}


class Estilos(unittest.TestCase):
    def test_lado(self):
        self.assertEqual(P.lado_pick(pk(1, "Total - Away", "Over 0.5", 1.3)), "visitante")
        self.assertEqual(P.lado_pick(pk(1, "Double Chance", "Home/Draw", 1.3)), "local")
        self.assertIsNone(P.lado_pick(pk(1, "Goals Over/Under", "Over 1.5", 1.3)))

    def test_tema_del_dia_y_no_se_guarda(self):
        # sábado (31/10): tema "los de fuera"
        ps = [pk(i, "Double Chance", "Draw/Away", 1.5, tipo="resultado") for i in range(4)]
        res = P.combis_estilo("2026-10-31", ps, [], set())
        self.assertEqual(res["tema"]["tema"], "fuera")
        # lunes sin picks de goles: no hay tema (no se usa otro día)
        res = P.combis_estilo("2026-10-26", ps, [], set())
        self.assertNotIn("tema", res)

    def test_atreve_solo_cuotas_altas(self):
        ps = [pk(0, "Match Winner", "Home", 1.9, tipo="resultado", liga="LaLiga"),
              pk(1, "Match Winner", "Home", 1.9, tipo="resultado", liga="Premier"),
              pk(2, "Total - Home", "Over 1.5", 1.9, liga="Serie A")] \
            + [pk(9, "Total - Home", "Over 0.5", 1.2, liga="Bundesliga")]
        c = P.combis_estilo("2026-10-27", ps, [], set()).get("atreve")
        self.assertTrue(c and all(p["cuota"] >= 1.7 for p in c["picks"]) and len(c["picks"]) <= 3)

    def test_no_repite_selecciones_usadas(self):
        ps = [pk(i, "Total - Away", "Over 0.5", 1.5) for i in range(4)]
        usados = {(p["partido_id"], p["mercado"], p["opcion"]) for p in ps}
        self.assertEqual(P.combis_estilo("2026-10-31", ps, [], usados), {})


if __name__ == "__main__":
    unittest.main()
