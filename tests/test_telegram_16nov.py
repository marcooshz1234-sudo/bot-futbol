"""16/11 (Marcos): a las 03:11 salió en Telegram una copia de tipster «Gana Eslovenia» sin explicación y antes del
buenos días; el buenos días ponía «Hoy en el canal» con solo la escalera. Además, en Threads/IG nada de picks sueltos."""
import json
import unittest
from datetime import datetime
from unittest import mock

import publicar_telegram as T
import redes


class Telegram16Nov(unittest.TestCase):
    def test_nada_antes_del_buenos_dias(self):
        from bot import MADRID
        madrugada = datetime(2026, 11, 16, 3, 11, tzinfo=MADRID)
        with mock.patch("pathlib.Path.read_text", return_value=json.dumps({"buenos_dias": "2026-11-15"})):
            self.assertTrue(T.espera_buenos_dias({"id": "2026-11-16-pick-tip-1"}, madrugada))
            self.assertFalse(T.espera_buenos_dias({"id": "2026-11-16-verde-auto-x"}, madrugada))   # resultados sí
        with mock.patch("pathlib.Path.read_text", return_value=json.dumps({"buenos_dias": "2026-11-16"})):
            self.assertFalse(T.espera_buenos_dias({"id": "2026-11-16-pick-tip-1"}, madrugada.replace(hour=10)))

    def test_porque(self):
        self.assertTrue(T.sin_porque("Este nos encanta 🔥\n🧠 Pensada con calma, sin prisas\n\n🍀 Gana el Eslovenia @1,53"))
        self.assertFalse(T.sin_porque("🍀 Gana X\n\n🧠 Por qué:\n• Serbia ya es última"))
        self.assertFalse(T.sin_porque("🍀 Gana X\n👨‍💻 El X ha ganado 4 de 5"))

    def test_texto_corto_deja_el_porque(self):
        import tarjeta_tg
        t = tarjeta_tg.texto_corto("🍀 Gana X @1,5\n\n⚽ A – B · 20:45\n\n👨‍💻 El X ha ganado 4 de sus últimos 5.")
        self.assertIn("👨‍💻", t)
        self.assertNotIn("⚽ A – B", t)

    def test_buenos_dias_sin_lista(self):
        import inspect
        import marca_tg
        self.assertNotIn("Hoy en el canal", inspect.getsource(marca_tg.buenos_dias))

    def test_pick_suelto_no_va_a_threads(self):
        self.assertTrue(redes.pick_suelto({"id": "2026-11-16-pick-tip-1", "sel": ["1|Match Winner|Away"]}))
        self.assertFalse(redes.pick_suelto({"id": "2026-11-16-combi-m", "sel": ["1|a|b", "2|a|b"]}))
        self.assertFalse(redes.pick_suelto({"id": "2026-11-16-escalera", "sel": ["1|a|b"]}))


if __name__ == "__main__":
    unittest.main()
