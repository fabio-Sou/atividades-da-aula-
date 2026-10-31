"""Operações seguras para a calculadora científica."""

import ast
import math
import operator
import re
from collections.abc import Callable


_OPERADORES: dict[type[ast.operator], Callable[[float, float], float]] = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Pow: math.pow,
}
_LIMITE_EXPRESSAO = 200
_LIMITE_NOS = 100
_LIMITE_EXPOENTE = 10_000


def _funcoes(graus: bool) -> dict[str, Callable[[float], float]]:
    converter_angulo = math.radians if graus else float
    converter_resultado = math.degrees if graus else float
    return {
        "sqrt": math.sqrt,
        "sin": lambda valor: math.sin(converter_angulo(valor)),
        "cos": lambda valor: math.cos(converter_angulo(valor)),
        "tan": lambda valor: math.tan(converter_angulo(valor)),
        "asin": lambda valor: converter_resultado(math.asin(valor)),
        "acos": lambda valor: converter_resultado(math.acos(valor)),
        "atan": lambda valor: converter_resultado(math.atan(valor)),
        "ln": math.log,
        "log": math.log10,
        "abs": abs,
    }


def _validar_numero(valor: float) -> float:
    if isinstance(valor, complex) or not math.isfinite(valor):
        raise ValueError("O resultado não é um número real finito.")
    return float(valor)


def _avaliar_no(no: ast.AST, funcoes: dict[str, object], profundidade: int = 0) -> float:
    if profundidade > 20:
        raise ValueError("A expressão está aninhada demais.")

    if isinstance(no, ast.Constant) and isinstance(no.value, (int, float)):
        return _validar_numero(no.value)

    if isinstance(no, ast.Name):
        constantes = {"pi": math.pi, "e": math.e}
        if no.id in constantes:
            return constantes[no.id]
        raise ValueError(f"Constante desconhecida: {no.id}.")

    if isinstance(no, ast.UnaryOp) and isinstance(no.op, (ast.UAdd, ast.USub)):
        valor = _avaliar_no(no.operand, funcoes, profundidade + 1)
        resultado = valor if isinstance(no.op, ast.UAdd) else -valor
        return _validar_numero(resultado)

    if isinstance(no, ast.BinOp) and type(no.op) in _OPERADORES:
        esquerda = _avaliar_no(no.left, funcoes, profundidade + 1)
        direita = _avaliar_no(no.right, funcoes, profundidade + 1)
        if isinstance(no.op, ast.Div) and direita == 0:
            raise ValueError("Não é possível dividir por zero.")
        if isinstance(no.op, ast.Pow) and abs(direita) > _LIMITE_EXPOENTE:
            raise ValueError("O expoente está fora do limite permitido.")
        try:
            resultado = _OPERADORES[type(no.op)](esquerda, direita)
        except ValueError as erro:
            raise ValueError("A operação está fora do domínio dos números reais.") from erro
        except OverflowError as erro:
            raise ValueError("O resultado é grande demais para calcular.") from erro
        return _validar_numero(resultado)

    if isinstance(no, ast.Call) and isinstance(no.func, ast.Name):
        if no.keywords or len(no.args) != 1:
            raise ValueError("Cada função deve receber exatamente um argumento.")
        funcao = funcoes.get(no.func.id)
        if funcao is None:
            raise ValueError(f"Função desconhecida: {no.func.id}.")
        argumento = _avaliar_no(no.args[0], funcoes, profundidade + 1)
        try:
            resultado = funcao(argumento)
        except ValueError as erro:
            raise ValueError(
                f"O argumento de {no.func.id} está fora do domínio real."
            ) from erro
        except OverflowError as erro:
            raise ValueError("O resultado é grande demais para calcular.") from erro
        return _validar_numero(resultado)

    raise ValueError("Expressão inválida. Use apenas números e operações aceitas.")


def calcular(expressao: str, graus: bool = True) -> float:
    """Avalia uma expressão matemática usando somente operações permitidas."""
    if not expressao.strip():
        raise ValueError("Digite uma expressão.")
    if len(expressao) > _LIMITE_EXPRESSAO:
        raise ValueError("A expressão é longa demais.")

    texto = expressao.strip().lower().replace("^", "**")
    texto = re.sub(r"(?<=\d),(?=\d)", ".", texto)
    try:
        arvore = ast.parse(texto, mode="eval")
    except SyntaxError as erro:
        raise ValueError("A expressão não está escrita corretamente.") from erro
    if sum(1 for _ in ast.walk(arvore)) > _LIMITE_NOS:
        raise ValueError("A expressão tem operações demais.")
    return _avaliar_no(arvore.body, _funcoes(graus))
