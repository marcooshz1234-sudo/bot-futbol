"""19/11 (Marcos: «automatizarlo gratis» → «prepárame lo del Buffer»): X (@combilocass) por Buffer."""
import sys
import unittest
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import x_buffer as xb  # noqa: E402

M = ZoneInfo("Europe/Madrid")
AHORA = datetime(2026, 11, 19, 21, 30, tzinfo=M)


class TextoX(unittest.TestCase):
    def test_sin_arroba_en_cuotas(self):   # en X «@1,80» es una mención a un usuario «1»
        t = xb.a_x("PARA DENTRO ✅\n\n✅ Gana el Lyon\n\n📈 Cuota @1,80")[0]
        self.assertNotIn("@", t)
        self.assertIn("Cuota 1,80", t)

    def test_cabe_en_280_y_si_no_hilo(self):
        corto = "🔥 COMBI 🔥\n\n🛡️ Benfica o empate\n\n🎯 CUOTA 2,10"
        self.assertEqual(xb.a_x(corto), [corto])
        largo = "🔥 COMBI POR 19,18 🔥\n\n" + "\n".join(f"⚽ Equipo número {i} gana el partido de esta noche · y marca" for i in range(8)) + "\n🎯 CUOTA 19,18"
        r = xb.a_x(largo)
        self.assertEqual(len(r), 2)
        self.assertTrue(all(xb.peso(t) <= 280 for t in r))
        self.assertTrue(r[0].startswith("🔥 COMBI POR 19,18"))

    def test_emojis_cuentan_doble(self):
        self.assertEqual(xb.peso("ab"), 2)
        self.assertEqual(xb.peso("🔥"), 2)
        self.assertEqual(xb.peso("🛡️"), 2)   # el selector de variante no suma


class QueSeSube(unittest.TestCase):
    def post(self, pid, fecha="2026-11-19T21:00", threads=True):
        return {"id": pid, "fecha": fecha, "texto": "x", "redes": {"threads": "1"} if threads else {}}

    def test_solo_lo_fuerte_y_ya_salido_en_threads(self):
        posts = [self.post("2026-11-19-verde-auto-2026-11-19-escalera"), self.post("2026-11-19-loca-th-2100-duelo"),
                 self.post("2026-11-19-escalera", threads=False), self.post("2026-11-19-loca-th-noche-2300-x50")]
        ids = [p["id"] for p in xb.candidatos(posts, {}, {}, AHORA)]
        self.assertEqual(ids, ["2026-11-19-verde-auto-2026-11-19-escalera", "2026-11-19-loca-th-noche-2300-x50"])
        todo = [p["id"] for p in xb.candidatos(posts, {}, {"x_modo": "todo"}, AHORA)]
        self.assertIn("2026-11-19-loca-th-2100-duelo", todo)

    def test_los_verdes_no_gastan_el_tope(self):   # 19/11: el verde de la escalera se quedó fuera por el tope
        hechos = {f"2026-11-19-loca-th-x{i}": {"cuando": "2026-11-19T1%d:00" % i} for i in range(5)}
        posts = [self.post("2026-11-19-verde-auto-2026-11-19-escalera"), self.post("2026-11-19-loca-th-noche-2300-x50")]
        ids = [p["id"] for p in xb.candidatos(posts, {"enviados": hechos}, {}, AHORA)]
        self.assertEqual(ids, ["2026-11-19-verde-auto-2026-11-19-escalera"])

    def test_no_repite_ni_sube_lo_viejo_y_respeta_tope_y_pausa(self):
        posts = [self.post(f"2026-11-19-loca-th-noche-p{i}-x50") for i in range(8)] + [self.post("2026-11-19-escalera", "2026-11-19T11:00")]
        estado = {"enviados": {"2026-11-19-loca-th-noche-p0-x50": {"cuando": "2026-11-19T21:05"}}}
        r = xb.candidatos(posts, estado, {}, AHORA)
        self.assertEqual(len(r), 4)   # tope 5 al día, ya va 1
        self.assertNotIn("2026-11-19-loca-th-noche-p0-x50", [p["id"] for p in r])
        self.assertNotIn("2026-11-19-escalera", [p["id"] for p in r])   # de las 11:00: fuera de la ventana de 3 h
        self.assertEqual(xb.candidatos(posts, {}, {"x_pausa": True}, AHORA), [])


class Buffer(unittest.TestCase):
    def test_mutacion_con_foto_y_hora(self):
        q = xb.mutacion(xb.entrada("c1", ["Hola \"X\" 🔥"], "https://raw.githubusercontent.com/a.jpg", AHORA))
        self.assertIn('channelId: "c1"', q)
        self.assertIn("schedulingType: automatic", q)
        self.assertIn("mode: customScheduled", q)
        self.assertIn('dueAt: "2026-11-19T20:30:00.000Z"', q)
        self.assertIn('assets: [{image: {url: "https://raw.githubusercontent.com/a.jpg"}}]', q)
        self.assertIn('text: "Hola \\"X\\" 🔥"', q)

    def test_duplicado_de_buffer_cuenta_como_subido(self):   # 19/11: no puede atascar lo siguiente
        self.assertTrue(xb.YA_ESTA.search("Invalid post: Whoops, it looks like you've already got this one scheduled"))

    def test_hilo(self):
        q = xb.mutacion(xb.entrada("c1", ["uno", "dos"], None, AHORA))
        self.assertIn('metadata: {twitter: {thread: [{text: "uno"}, {text: "dos"}]}}', q)

    def test_sin_clave_no_hace_nada(self):
        import os
        import tempfile
        from unittest import mock
        import bot
        with tempfile.TemporaryDirectory() as d, mock.patch.object(bot, "DATOS", Path(d)), \
                mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop("BUFFER_TOKEN", None)
            self.assertEqual(xb.main(AHORA), 0)
            self.assertFalse(bot.leer(Path(d) / xb.ESTADO_F, {})["clave"])

    def test_en_el_bucle_con_su_secreto(self):
        wf = (Path(__file__).resolve().parent.parent / ".github" / "workflows" / "telegram.yml").read_text(encoding="utf-8")
        self.assertIn("BUFFER_TOKEN: ${{ secrets.BUFFER_TOKEN }}", wf)
        self.assertIn("paso x_buffer 120 x_buffer.py", wf)
        self.assertIn("datos/x_buffer.json; do", wf)   # 19/11: si no se guarda, entre tandas se repetían los posts


if __name__ == "__main__":
    unittest.main()
