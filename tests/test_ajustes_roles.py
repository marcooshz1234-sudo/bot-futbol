"""10/11: ajustes de cada rol de la Oficina (ajustes.py, panel_acciones «ajuste/canal/verde»)."""
import unittest
from unittest import mock

import ajustes
import combis_dia
import panel_acciones


class Ajustes(unittest.TestCase):
    def test_por_defecto_lo_de_siempre(self):
        c = {}
        self.assertEqual((ajustes.valor("pick_cuota_min", c), ajustes.valor("pick_cuota_max", c)), combis_dia.SEGURO_NUEVO["cuota"])
        self.assertEqual(ajustes.hora("hora_pick1", c), combis_dia.SEGURO["hora"])
        self.assertEqual(ajustes.hora("hora_pick2", c), combis_dia.SEGURO_NUEVO["hora2"])
        for rol in ajustes.ROLES:
            self.assertFalse(ajustes.pausado(rol, c))
        self.assertTrue(ajustes.valor("pick_razones", c) and ajustes.valor("pick_stake", c) and ajustes.valor("rojos_pick", c))

    def test_puesto_desde_el_panel(self):
        c = {"ajustes": {"pausa_ojeador": True, "pick_cuota_max": 1.8}, "canales_off": ["INSIDER"]}
        self.assertTrue(ajustes.pausado("ojeador", c))
        self.assertEqual(ajustes.valor("pick_cuota_max", c), 1.8)
        self.assertEqual(ajustes.canales_off(c), {"INSIDER"})

    def _aplicar(self, acc, control):
        guardado = {}
        with mock.patch.object(panel_acciones, "leer", side_effect=lambda r, d=None: control if r == panel_acciones.CONTROL else d), \
             mock.patch.object(panel_acciones, "publicaciones", return_value=[]), \
             mock.patch.object(panel_acciones, "escribir", side_effect=lambda r, d: guardado.__setitem__(r, d)):
            lineas, _ = panel_acciones.aplicar({"v": 1, "acc": acc})
        return lineas, control

    def test_acciones(self):
        lineas, c = self._aplicar([{"a": "ajuste", "k": "saludo_pick", "v": "  Hoy va fuerte   familia 🔥 "},
                                   {"a": "ajuste", "k": "pick_cuota_min", "v": 0.5},
                                   {"a": "canal", "n": "TipsPro", "v": False},
                                   {"a": "verde", "id": "2026-11-10-verde-x", "ok": True}],
                                  {"por_aprobar": {"abc": "2026-11-10-verde-x"}})
        self.assertEqual(c["ajustes"]["saludo_pick"], "Hoy va fuerte familia 🔥")
        self.assertEqual(c["ajustes"]["pick_cuota_min"], 1.2)   # no baja del mínimo
        self.assertEqual(c["canales_off"], ["TipsPro"])
        self.assertIn("2026-11-10-verde-x", c["aprobados"])
        self.assertTrue(any("Redactor" in l for l in lineas))


if __name__ == "__main__":
    unittest.main()
