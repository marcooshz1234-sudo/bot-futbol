"""13/11 (Marcos: «esto sigue sin salir como quiero, el logo con el círculo blanco»): la tarjeta de Threads de los
ganadores se hizo con la plantilla vieja y 6 equipos, y no se rehacía porque solo se miraba si el archivo existía."""
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import ganadores_win as GW
import imagenes


class TarjetaGanadores(unittest.TestCase):
    def test_se_rehace_si_cambian_los_equipos_o_la_plantilla(self):
        p = {"id": "2026-11-13-ganadores-nations", "ganadores_img": {"titulo": "NATIONS", "filas": [{"nombre": "A"}]}}
        with tempfile.TemporaryDirectory() as d, mock.patch.object(imagenes, "MEDIA", Path(d)):
            self.assertFalse(GW.tarjeta_al_dia(p))
            Path(d, f"{p['id']}.tarjeta.jpg").write_bytes(b"x")
            self.assertFalse(GW.tarjeta_al_dia(p))   # existe, pero sin huella (hecha con la plantilla vieja)
            Path(d, f"{p['id']}.tarjeta.firma").write_text(GW.huella_tarjeta(p))
            self.assertTrue(GW.tarjeta_al_dia(p))
            p["ganadores_img"]["filas"].append({"nombre": "B"})
            self.assertFalse(GW.tarjeta_al_dia(p))   # cambian los equipos → se rehace
            Path(d, f"{p['id']}.tarjeta.firma").write_text(GW.huella_tarjeta(p))
            with mock.patch.object(GW, "VERSION_TARJETA", "otra"):
                self.assertFalse(GW.tarjeta_al_dia(p))   # cambia la plantilla → se rehace


if __name__ == "__main__":
    unittest.main()
