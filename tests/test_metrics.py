"""Pruebas de cuadre: las cifras del reporte deben coincidir con las fichas aprobadas.

Correr con:  python -m unittest discover tests
"""
import unittest

from pipeline.metrics import build_data, emv, roi
from pipeline.util.config import latest_capture, load_campaign, load_client


class CuadreOctubre(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = build_data(load_client(), load_campaign("2026-10"))
        cls.by = {c["handle"]: c for c in cls.data["creators"]}

    def test_siberek_tiktok_con_compartidos_y_guardados(self):
        tt = next(p for p in self.by["siberekk"]["posts"] if p["net"] == "tt")
        self.assertEqual(tt["emv"], 58600 * 7200 + 305 * 10500 + 849 * 12350 + 3613 * 13560)
        self.assertEqual(self.by["siberekk"]["t"]["emv"], 630_889_530)
        self.assertEqual(self.by["siberekk"]["nets"], ["TikTok", "Instagram", "YouTube"])

    def test_emv_formula_del_cliente(self):
        v = load_client()["emv"]["valores"]
        self.assertEqual(emv({"likes": 1, "comments": 1, "shares": 1, "saves": 1}, v), 7200 + 10500 + 12350 + 13560)

    def test_esteban_go(self):
        c = self.by["estebango__"]
        self.assertEqual(c["t"]["views"], 71500)
        self.assertEqual(c["t"]["inter"], 4489)
        self.assertEqual(c["t"]["emv"], 32_452_800)
        self.assertAlmostEqual(c["er"], 0.0628, places=4)
        self.assertEqual(c["med"], 232000)
        self.assertEqual(round(c["idx"], 2), 0.31)
        self.assertTrue(c["isMin"])

    def test_una_reina_del_drama(self):
        c = self.by["unareinadeldrama"]
        self.assertEqual(c["t"]["emv"], 2_165_400 + 342_130)  # reel + TikTok
        self.assertAlmostEqual(c["er"], (292 + 6 + 26 + 5) / (10_400 + 531), places=4)
        self.assertEqual(c["med"], 23550)
        self.assertEqual(round(c["idx"], 2), 0.44)
        self.assertTrue(c["isMin"])

    def test_totales_igual_suma_de_partes(self):
        T = self.data["totals"]
        self.assertEqual(T["emv"], sum(c["t"]["emv"] for c in self.data["creators"]))
        self.assertEqual(T["emv"], 34_618_200 + 342_130 + 630_889_530)
        self.assertEqual(T["views"], 81_900 + 531 + 264_800 + 141_000 + 27_289)
        self.assertEqual(T["inter"], 4_787 + 31 + 58_905 + 16_588 + 3_653)
        self.assertEqual(sum(n["emv"] for n in self.data["networks"]), T["emv"])

    def test_ranking_por_emv(self):
        self.assertEqual([c["handle"] for c in self.data["creators"]], ["siberekk", "estebango__", "unareinadeldrama"])
        emvs = [p["emv"] for p in self.data["posts"]]
        self.assertEqual(emvs, sorted(emvs, reverse=True))

    def test_pago_por_accion(self):
        # Valor para LCI ÷ número de acciones del talento
        self.assertEqual(self.by["estebango__"]["t"]["pay"], 8_904_056)
        self.assertEqual(self.by["unareinadeldrama"]["t"]["pay"], round(10_893_260 / 4))
        self.assertEqual(self.data["totals"]["pay"], 8_904_056 + 2_723_315 + 3_300_000)
        self.assertEqual(self.by["siberekk"]["perAction"], 1_100_000)

    def test_salidas_pendientes_y_ejecucion(self):
        r = self.by["unareinadeldrama"]
        self.assertEqual((r["done"], r["actions"]), (1, 4))
        self.assertEqual(r["roiNote"], "aún faltan 3 acciones por validar")
        self.assertIsNone(self.by["estebango__"]["roiNote"])
        T = self.data["totals"]
        self.assertEqual((T["budget"], T["budgetActions"], T["done"]), (152_617_206, 22, 5))

    def test_salida_agrupada(self):
        # Reel + TikTok de Reina cuentan como 1 salida y se reparten su valor
        r = self.by["unareinadeldrama"]
        self.assertEqual(len(r["posts"]), 2)
        self.assertEqual(r["done"], 1)
        self.assertEqual(r["t"]["pay"], round(10_893_260 / 4))
        self.assertEqual(r["roiNote"], "aún faltan 3 acciones por validar")

    def test_roi_solo_con_pago(self):
        self.assertIsNone(roi(1000, None))
        self.assertEqual(roi(3000, 1000), 2.0)


@unittest.skipUnless(latest_capture("2026-10"), "sin captura local en datos/capturas/2026-10")
class CapturaOctubre(unittest.TestCase):
    """Captura del 30 oct 2026 leída de Instagram. Solo corre donde exista la captura local."""

    @classmethod
    def setUpClass(cls):
        cap = latest_capture("2026-10")
        cls.data = build_data(load_client(), load_campaign("2026-10"), cap)
        cls.by = {c["handle"]: c for c in cls.data["creators"]}

    def test_siberek_captura(self):
        c = self.by["siberekk"]
        self.assertEqual(c["med"], 210_000)
        self.assertEqual(round(c["idx"], 2), 0.67)
        t = c["talk"]
        self.assertEqual((t["read"], t["pos"], t["neu"], t["neg"]), (115, 37, 73, 5))
        self.assertEqual(c["top"][0][1], 2423)

    def test_ventana_ultimos_12_hasta_el_corte(self):
        for c in self.data["creators"]:
            self.assertEqual(len(c["reels"]), 12)
            self.assertEqual(sum(1 for i in range(12) if i == c["lci"]), 1)

    def test_esteban_go(self):
        c = self.by["estebango__"]
        self.assertEqual(c["followers"], 511_592)
        self.assertEqual(c["t"]["emv"], 4779 * 7200 + 42 * 10500)
        self.assertEqual(c["med"], 239_000)
        self.assertEqual(round(c["idx"], 2), 0.36)
        self.assertEqual(c["reels"][0][1], "24 sep")
        self.assertEqual(c["marks"], {"3": "A", "5": "B", "9": "C"})

    def test_una_reina_del_drama(self):
        c = self.by["unareinadeldrama"]
        self.assertEqual(c["t"]["emv"], 302 * 7200 + 6 * 10500 + 26 * 7200 + 5 * 10500 + 5 * 12350 + 3 * 13560)
        self.assertEqual(c["med"], 20_500)
        self.assertEqual(round(c["idx"], 2), 0.53)
        self.assertEqual(c["posts"][0]["date"], "8 oct 2026")

    def test_total(self):
        self.assertEqual(self.data["totals"]["emv"], 37_087_200 + 342_130 + 630_889_530)

    def test_roi(self):
        self.assertEqual(round(self.by["estebango__"]["roi"] * 100), 291)
        self.assertEqual(round(self.by["unareinadeldrama"]["roi"] * 100), -5)
        self.assertEqual(round(self.data["totals"]["roi"] * 100), 4377)

    def test_cpv_cpe(self):
        e = self.by["estebango__"]
        self.assertEqual(round(e["cpv"]), round(8_904_056 / 85_900))
        self.assertEqual(round(e["cpe"]), round(8_904_056 / (4779 + 42)))
        T = self.data["totals"]
        self.assertAlmostEqual(T["cpv"], T["pay"] / T["views"])

    def test_conversacion_desde_la_captura(self):
        t = self.by["estebango__"]["talk"]
        self.assertEqual((t["read"], t["pos"], t["neu"], t["neg"]), (37, 14, 17, 6))
        self.assertEqual(self.by["estebango__"]["top"][0][1], 147)
        r = self.by["unareinadeldrama"]["talk"]
        self.assertEqual((r["read"], r["pos"]), (3, 3))


if __name__ == "__main__":
    unittest.main()
