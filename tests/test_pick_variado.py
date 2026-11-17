"""16/11 (Marcos: «quiero que salga lo más probable… más de 2,5 goles si lo ves muy probable… muchas faltas…
que no sea monótono, aunque el gana o gana o empata me gusta»): el pick de Telegram sale de todos los mercados; lo
prohibido en las combis (más de 2,5 goles, tarjetas del partido) solo si es muy probable; los dos del día de tipos
distintos y lo repetido de los últimos días resta un poco."""
import sys
import unittest
from pathlib import Path
from unittest import mock

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

import bot  # noqa: E402
import combis_dia as C  # noqa: E402

DIA = "2099-06-01"


def pk(pid, mercado, opcion, cuota, prob, texto):
    return {"partido_id": pid, "fecha": f"{DIA}T20:45", "mercado": mercado, "opcion": opcion, "cuota": cuota,
            "prob_aprendida": prob, "texto": texto, "tipo": "resultado"}


GANA = pk(1, "Match Winner", "Home", 1.57, 0.70, "Gana Eslovenia")
GANA2 = pk(2, "Match Winner", "Away", 1.60, 0.69, "Gana Grecia")
CORNERS = pk(3, "Home Corners Over/Under", "Over 4.5", 1.62, 0.66, "Alemania más de 4,5 córners")
MAS25_CLARO = pk(4, "Goals Over/Under", "Over 2.5", 1.55, 0.74, "Más de 2,5 goles")
MAS25_DUDOSO = pk(5, "Goals Over/Under", "Over 2.5", 1.65, 0.66, "Más de 2,5 goles (dudoso)")
TARJETAS = pk(6, "Cards Over/Under", "Over 4.5", 1.60, 0.72, "Más de 4,5 tarjetas")
GOL_1T = pk(7, "Goals Over/Under First Half", "Over 0.5", 1.55, 0.80, "Gol en la 1ª parte")


class PickVariado(unittest.TestCase):
    def _pick(self, pools, segundo=False, recientes=()):
        with mock.patch.object(C, "pick_de_tipster", lambda *a, **k: None), \
                mock.patch.object(C, "pick_de_copa", lambda *a, **k: None), \
                mock.patch.object(C, "minimo_diario", lambda: False), \
                mock.patch.object(C, "tipos_recientes", lambda dia: list(recientes)):
            r = C.pick_seguro(pools, DIA, segundo=segundo)
        return r[0]["texto"] if r else None

    def test_mas_de_25_si_es_muy_probable(self):
        self.assertEqual(self._pick([[MAS25_CLARO, GANA]]), "Más de 2,5 goles")

    def test_mas_de_25_dudoso_no(self):
        self.assertIsNone(self._pick([[MAS25_DUDOSO]]))

    def test_tarjetas_ya_no(self):   # 17/11 (Marcos: «las de las tarjetas van fatal»): antes salían si eran muy probables
        self.assertIsNone(self._pick([[TARJETAS]]))

    def test_lo_demas_prohibido_sigue_fuera(self):
        self.assertIsNone(self._pick([[GOL_1T]]))

    def test_corners_puede_ser_pick(self):
        self.assertEqual(self._pick([[CORNERS]]), "Alemania más de 4,5 córners")

    def test_el_segundo_no_es_otro_gana(self):
        self.assertEqual(self._pick([[GANA2, CORNERS]], segundo=GANA), "Alemania más de 4,5 córners")

    def test_minimo_diario_puede_repetir_tipo(self):
        with mock.patch.object(C, "pick_de_tipster", lambda *a, **k: None), \
                mock.patch.object(C, "pick_de_copa", lambda *a, **k: None), \
                mock.patch.object(C, "minimo_diario", lambda: True), \
                mock.patch.object(C, "tipos_recientes", lambda dia: []):
            r = C.pick_seguro([[GANA2]], DIA, segundo=GANA)
        self.assertEqual(r[0]["texto"], "Gana Grecia")

    def test_no_monotono(self):
        # córners salió los 3 últimos días: aunque sea algo más probable, hoy va el «gana»
        c = dict(CORNERS, prob_aprendida=0.71)
        self.assertEqual(self._pick([[c, GANA]], recientes=["corners"] * 3), "Gana Eslovenia")

    def test_el_gana_repite_mas_facil(self):
        g = dict(GANA, prob_aprendida=0.71)
        self.assertEqual(self._pick([[g, CORNERS]], recientes=["resultado"] * 2), "Gana Eslovenia")

    def test_comprobar_post_deja_el_pick_y_no_la_combi(self):
        pick = {"id": "2099-06-01-pick-seguro", "sel": ["4|Goals Over/Under|Over 2.5"]}
        combi = {"id": "2099-06-01-combi-tres", "sel": ["4|Goals Over/Under|Over 2.5", "1|Match Winner|Home"]}
        primera = {"id": "2099-06-01-pick-seguro", "sel": ["7|Goals Over/Under First Half|Over 0.5"]}
        self.assertIsNone(bot.mercado_prohibido(pick))
        self.assertIsNotNone(bot.mercado_prohibido(combi))
        self.assertIsNotNone(bot.mercado_prohibido(primera))
        # 16/11: la copia de Pérez «más de 9,5 remates a puerta» se quedaba frenada por la regla de los picks
        copia = {"id": "2099-06-01-pick-tip-4", "origen": "tipster", "sel": ["4|Total ShotOnGoal|Over 9.5"]}
        self.assertIsNone(bot.mercado_prohibido(copia))

    def test_tipo_pick(self):
        self.assertEqual(C.tipo_pick(GANA), "resultado")
        self.assertEqual(C.tipo_pick(CORNERS), "corners")
        self.assertEqual(C.tipo_pick({"mercado": "Both Teams Cards", "opcion": "Yes"}), "tarjetas")


if __name__ == "__main__":
    unittest.main()


class PicksExtra(unittest.TestCase):
    """16/11 (Marcos: «si hay más cuotas buenas, que las meta también, y si son de diferente mercado, mejor»)."""

    def _extra(self, pools, hechos):
        with mock.patch("plantillas.choca", lambda s, otras: False):
            r = C.pick_extra(pools, DIA, (12, 30), hechos)
        return r[0]["texto"] if r else None

    def test_mejor_otro_mercado(self):
        g = dict(GANA2, prob_aprendida=0.70)
        self.assertEqual(self._extra([[g, CORNERS]], hechos=[GANA]), "Alemania más de 4,5 córners")

    def test_si_no_hay_otro_puede_repetir_tipo(self):
        self.assertEqual(self._extra([[GANA2]], hechos=[GANA]), "Gana Grecia")

    def test_sin_cuota_buena_no_sale(self):
        flojo = dict(CORNERS, prob_aprendida=0.55)
        caro = dict(CORNERS, partido_id=9, cuota=1.95, prob_aprendida=0.75)
        self.assertIsNone(self._extra([[flojo, caro]], hechos=[GANA]))

    def test_no_repite_el_mismo_pick(self):
        self.assertIsNone(self._extra([[GANA]], hechos=[GANA]))

    def test_no_choca(self):
        with mock.patch("plantillas.choca", lambda s, otras: True):
            self.assertIsNone(C.pick_extra([[CORNERS]], DIA, (12, 30), [GANA]))
