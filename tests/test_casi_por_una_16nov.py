"""16/11 (Marcos: «si alguna muy gorda falla por uno, se sube»)."""
import unittest
from datetime import datetime

import verdes_auto as V


def combi(pid, estados, cuota=1.8):
    return {"id": pid, "titulo": "COMBI", "estado": "rojo" if "rojo" in estados else "pendiente",
            "picks": [{"texto": f"Pata {i}", "estado": e, "cuota": cuota, "estado_partido": "FT"} for i, e in enumerate(estados)]}


class CasiPorUna16Nov(unittest.TestCase):
    ahora = datetime(2026, 11, 16, 23, 0)

    def test_gorda_por_una_sale_con_ok(self):
        d = {"publicados_hoy": [combi("2026-11-16-loca-th-0400-x100", ["verde"] * 7 + ["rojo"])]}   # 1,8^8 ≈ 110
        n = V.casi_por_una(d, set(), self.ahora, set())
        self.assertEqual(len(n), 1)
        self.assertTrue(n[0]["requiere_ok"])
        self.assertEqual(n[0]["solo_en"], ["threads"])
        self.assertIn("Solo falló: Pata 7", n[0]["texto"])
        self.assertIn("7 de 8", n[0]["texto"])

    def test_no_sale(self):
        casos = [combi("2026-11-16-loca-th-x", ["verde"] * 6 + ["rojo", "rojo"]),                 # falla por dos
                 combi("2026-11-16-loca-th-y", ["verde", "verde", "rojo"]),                        # x5,8: no es gorda
                 combi("2026-11-16-loca-th-lista-corners", ["verde"] * 7 + ["rojo"]),             # una lista
                 combi("2026-11-16-boleto-larga", ["verde"] * 7 + ["rojo"])]                      # boleto de Marcos
        pend = combi("2026-11-16-loca-th-z", ["verde"] * 7 + ["rojo"])
        pend["picks"][0]["estado_partido"] = "2H"                                                   # sin acabar
        casos.append(pend)
        self.assertEqual(V.casi_por_una({"publicados_hoy": casos}, set(), self.ahora, set()), [])

    def test_una_sola_vez(self):
        d = {"publicados_hoy": [combi("2026-11-16-loca-th-0400-x100", ["verde"] * 7 + ["rojo"])]}
        hechos = set()
        V.casi_por_una(d, hechos, self.ahora, set())
        self.assertEqual(V.casi_por_una(d, hechos, self.ahora, set()), [])


if __name__ == "__main__":
    unittest.main()
