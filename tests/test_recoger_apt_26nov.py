"""26/11: la recogida falló 3 veces seguidas porque «apt-get install» sin «apt-get update» daba 404 y el paso
de imágenes tumbaba todo (no se guardaban datos, escalera ni posts de mañana)."""
import unittest
from pathlib import Path

WF = Path(__file__).resolve().parent.parent / ".github" / "workflows"


class RecogerApt(unittest.TestCase):
    def test_apt_update_antes_de_install(self):
        for nombre in ("recoger.yml", "asistente.yml"):
            s = (WF / nombre).read_text(encoding="utf-8")
            for linea in s.splitlines():
                if "apt-get install" in linea and not linea.strip().startswith("#"):
                    antes = s[:s.index(linea)]
                    self.assertIn("apt-get update", antes + linea, nombre)

    def test_imagenes_no_bloquea_y_se_guarda_siempre(self):
        s = (WF / "recoger.yml").read_text(encoding="utf-8")
        paso = s.split("- name: Imágenes y reels")[1].split("- name:")[0]
        for linea in paso.splitlines():
            if "apt-get install" in linea or "playwright install" in linea:
                self.assertIn("||", linea)
        guardar = s.split("- name: Guardar cambios")[1].split("run:")[0]
        self.assertIn("if: always()", guardar)


if __name__ == "__main__":
    unittest.main()
