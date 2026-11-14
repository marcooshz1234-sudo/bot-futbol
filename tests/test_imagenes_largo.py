"""14/11: una combi de 11 patas se salía por arriba en vertical (1920) y bloqueaba las imágenes de los demás posts."""
import unittest

from playwright.sync_api import sync_playwright

import imagenes

LARGO = {"id": "t-largo", "fecha": "2026-11-21T10:00", "tipo": "combi", "foto": None,
         "texto": "VAMOS CON LA COMBI DEL DÍA FAMILIA 🔥\n\n" + "\n".join(
             f"🏴 Más de 1,5 goles en la 2ª parte del Equipo Largo {i}-Otro Equipo Larguísimo {i}" for i in range(11))
         + "\n\nℹ️ No hace falta coger todos los picks: es info de los que hemos analizado entre todos los partidos. "
           "Quédate con los que más te gusten 👌\n\n📈 Cuota @685,87"}


class ImagenLarga(unittest.TestCase):
    def test_vertical_largo_cabe(self):
        doc, total = imagenes.documento(LARGO, True, mostrar=99)
        with sync_playwright() as pw:
            nav = pw.chromium.launch()
            pg = nav.new_page(viewport={"width": 1080, "height": 1920})
            pg.set_content(doc)
            pg.wait_for_timeout(100)
            imagenes.ajustar_al_lienzo(pg, 1920)   # antes: «Texto recortado por arriba»
            nav.close()


if __name__ == "__main__":
    unittest.main()
