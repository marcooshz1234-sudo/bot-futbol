"""17/11: el «Gana Corea @1,40» que metió Claude a mano salió sin sel: el bot no lo siguió y su verde no salía."""
import unittest

import comprobar_post as C


class ClaudeConSel(unittest.TestCase):
    def test_sin_sel_no_sale(self):
        self.assertTrue(C.sin_sel_claude({"id": "2026-11-17-pick-claude-1", "origen": "claude", "texto": "🍀 Gana Corea"}))

    def test_con_sel_si(self):
        self.assertIsNone(C.sin_sel_claude({"id": "x", "origen": "claude", "sel": ["1647369|Match Winner|Away"]}))

    def test_bot_y_threads_no_aplica(self):
        self.assertIsNone(C.sin_sel_claude({"id": "x", "origen": "bot"}))
        self.assertIsNone(C.sin_sel_claude({"id": "x", "origen": "claude", "solo_en": ["threads"]}))


if __name__ == "__main__":
    unittest.main()
