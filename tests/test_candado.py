"""Candado del build: no construir con datos más viejos que los del reporte ya publicado."""
import tempfile
import unittest
from pathlib import Path

from scripts.build_reporte import CapturaVieja, captura_del_reporte, verificar_frescura


class Candado(unittest.TestCase):
    def test_bloquea_captura_vieja(self):
        # Caso del 26-nov-2026: equipo con la captura del 4-nov, reporte construido el 26-nov
        with self.assertRaises(CapturaVieja):
            verificar_frescura("2026-11-04", "2026-11-26")

    def test_bloquea_sin_captura(self):
        with self.assertRaises(CapturaVieja):
            verificar_frescura(None, "2026-11-26")

    def test_deja_pasar_la_corrida_del_optiplex(self):
        verificar_frescura("2026-11-27", "2026-11-26")   # captura nueva
        verificar_frescura("2026-11-26", "2026-11-26")   # misma fecha (segunda corrida del día)
        verificar_frescura("2026-11-04", None)           # aún no hay reporte construido

    def test_lee_la_fecha_del_reporte(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "index.html"
            self.assertIsNone(captura_del_reporte(p))
            p.write_text('<script>var DATA={"campaign":{"id":"2026-10","captured_on":"2026-11-26"}};</script>',
                         encoding="utf-8")
            self.assertEqual(captura_del_reporte(p), "2026-11-26")


if __name__ == "__main__":
    unittest.main()
