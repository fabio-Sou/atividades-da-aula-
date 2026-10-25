import math
import unittest

from calculadora import calcular


class TestCalculadora(unittest.TestCase):
    def test_operacoes_basicas(self):
        self.assertEqual(calcular("8+2"), 10)
        self.assertEqual(calcular("8-2"), 6)
        self.assertEqual(calcular("8*2"), 16)
        self.assertEqual(calcular("8/2"), 4)

    def test_potencia_e_raiz(self):
        self.assertEqual(calcular("2^3"), 8)
        self.assertEqual(calcular("sqrt(25)"), 5)

    def test_constantes_e_funcoes_logaritmicas(self):
        self.assertAlmostEqual(calcular("sin(pi/2)", graus=False), 1)
        self.assertEqual(calcular("ln(e)"), 1)
        self.assertEqual(calcular("log(100)"), 2)

    def test_trigonometria_em_graus_e_radianos(self):
        self.assertAlmostEqual(calcular("sin(30)"), 0.5)
        self.assertAlmostEqual(calcular("sin(pi/6)", graus=False), 0.5)
        self.assertAlmostEqual(calcular("asin(0.5)"), 30)
        self.assertAlmostEqual(calcular("asin(0.5)", graus=False), math.pi / 6)

    def test_virgula_decimal(self):
        self.assertEqual(calcular("1,5 + 2"), 3.5)

    def test_trata_divisao_por_zero(self):
        with self.assertRaisesRegex(ValueError, "dividir por zero"):
            calcular("2/0")

    def test_rejeita_sintaxe_e_funcoes_nao_permitidas(self):
        for expressao in ("", "2 +", "unknown(2)", "__import__('os')", "2 // 1"):
            with self.subTest(expressao=expressao):
                with self.assertRaises(ValueError):
                    calcular(expressao)

    def test_trata_dominio_e_resultados_nao_reais(self):
        for expressao in ("sqrt(-1)", "ln(0)", "(-1)^0.5"):
            with self.subTest(expressao=expressao):
                with self.assertRaisesRegex(ValueError, "domínio"):
                    calcular(expressao)


if __name__ == "__main__":
    unittest.main()
