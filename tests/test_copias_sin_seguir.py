"""19/11 (Marcos: «revisa que no falta nada»): las copias de canal salían sin «sel» y el bot no las seguía
(18/11: no salió el verde del Mar Menor y el resumen decía 3 de 4; 19/11 13:42: «Más de 2,5» del Paris FC–Køge)."""
import sys
import unittest
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import copiar_tipsters as ct  # noqa: E402
import tipsters  # noqa: E402

M = ZoneInfo("Europe/Madrid")


def pk(**kw):
    d = {"dia": "2026-11-19", "texto": "Más de 2.5 goles", "partido_id": 1638327, "mercado": "Goals Over/Under",
         "opcion": "Over 2.5", "cuota": 1.53, "local": "Paris FC W", "visitante": "HB Koge W", "tipster": "X"}
    d.update(kw)
    return d


class CopiasSinSeguir(unittest.TestCase):
    def test_nombres_raros_casan(self):
        self.assertEqual(tipsters.norm("HB Køge W"), "hb koge")
        self.assertTrue(tipsters.mismo(tipsters.norm("HB Koge W"), tipsters.norm("Køge W")))
        self.assertTrue(tipsters.mismo(tipsters.norm("Paris FC W"), tipsters.norm("Paris FC W")))
        self.assertFalse(tipsters.mismo(tipsters.norm("Real Madrid"), tipsters.norm("Real Sociedad")))

    def test_con_partido_sale_y_se_sigue(self):
        ini = datetime(2026, 11, 19, 18, 45, tzinfo=M)
        p = ct.post_suelto(pk(), ini, datetime(2026, 11, 19, 13, 30, tzinfo=M), 2)
        self.assertEqual(p["sel"], ["1638327|Goals Over/Under|Over 2.5"])
        self.assertNotIn("requiere_ok", p)

    def test_sin_partido_espera_ok(self):
        ini = datetime(2026, 11, 18, 20, 30, tzinfo=M)
        p = ct.post_suelto(pk(partido_id=None, texto="Gana el Mar Menor", mercado="Match Winner", opcion="Home",
                              local="San Javier Mar Menor", visitante="Bullas Deportivo", dia="2026-11-18"),
                           ini, datetime(2026, 11, 18, 18, 0, tzinfo=M), 1)
        self.assertEqual(p["sel"], [])
        self.assertTrue(p["requiere_ok"])
        self.assertIn("no encuentra el partido", p["aviso"])

    def test_crear_apuesta_espera_ok(self):
        ini = datetime(2026, 11, 18, 18, 45, tzinfo=M)
        p = ct.post_suelto(pk(texto="Crear apuesta: gol en la 1ª mitad + más de 2 goles", partido_id=1638312,
                              mercado="Crear apuesta", opcion="x"), ini, datetime(2026, 11, 18, 13, 0, tzinfo=M), 3)
        self.assertTrue(p["requiere_ok"])
        self.assertIn("Crear apuesta", p["aviso"])

    def test_combi_con_una_pata_sin_partido_espera_ok(self):
        a = pk(_ini=datetime(2026, 11, 19, 18, 45, tzinfo=M))
        b = pk(partido_id=None, _ini=datetime(2026, 11, 19, 21, 0, tzinfo=M), local="Arsenal W", visitante="Lyon W")
        p = ct.post_combi([a, b], datetime(2026, 11, 19, 13, 0, tzinfo=M), 1)
        self.assertEqual(p["sel"], [])
        self.assertTrue(p["requiere_ok"])


if __name__ == "__main__":
    unittest.main()
