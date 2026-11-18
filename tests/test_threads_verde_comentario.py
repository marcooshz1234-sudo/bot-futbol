"""18/11 (Marcos): cada acierto de un post de Threads va en el comentario de ese mismo post, sea cual sea la cuota."""
import unittest
from unittest import mock

import redes


class VerdeEnSuHilo(unittest.TestCase):
    def test_verde_de_post_de_threads(self):
        p = {"id": "2026-11-18-verde-auto-2026-11-17-loca-th-0300-duelo", "verde_de": "2026-11-17-loca-th-0300-duelo",
             "resultado": "verde", "texto": "PARA DENTRO SEÑORES ✅\n\n📈 Cuota @2,26", "solo_en": ["threads"]}
        with mock.patch.object(redes, "hilo_original", return_value="1810"):
            self.assertTrue(redes.verde_en_su_hilo(p))
            self.assertTrue(redes.resultado_sin_cuoton(p))   # cuota baja: sin la regla nueva no saldría

    def test_sin_post_en_threads_no(self):
        p = {"id": "x-verde-auto-y", "verde_de": "y", "resultado": "verde"}
        with mock.patch.object(redes, "hilo_original", return_value=None):
            self.assertFalse(redes.verde_en_su_hilo(p))

    def test_rojo_y_balance_no(self):
        with mock.patch.object(redes, "hilo_original", return_value="1810"):
            self.assertFalse(redes.verde_en_su_hilo({"id": "a-rojo-auto-b", "rojo_de": "b"}))
            self.assertFalse(redes.verde_en_su_hilo({"id": "2026-11-18-balance-auto", "verde_de": "b"}))


class ListasDeThreadsTambien(unittest.TestCase):
    def test_listas_loca_th_cuentan(self):
        src = open(redes.RAIZ / "verdes_auto.py", encoding="utf-8").read() if hasattr(redes, "RAIZ") else \
            open("verdes_auto.py", encoding="utf-8").read()
        self.assertNotIn('not re.search(r"-lista-|ganadores"', src)


if __name__ == "__main__":
    unittest.main()
