"""Pruebas de las reglas de actualización (scripts/actualizar_cifras.py). No necesitan capturas.

Correr con:  python -m unittest discover tests
"""
import unittest

from scripts.actualizar_cifras import aplicar, cifra


class Cifras(unittest.TestCase):
    def test_textos_de_la_red(self):
        self.assertEqual(cifra("4.9K"), (4900, True))
        self.assertEqual(cifra("85.9K"), (85900, True))
        self.assertEqual(cifra("1.2M"), (1200000, True))
        self.assertEqual(cifra("4,9 mil"), (4900, True))
        self.assertEqual(cifra("1,234"), (1234, False))
        self.assertEqual(cifra(363), (363, False))
        self.assertIsNone(cifra(""))
        self.assertIsNone(cifra(None))


class Reglas(unittest.TestCase):
    base = {"publications": {"A": {"views": 85900, "likes": 4779, "comments": 42}},
            "creators": {"x": {"followers": 511592}}}

    def test_solo_sube(self):
        cap, _ = aplicar(self.base, {"publicaciones": {"A": {"views": 81248, "comments": 40}}})
        self.assertEqual(cap["publications"]["A"]["views"], 85900)
        self.assertEqual(cap["publications"]["A"]["comments"], 42)

    def test_redondeado_mayor_se_usa_con_aprox(self):
        cap, _ = aplicar(self.base, {"publicaciones": {"A": {"likes": "4.9K"}}})
        self.assertEqual(cap["publications"]["A"]["likes"], 4900)
        self.assertEqual(cap["publications"]["A"]["aprox"], ["likes"])

    def test_redondeado_menor_no_se_usa(self):
        cap, _ = aplicar(self.base, {"publicaciones": {"A": {"likes": "4.7K"}}})
        self.assertEqual(cap["publications"]["A"]["likes"], 4779)
        self.assertNotIn("aprox", cap["publications"]["A"])

    def test_exacto_mayor_quita_aprox(self):
        b = {"publications": {"A": {"likes": 4900, "aprox": ["likes"]}}}
        cap, _ = aplicar(b, {"publicaciones": {"A": {"likes": 4950}}})
        self.assertEqual(cap["publications"]["A"]["likes"], 4950)
        self.assertNotIn("aprox", cap["publications"]["A"])

    def test_seguidores_reflejan_hoy(self):
        cap, _ = aplicar(self.base, {"seguidores": {"x": 510234}})
        self.assertEqual(cap["creators"]["x"]["followers"], 510234)

    def test_no_se_borra_nada(self):
        cap, _ = aplicar(self.base, {"publicaciones": {"B": {"views": 10}}})
        self.assertIn("A", cap["publications"])
        self.assertEqual(self.base["publications"]["A"]["likes"], 4779)  # la base no se modifica


if __name__ == "__main__":
    unittest.main()
