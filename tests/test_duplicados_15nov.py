"""15/11: Madrid CFF y Finlandia salieron 2 veces en Telegram y Bélgica–Italia 3 veces en Threads; y el resumen decía
«7 de 10» con solo 4 en «Para dentro» (faltaba el de España–Inglaterra, subido la noche antes)."""
import unittest
from unittest import mock

import comprobar_post as C
import resumen_dia as R


def post(i, texto, **k):
    return {"id": i, "fecha": i[:10] + "T12:00", "texto": texto, **k}


class Duplicados(unittest.TestCase):
    def test_mismo_pick_otra_vez_en_la_misma_red(self):
        a = post("2026-11-15-pick-tip-1", "🍀 Madrid CFF · empate no válido @1,44", enviado="2026-11-15T11:22",
                 redes={"threads": "1"})
        b = post("2026-11-15-pick-tip-1-2", "Otra vez 🔥\n🍀 Madrid CFF · empate no válido @1,44", solo_en=["telegram"])
        with mock.patch.object(C, "leer", return_value=[]):
            self.assertIn("ya salió", C.duplicado(b, cola=[a, b]))
            # en otra red sí (la foto para Instagram aparte)
            self.assertIsNone(C.duplicado(dict(b, solo_en=["instagram"]), cola=[a, b]))
        # si Marcos borró el original, se puede volver a subir
        with mock.patch.object(C, "leer", side_effect=lambda f, d=None: ["2026-11-15-pick-tip-1"] if "borrados" in str(f) else []):
            self.assertIsNone(C.duplicado(b, cola=[a, b]))


class ResumenCuadra(unittest.TestCase):
    def test_cuenta_igual_que_la_lista_y_cuenta_lo_subido_la_noche_antes(self):
        pk = lambda t, e: {"texto": t, "estado": e, "partido_id": 1, "mercado": t, "opcion": "x"}
        posts = [
            {"id": "2026-11-15-pick-tip-1", "fecha": "2026-11-14T22:37", "estado": "verde",
             "picks": [pk("Más de 2,5 goles en España–Inglaterra", "verde")]},
            {"id": "2026-11-15-pick-seguro", "fecha": "2026-11-15T10:30", "estado": "rojo",
             "picks": [pk("Bielorrusia marca", "rojo")]},
            {"id": "2026-11-15-pick-seguro-b", "fecha": "2026-11-15T11:41", "estado": "verde",
             "picks": [pk("Gana Croacia", "verde")]},
        ]
        cola = [{"id": p["id"], "texto": f"🍀 x @1,{60 - i}"} for i, p in enumerate(posts)]
        t, _ = R.textos_picks([x for p in posts for x in p["picks"]], "2026-11-15", posts, cola)
        self.assertIn("2 de 3 picks en verde", t)
        self.assertIn("España–Inglaterra", t)
        self.assertEqual(t.count("\n✅ "), 3)   # la cabecera + los 2 de «Para dentro»


if __name__ == "__main__":
    unittest.main()
