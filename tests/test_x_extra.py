"""20/11 (Marcos: «mira en X qué le funciona a la gente para copiarlo» → «monta todo»): formatos nuevos de X."""
import sys
import unittest
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import x_extra as xe  # noqa: E402

M = ZoneInfo("Europe/Madrid")
AHORA = datetime(2026, 11, 19, 23, 0, tzinfo=M)
ESC = {"actual": {"dia": "2026-11-19", "escalon": 3, "stake": 62.28, "cuota": 1.8,
                  "anterior": {"dia": "2026-11-18", "escalon": 2, "stake": 34.6, "cuota": 1.8,
                               "anterior": {"dia": "2026-11-17", "escalon": 1, "stake": 20.0, "cuota": 1.73,
                                            "anterior": {"dia": "2026-11-16", "escalon": 1, "stake": 20.0, "cuota": 1.8}}}}}


class XExtra(unittest.TestCase):
    def test_apagado_sin_ok(self):
        self.assertFalse(xe.activo({}))
        self.assertTrue(xe.activo({"x_extra": True}))

    def test_escalera_presumida(self):
        t = xe.escalera_x(ESC, "2026-11-19")
        self.assertIn("DÍA 3/7 SUPERADO", t)
        self.assertIn("✅ Día 1 · 1,73\n✅ Día 2 · 1,80\n✅ Día 3 · 1,80", t)
        self.assertIn("20,00€ → 112,10€", t)
        self.assertEqual(xe.transformar({"id": "2026-11-19-verde-auto-2026-11-19-escalera"}, ["x"], AHORA, ESC), [t])

    def test_para_manana_y_enlace_en_el_segundo(self):
        r = xe.transformar({"id": "2026-11-20-loca-th-noche-2100-x100"}, ["🎰 LA CENTENARIA"], AHORA)
        self.assertTrue(r[0].startswith("🗓️ PARA MAÑANA · VIERNES 20/11\n🎰"))
        self.assertNotIn("t.me", r[0])                       # el enlace nunca en el principal
        self.assertIn(xe.TELEGRAM, r[1])
        self.assertEqual(xe.transformar({"id": "2026-11-19-verde-auto-x"}, ["✅"], AHORA), ["✅"])   # verdes sin enlace
        hilo = xe.transformar({"id": "2026-11-19-loca-th-x50"}, ["uno", "dos"], AHORA)
        self.assertEqual(len(hilo), 2)
        self.assertTrue(hilo[1].startswith("dos") and xe.TELEGRAM in hilo[1])

    def test_directo_una_vez_entre_60_y_80(self):
        vivo = [{"id": "2026-11-19-escalera", "estado": "pendiente", "picks": [
            {"partido": "Arsenal – Lyon", "marcador": [0, 1], "minuto": 71, "estado": "va_bien", "texto": "Gana el Lyon"}]}]
        t = xe.directo(vivo, "2026-11-19", {})
        self.assertIn("Minuto 71' · Arsenal – Lyon 0-1", t)
        self.assertIn("camino del verde", t)
        self.assertIsNone(xe.directo(vivo, "2026-11-19", {"2026-11-19": "x"}))   # ya salió hoy
        vivo[0]["picks"][0]["minuto"] = 50
        self.assertIsNone(xe.directo(vivo, "2026-11-19", {}))


if __name__ == "__main__":
    unittest.main()
