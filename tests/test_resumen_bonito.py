"""13/11 (Marcos: «poner no sé cuántos fallados queda muy feo… busca una manera para que quede bien»)."""
import unittest

import resumen_dia as R


def pk(i, t, e, cuota=None):
    return {"partido_id": i, "texto": t, "estado": e, "estado_partido": "FT", "cuota": cuota}


class ResumenBonito(unittest.TestCase):
    def setUp(self):
        self.posts = [
            {"id": "2026-11-12-pick-seguro", "fecha": "2026-11-12T10:30", "titulo": "Pick", "estado": "verde",
             "picks": [pk(1, "Gana el Albacete", "verde", 1.53)]},
            {"id": "2026-11-12-pick-tip-4", "fecha": "2026-11-12T12:00", "titulo": "Pick", "estado": "verde",
             "picks": [pk(2, "Más de 2,5 goles en Turquía–Bélgica", "verde", 1.5)]},
            {"id": "2026-11-12-pick-tip-6", "fecha": "2026-11-12T12:00", "titulo": "Pick", "estado": "verde",
             "picks": [pk(3, "España gana al descanso", "verde", 1.61)]},
            {"id": "2026-11-12-pick-tip-5", "fecha": "2026-11-12T12:00", "titulo": "Pick", "estado": "rojo",
             "picks": [pk(4, "Inglaterra hándicap -1,5", "rojo")]},
            {"id": "2026-11-12-combi-multi", "fecha": "2026-11-12T14:30", "titulo": "Combi", "estado": "rojo",
             "picks": [pk(5, "Calvo Sotelo marca", "rojo"), pk(6, "Barça marca 3 o más", "rojo"), pk(7, "Chipre marca", "verde")]},
        ]
        self.cola = [{"id": "2026-11-12-pick-seguro", "texto": "🍀 Gana el Albacete @1,53"}]

    def test_sin_fallados_y_con_los_verdes(self):
        picks, _ = R.picks_dia(self.posts, "2026-11-12")
        t, _ = R.textos_picks(picks, "2026-11-12", self.posts, self.cola)
        self.assertNotIn("❌", t)
        self.assertNotIn("fallad", t.lower())
        self.assertIn("✅ 4 picks en verde hoy", t)
        self.assertIn("🎯 Picks sueltos: 3 de 4 acertados", t)   # los sueltos, aparte de las combis
        self.assertIn("✅ Gana el Albacete @1,53", t)
        self.assertNotIn("Calvo Sotelo", t)
        self.assertLessEqual(len(t), 500)

    def test_numeros_malos_no_salen(self):
        posts = [dict(p, estado="rojo", picks=[dict(x, estado="rojo") for x in p["picks"]]) for p in self.posts[:2]]
        posts += self.posts[2:]
        picks, _ = R.picks_dia(posts, "2026-11-12")
        t, _ = R.textos_picks(picks, "2026-11-12", posts, self.cola)
        self.assertIsNone(t)   # 2 verdes: no hay resumen


if __name__ == "__main__":
    unittest.main()
