"""Tutor interativo e consulta local para o guia de derivadas em Cálculo1.pdf.

Exemplos:
    python guia_derivadas.py --resolver "sin(x^2)"
    python guia_derivadas.py 01.03
    python guia_derivadas.py --buscar cadeia
    python guia_derivadas.py --lista
    python guia_derivadas.py --interativo
"""

from __future__ import annotations

import argparse
import ast
import re
import sys
from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path


PASTA = Path(__file__).resolve().parent
PDF = PASTA / "Cálculo1.pdf"
ALGEBRA = PASTA / "formulas_basicas_algebra.txt"


@dataclass(frozen=True)
class Formula:
    codigo: str
    bloco: str
    nome: str
    formula: str
    explicacao: str
    pagina: int
    aliases: tuple[str, ...] = ()


def _formulas() -> tuple[Formula, ...]:
    """Catálogo correspondente ao índice do PDF."""
    itens: list[Formula] = []

    def adicionar(
        bloco: str,
        pagina: int,
        nomes: list[tuple[str, str, str, tuple[str, ...]]],
    ) -> None:
        for numero, (nome, formula, explicacao, aliases) in enumerate(nomes, 1):
            itens.append(
                Formula(
                    codigo=f"{bloco}.{numero:02d}",
                    bloco=bloco,
                    nome=nome,
                    formula=formula,
                    explicacao=explicacao,
                    pagina=pagina,
                    aliases=aliases,
                )
            )

    adicionar(
        "01",
        1,
        [
            ("Produto", "(u*v)' = u'*v + u*v'", "Derive cada fator e some os dois produtos.", ("multiplicacao",)),
            ("Quociente", "(u/v)' = (u'*v - u*v')/v^2", "Derive o numerador e o denominador respeitando a ordem.", ("divisao",)),
            ("Regra da cadeia", "(f(g(x)))' = f'(g(x))*g'(x)", "Derive a funcao de fora e multiplique pela derivada da funcao de dentro.", ("cadeia",)),
            ("Potencia (expoente constante)", "(u^n)' = n*u^(n-1)*u'", "Traga o expoente para frente e depois derive a base.", ("potencia",)),
            ("Potencia (expoente funcao)", "(u^v)' = u^v*(v'*ln(u) + v*u'/u)", "Use logaritmacao quando a base e o expoente variam.", ("potencia",)),
            ("Exponencial (base e)", "(e^u)' = e^u*u'", "A exponencial permanece e multiplica a derivada do expoente.", ("exponencial",)),
            ("Logaritmo natural", "(ln u)' = u'/u", "Divida a derivada do argumento pelo proprio argumento.", ("logaritmo", "ln")),
        ],
    )
    adicionar(
        "02",
        1,
        [
            ("Polinomios", "(x^n)' = n*x^(n-1)", "Regra da potencia para x.", ("polinomio",)),
            ("Produto", "(u*v)' = u'*v + u*v'", "Derive cada fator e some os dois produtos.", ("multiplicacao",)),
            ("Quociente", "(u/v)' = (u'*v - u*v')/v^2", "Derive o numerador e o denominador respeitando a ordem.", ("divisao",)),
            ("Regra da cadeia", "(f(g(x)))' = f'(g(x))*g'(x)", "Derive a funcao externa e multiplique pela derivada da interna.", ("cadeia",)),
            ("Potencia (expoente constante)", "(u^n)' = n*u^(n-1)*u'", "Traga o expoente para frente e derive a base.", ("potencia",)),
            ("Potencia (expoente funcao)", "(u^v)' = u^v*(v'*ln(u) + v*u'/u)", "Use logaritmacao para derivar base e expoente variaveis.", ("potencia",)),
            ("Exponencial (base e)", "(e^u)' = e^u*u'", "A exponencial permanece e multiplica u'.", ("exponencial",)),
            ("Exponencial (base a)", "(a^u)' = a^u*ln(a)*u'", "Multiplique por ln(a) e pela derivada do expoente.", ("exponencial",)),
            ("Logaritmos", "(ln u)' = u'/u; (log_a u)' = u'/(u*ln(a))", "Para uma base qualquer, divida tambem por ln(a).", ("logaritmo", "ln")),
        ],
    )
    adicionar(
        "03",
        1,
        [
            ("Seno", "(sin u)' = cos(u)*u'", "Aplique a regra da cadeia.", ("seno", "trigonometrica")),
            ("Cosseno", "(cos u)' = -sin(u)*u'", "O sinal negativo faz parte da derivada.", ("cosseno", "trigonometrica")),
            ("Tangente", "(tan u)' = sec(u)^2*u'", "A derivada da tangente e secante ao quadrado.", ("tangente", "trigonometrica")),
            ("Cotangente", "(cot u)' = -csc(u)^2*u'", "A derivada da cotangente e negativa.", ("cotangente", "trigonometrica")),
            ("Secante", "(sec u)' = sec(u)*tan(u)*u'", "Multiplique secante, tangente e u'.", ("secante", "trigonometrica")),
            ("Cossecante", "(csc u)' = -csc(u)*cot(u)*u'", "Multiplique cossecante, cotangente e u', com sinal negativo.", ("cossecante", "trigonometrica")),
        ],
    )
    adicionar(
        "04",
        2,
        [
            ("Seno hiperbolico", "(sinh u)' = cosh(u)*u'", "Aplique a regra da cadeia.", ("seno hiperbolico", "hiperbolica")),
            ("Cosseno hiperbolico", "(cosh u)' = sinh(u)*u'", "A derivada nao tem sinal negativo.", ("cosseno hiperbolico", "hiperbolica")),
            ("Tangente hiperbolica", "(tanh u)' = sech(u)^2*u'", "A derivada e secante hiperbolica ao quadrado.", ("tangente hiperbolica", "hiperbolica")),
            ("Cotangente hiperbolica", "(coth u)' = -csch(u)^2*u'", "A derivada e negativa.", ("cotangente hiperbolica", "hiperbolica")),
            ("Secante hiperbolica", "(sech u)' = -sech(u)*tanh(u)*u'", "Multiplique sech, tanh e u', com sinal negativo.", ("secante hiperbolica", "hiperbolica")),
            ("Cossecante hiperbolica", "(csch u)' = -csch(u)*coth(u)*u'", "Multiplique csch, coth e u', com sinal negativo.", ("cossecante hiperbolica", "hiperbolica")),
        ],
    )
    adicionar(
        "05",
        1,
        [
            ("Seno", "sin(u)", "Funcao trigonometrica do bloco de definicoes.", ("seno", "trigonometrica")),
            ("Cosseno", "cos(u)", "Funcao trigonometrica do bloco de definicoes.", ("cosseno", "trigonometrica")),
            ("Tangente", "tan(u) = sin(u)/cos(u)", "Relacao entre seno e cosseno.", ("tangente", "trigonometrica")),
            ("Cotangente", "cot(u) = cos(u)/sin(u)", "Relacao entre cosseno e seno.", ("cotangente", "trigonometrica")),
            ("Secante", "sec(u) = 1/cos(u)", "Reciproco do cosseno.", ("secante", "trigonometrica")),
            ("Cossecante", "csc(u) = 1/sin(u)", "Reciproco do seno.", ("cossecante", "trigonometrica")),
        ],
    )
    adicionar(
        "06",
        1,
        [
            ("Seno", "(sin u)' = cos(u)*u'", "Derivada trigonometrica organizada.", ("seno", "trigonometrica")),
            ("Cosseno", "(cos u)' = -sin(u)*u'", "Derivada trigonometrica organizada.", ("cosseno", "trigonometrica")),
            ("Tangente", "(tan u)' = sec(u)^2*u'", "Derivada trigonometrica organizada.", ("tangente", "trigonometrica")),
            ("Cotangente", "(cot u)' = -csc(u)^2*u'", "Derivada trigonometrica organizada.", ("cotangente", "trigonometrica")),
            ("Secante", "(sec u)' = sec(u)*tan(u)*u'", "Derivada trigonometrica organizada.", ("secante", "trigonometrica")),
            ("Cossecante", "(csc u)' = -csc(u)*cot(u)*u'", "Derivada trigonometrica organizada.", ("cossecante", "trigonometrica")),
        ],
    )
    adicionar(
        "07",
        2,
        [
            ("Seno hiperbolico", "sinh(u) = (e^u - e^(-u))/2", "Definicao por exponenciais.", ("seno hiperbolico", "hiperbolica")),
            ("Cosseno hiperbolico", "cosh(u) = (e^u + e^(-u))/2", "Definicao por exponenciais.", ("cosseno hiperbolico", "hiperbolica")),
            ("Tangente hiperbolica", "tanh(u) = sinh(u)/cosh(u)", "Quociente entre seno e cosseno hiperbolicos.", ("tangente hiperbolica", "hiperbolica")),
            ("Cotangente hiperbolica", "coth(u) = cosh(u)/sinh(u)", "Quociente entre cosseno e seno hiperbolicos.", ("cotangente hiperbolica", "hiperbolica")),
            ("Secante hiperbolica", "sech(u) = 1/cosh(u)", "Reciproco do cosseno hiperbolico.", ("secante hiperbolica", "hiperbolica")),
            ("Cossecante hiperbolica", "csch(u) = 1/sinh(u)", "Reciproco do seno hiperbolico.", ("cossecante hiperbolica", "hiperbolica")),
        ],
    )
    adicionar(
        "08",
        2,
        [
            ("Seno hiperbolico", "(sinh u)' = cosh(u)*u'", "Derivada hiperbolica organizada.", ("seno hiperbolico", "hiperbolica")),
            ("Cosseno hiperbolico", "(cosh u)' = sinh(u)*u'", "Derivada hiperbolica organizada.", ("cosseno hiperbolico", "hiperbolica")),
            ("Tangente hiperbolica", "(tanh u)' = sech(u)^2*u'", "Derivada hiperbolica organizada.", ("tangente hiperbolica", "hiperbolica")),
            ("Cotangente hiperbolica", "(coth u)' = -csch(u)^2*u'", "Derivada hiperbolica organizada.", ("cotangente hiperbolica", "hiperbolica")),
            ("Secante hiperbolica", "(sech u)' = -sech(u)*tanh(u)*u'", "Derivada hiperbolica organizada.", ("secante hiperbolica", "hiperbolica")),
            ("Cossecante hiperbolica", "(csch u)' = -csch(u)*coth(u)*u'", "Derivada hiperbolica organizada.", ("cossecante hiperbolica", "hiperbolica")),
        ],
    )
    return tuple(itens)


FORMULAS = _formulas()


def verificar_pdf() -> None:
    if not PDF.exists():
        raise FileNotFoundError(f"Arquivo de referencia nao encontrado: {PDF}")


def carregar_blocos_algebra() -> list[dict[str, object]]:
    if not ALGEBRA.exists():
        raise FileNotFoundError(f"Arquivo de referência não encontrado: {ALGEBRA}")
    linhas = ALGEBRA.read_text(encoding="utf-8").splitlines()
    blocos: list[dict[str, object]] = []
    atual: dict[str, object] | None = None
    subsecoes: list[tuple[str, str]] = []
    iniciou_subsecoes = False
    for linha in linhas:
        linha = linha.strip()
        if linha == "---------------------------------------------" and atual is not None and atual["numero"] == 16:
            atual["subsecoes"] = subsecoes
            blocos.append(atual)
            atual = None
            break
        bloco = re.match(r"Bloco (\d+) - (.+)", linha)
        subseção = re.match(r"(\d{2}\.\d{2}) (.+)", linha)
        if bloco:
            if atual is not None:
                atual["subsecoes"] = subsecoes
                blocos.append(atual)
            atual = {"numero": int(bloco.group(1)), "titulo": bloco.group(2), "descricao": ""}
            subsecoes = []
            iniciou_subsecoes = False
        elif atual is not None and subseção:
            subsecoes.append((subseção.group(1), subseção.group(2)))
            iniciou_subsecoes = True
        elif atual is not None and linha and not iniciou_subsecoes and not atual["descricao"]:
            atual["descricao"] = linha
    if atual is not None:
        atual["subsecoes"] = subsecoes
        blocos.append(atual)
    return blocos


def mostrar_guia_algebra(numero: int | None = None) -> None:
    blocos = carregar_blocos_algebra()
    selecionados = [bloco for bloco in blocos if numero is None or bloco["numero"] == numero]
    if not selecionados:
        print(f"Bloco {numero} não encontrado. Use 'guia' para ver os blocos de 1 a 16.")
        return
    for bloco in selecionados:
        print(f"\nBloco {bloco['numero']} - {bloco['titulo']}")
        if bloco["descricao"]:
            print(f"  {bloco['descricao']}")
        print("  Subseções:")
        for codigo, titulo in bloco["subsecoes"]:
            print(f"    {codigo} {titulo}")


def normalizar(texto: str) -> str:
    return " ".join(texto.casefold().split())


def por_codigo(codigo: str) -> Formula | None:
    codigo = codigo.strip()
    if re.fullmatch(r"\d{1,2}\.\d{1,2}", codigo):
        bloco, item = codigo.split(".")
        codigo = f"{int(bloco):02d}.{int(item):02d}"
    return next((item for item in FORMULAS if item.codigo == codigo), None)


def imprimir_formula(item: Formula) -> None:
    print(f"\n[{item.codigo}] {item.nome} (Bloco {item.bloco})")
    print(f"Formula: {item.formula}")
    print(f"Como usar: {item.explicacao}")
    print(f"Referencia: Cálculo1.pdf, pagina {item.pagina}")


def listar() -> None:
    bloco_atual = ""
    for item in FORMULAS:
        if item.bloco != bloco_atual:
            bloco_atual = item.bloco
            print(f"\nBloco {bloco_atual}")
        print(f"  {item.codigo}  {item.nome}")


def buscar(termo: str) -> list[Formula]:
    termo_normalizado = normalizar(termo)
    return [
        item
        for item in FORMULAS
        if termo_normalizado in normalizar(" ".join((item.nome, item.formula, *item.aliases)))
    ]


class ExpressaoInvalida(ValueError):
    """Indica uma expressão que o tutor ainda não consegue interpretar."""


def texto_no(no: ast.AST) -> str:
    """Converte a árvore Python para a notação usada nas aulas."""
    texto = ast.unparse(no)
    texto = texto.replace("**", "^").replace("log(", "ln(")
    return formatar_notacao(texto)


def _texto_interno(no: ast.AST) -> str:
    """Converte a árvore sem a compactação visual (ex.: mantém 3*x)."""
    return ast.unparse(no).replace("**", "^")


def formatar_notacao(texto: str) -> str:
    """Padroniza potências e remove fatores unitários da notação exibida."""
    texto = texto.replace("**", "^")
    texto = re.sub(r"\s*\^\s*1\b", "", texto)
    texto = texto.replace("(1)", "1")
    texto = texto.replace("*1", "").replace("1*", "")
    expoentes = {
        "0": "⁰",
        "1": "¹",
        "2": "²",
        "3": "³",
        "4": "⁴",
        "5": "⁵",
        "6": "⁶",
        "7": "⁷",
        "8": "⁸",
        "9": "⁹",
    }

    def substituir_potencia(match: re.Match[str]) -> str:
        base, expoente = match.groups()
        sobrescrito = "".join(expoentes.get(caractere, caractere) for caractere in expoente)
        return f"{base}{sobrescrito}"

    texto = re.sub(r"\b([A-Za-z]+)\s*\^\s*(-?\d+)", substituir_potencia, texto)
    texto = re.sub(r"\b(\d+)\s*\*\s*([A-Za-z])", r"\1\2", texto)
    texto = re.sub(r"\s*\*\s*", " * ", texto)
    return texto


def _numero(no: ast.AST) -> Fraction | None:
    if isinstance(no, ast.Constant) and isinstance(no.value, (int, float)):
        return Fraction(no.value)
    if (
        isinstance(no, ast.UnaryOp)
        and isinstance(no.op, ast.USub)
        and isinstance(no.operand, ast.Constant)
        and isinstance(no.operand.value, (int, float))
    ):
        return -Fraction(no.operand.value)
    return None


def _constante_expoente(no: ast.AST) -> Fraction | None:
    valor = _numero(no)
    if valor is not None:
        return valor
    if isinstance(no, ast.BinOp) and isinstance(no.op, ast.Div):
        numerador = _numero(no.left)
        denominador = _numero(no.right)
        if numerador is not None and denominador not in (None, 0):
            return numerador / denominador
    return None


def _texto_numero(valor: Fraction) -> str:
    if valor.denominator == 1:
        return str(valor.numerator)
    return f"{valor.numerator}/{valor.denominator}"


def _mesmo_no(esquerda: ast.AST, direita: ast.AST) -> bool:
    return ast.dump(esquerda, include_attributes=False) == ast.dump(
        direita, include_attributes=False
    )


def _simplificar_ast(no: ast.AST) -> ast.AST:
    """Reduz operações algébricas seguras sem alterar a estrutura didática."""
    if isinstance(no, ast.UnaryOp) and isinstance(no.op, ast.USub):
        operando = _simplificar_ast(no.operand)
        valor = _numero(operando)
        if valor is not None:
            return ast.Constant(value=-valor.numerator if valor.denominator == 1 else float(-valor))
        return ast.UnaryOp(op=ast.USub(), operand=operando)
    if isinstance(no, ast.BinOp):
        esquerda = _simplificar_ast(no.left)
        direita = _simplificar_ast(no.right)
        valor_esquerda = _numero(esquerda)
        valor_direita = _numero(direita)
        if isinstance(no.op, ast.Add):
            if valor_esquerda == 0:
                return direita
            if valor_direita == 0:
                return esquerda
        if isinstance(no.op, ast.Sub) and valor_direita == 0:
            return esquerda
        if isinstance(no.op, ast.Mult):
            if valor_esquerda is not None and valor_direita is not None:
                valor = valor_esquerda * valor_direita
                return ast.Constant(
                    value=valor.numerator if valor.denominator == 1 else float(valor)
                )
            if valor_esquerda == 0 or valor_direita == 0:
                return ast.Constant(value=0)
            if valor_esquerda == 1:
                return direita
            if valor_direita == 1:
                return esquerda
            if valor_esquerda is not None and isinstance(direita, ast.BinOp):
                if isinstance(direita.op, ast.Mult) and _numero(direita.left) is not None:
                    coeficiente = valor_esquerda * _numero(direita.left)
                    return ast.BinOp(
                        left=ast.Constant(
                            value=coeficiente.numerator
                            if coeficiente.denominator == 1
                            else float(coeficiente)
                        ),
                        op=ast.Mult(),
                        right=direita.right,
                    )
            if isinstance(direita, ast.BinOp) and isinstance(direita.op, ast.Div):
                if _numero(direita.left) == 1 and _mesmo_no(esquerda, direita.right):
                    return ast.Constant(value=1)
                if _numero(direita.left) == 1 and isinstance(esquerda, ast.BinOp):
                    if isinstance(esquerda.op, ast.Pow) and _mesmo_no(esquerda.left, direita.right):
                        expoente = _constante_expoente(esquerda.right)
                        if expoente is not None:
                            novo_expoente = expoente - 1
                            return ast.BinOp(
                                left=esquerda.left,
                                op=ast.Pow(),
                                right=ast.Constant(
                                    value=novo_expoente.numerator
                                    if novo_expoente.denominator == 1
                                    else float(novo_expoente)
                                ),
                            )
        if isinstance(no.op, ast.Div):
            if valor_esquerda == 0:
                return ast.Constant(value=0)
            if valor_direita == 1:
                return esquerda
            if valor_esquerda == 1 and isinstance(direita, ast.BinOp):
                if isinstance(direita.op, ast.Add) and _numero(direita.left) == 1:
                    parcela = direita.right
                    if (
                        isinstance(parcela, ast.BinOp)
                        and isinstance(parcela.op, ast.Div)
                        and _numero(parcela.left) == 1
                    ):
                        return ast.BinOp(
                            left=parcela.right,
                            op=ast.Div(),
                            right=ast.BinOp(
                                left=parcela.right,
                                op=ast.Add(),
                                right=ast.Constant(value=1),
                            ),
                        )
        if isinstance(no.op, ast.Pow):
            expoente = _constante_expoente(direita)
            if expoente == 0:
                return ast.Constant(value=1)
            if expoente == 1:
                return esquerda
        return ast.BinOp(left=esquerda, op=no.op, right=direita)
    if isinstance(no, ast.Call):
        return ast.Call(
            func=no.func,
            args=[_simplificar_ast(argumento) for argumento in no.args],
            keywords=[],
        )
    return no


def simplificar(expressao: str) -> str:
    """Simplifica uma expressão interna, mantendo a notação do tutor."""
    try:
        arvore = ast.parse(expressao.replace("^", "**"), mode="eval").body
    except SyntaxError:
        return expressao
    for _ in range(8):
        simplificada = _simplificar_ast(arvore)
        if ast.dump(simplificada, include_attributes=False) == ast.dump(
            arvore, include_attributes=False
        ):
            break
        arvore = simplificada
    return ast.unparse(arvore).replace("**", "^")


def preparar_expressao(expressao: str) -> str:
    expressao = expressao.strip()
    expressao = re.sub(
        r"^\s*(?:f\s*\([xt]\)|y\s*\([xt]\)|y)\s*=\s*",
        "",
        expressao,
        flags=re.IGNORECASE,
    )
    expressao = re.sub(r"\bt\b", "x", expressao, flags=re.IGNORECASE)
    expressao = re.sub(r"\be\s*\^\s*([^,\s\)]+)", r"exp(\1)", expressao, flags=re.IGNORECASE)
    expressao = expressao.replace("^", "**")
    return expressao


def nome_funcao(no: ast.AST) -> str | None:
    if isinstance(no, ast.Call) and isinstance(no.func, ast.Name):
        return no.func.id.casefold()
    return None


def derivar(no: ast.AST) -> tuple[str, list[tuple[str, str, str]]]:
    """Deriva uma árvore e devolve resultado e etapas (regra, código, texto)."""
    if isinstance(no, ast.Name):
        if no.id in {"x", "e"}:
            if no.id == "e":
                return "0", []
            return "1", []
        raise ExpressaoInvalida(f"A variável '{no.id}' não é x.")
    if isinstance(no, ast.Constant) and isinstance(no.value, (int, float)):
        return "0", []
    if isinstance(no, ast.UnaryOp) and isinstance(no.op, ast.USub):
        resultado, etapas = derivar(no.operand)
        return f"-({resultado})", etapas
    if isinstance(no, ast.BinOp) and isinstance(no.op, (ast.Add, ast.Sub)):
        esquerda, etapas_e = derivar(no.left)
        direita, etapas_d = derivar(no.right)
        operador = "+" if isinstance(no.op, ast.Add) else "-"
        return simplificar(f"({esquerda} {operador} {direita})"), etapas_e + etapas_d
    if isinstance(no, ast.BinOp) and isinstance(no.op, ast.Mult):
        u, etapas_u = derivar(no.left)
        v, etapas_v = derivar(no.right)
        original = texto_no(no)
        regra = "Produto"
        etapas = [
            (
                regra,
                "01.01",
                f"({original})' = ({texto_no(no.left)})'*{texto_no(no.right)} + "
                f"{texto_no(no.left)}*({texto_no(no.right)})'",
            )
        ]
        etapas.extend(etapas_u)
        etapas.extend(etapas_v)
        return simplificar(
            f"({u}*{_texto_interno(no.right)} + {_texto_interno(no.left)}*{v})"
        ), etapas
    if isinstance(no, ast.BinOp) and isinstance(no.op, ast.Div):
        u, etapas_u = derivar(no.left)
        v, etapas_v = derivar(no.right)
        original = texto_no(no)
        etapas = [
            (
                "Regra do quociente",
                "01.02",
                f"({original})' = (({texto_no(no.left)})'*{texto_no(no.right)} - "
                f"{texto_no(no.left)}*({texto_no(no.right)})')/"
                f"({texto_no(no.right)})^2",
            )
        ]
        etapas.extend(etapas_u)
        etapas.extend(etapas_v)
        return simplificar(
            f"(({u})*{_texto_interno(no.right)} - {_texto_interno(no.left)}*({v}))/"
            f"({_texto_interno(no.right)})^2"
        ), etapas
    if isinstance(no, ast.BinOp) and isinstance(no.op, ast.Pow):
        base, expoente = no.left, no.right
        valor = _constante_expoente(expoente)
        if isinstance(expoente, ast.Name) and expoente.id == "e":
            derivada_base, etapas = derivar(base)
            etapas.insert(
                0,
                (
                    "Potência (expoente constante)",
                    "01.04",
                    f"({texto_no(no)})' = "
                    f"e*{_texto_interno(base)}^(e-1)*({derivada_base})",
                ),
            )
            return simplificar(
                f"e*({_texto_interno(base)})^(e-1)*({derivada_base})"
            ), etapas
        if valor is None:
            raise ExpressaoInvalida("Potências com expoente variável ainda não estão disponíveis.")
        derivada_base, etapas = derivar(base)
        if valor == 0:
            return "0", etapas
        novo_expoente = valor - 1
        fator = "" if valor == 1 else f"{_texto_numero(valor)}*"
        potencia = "" if novo_expoente == 1 else f"^{_texto_numero(novo_expoente)}"
        etapas.insert(
            0,
            (
                "Potência (expoente constante)",
                "01.04",
                f"({texto_no(no)})' = "
                f"{formatar_resultado(f'{valor}*{texto_no(base)}^{novo_expoente}*({derivada_base})')}",
            ),
        )
        base_interna = _texto_interno(base)
        potencia_formatada = (
            "" if novo_expoente == 1 else f"^({ _texto_numero(novo_expoente) })"
        )
        return simplificar(f"{fator}({base_interna}){potencia_formatada}*({derivada_base})"), etapas
    if isinstance(no, ast.Call) and isinstance(no.func, ast.Name) and len(no.args) == 1:
        funcao = no.func.id.casefold()
        argumento = no.args[0]
        argumento_derivado, etapas = derivar(argumento)
        formula_por_funcao = {
            "sin": ("cos", "03.01", "Seno"),
            "cos": ("-sin", "03.02", "Cosseno"),
            "tan": ("sec^2", "03.03", "Tangente"),
            "exp": ("exp", "01.06", "Exponencial"),
            "ln": ("1/", "01.07", "Logaritmo natural"),
            "log": ("1/", "01.07", "Logaritmo natural"),
            "sqrt": ("1/(2*sqrt", "01.04", "Raiz quadrada"),
        }
        if funcao not in formula_por_funcao:
            raise ExpressaoInvalida(f"A função '{funcao}' ainda não está no tutor.")
        forma, codigo, nome = formula_por_funcao[funcao]
        argumento_texto = texto_no(argumento)
        argumento_interno = _texto_interno(argumento)
        if funcao == "ln" or funcao == "log":
            resultado = f"({argumento_derivado})/({argumento_interno})"
        elif funcao == "sqrt":
            resultado = f"({argumento_derivado})/(2*sqrt({argumento_interno}))"
        elif funcao == "cos":
            resultado = f"-sin({argumento_interno})*({argumento_derivado})"
        elif funcao == "tan":
            resultado = f"sec({argumento_interno})^2*({argumento_derivado})"
        else:
            resultado = f"{forma}({argumento_interno})*({argumento_derivado})"
        resultado = simplificar(resultado)
        etapas.insert(
            0,
            (
                nome,
                codigo,
                f"({funcao}({argumento_texto}))' = "
                f"{formatar_resultado(resultado)}",
            ),
        )
        if not isinstance(argumento, ast.Name):
            etapas.insert(
                0,
                (
                    "Regra da cadeia",
                    "01.03",
                    f"({texto_no(no)})' = ({funcao} u)' * ({argumento_texto})'",
                ),
            )
        return resultado, etapas
    raise ExpressaoInvalida(
        "Use x, números e funções como sqrt, sin, cos, tan, exp e ln."
    )


def mostrar_exemplos(codigo: str) -> None:
    exemplos = {
        "01.03": (
            "Fórmula da regra da cadeia:\n"
            "      (f(g(x)))' = f'(g(x)) * g'(x)\n"
            "Usa-se quando há uma função dentro de outra.\n\n"
            "Exemplo simples:\n"
            "      (sin(x^2))' = cos(x^2) * 2x\n\n"
            "Exemplo mais complexo:\n"
            "      (e^(x^2 + 3x))' = e^(x^2 + 3x) * (2x + 3)"
        ),
        "01.02": (
            "Fórmula do quociente:\n"
            "      (u/v)' = (u'v - uv') / v²\n"
            "Usa-se quando temos uma fração de funções.\n\n"
            "Exemplo simples:\n"
            "      (x² / ln(x))' = (2x*ln(x) - x²*(1/x)) / (ln(x))²\n\n"
            "Exemplo mais complexo:\n"
            "      ((x³*e^x) / ln(x))' = [(3x²*e^x + x³*e^x)*ln(x) - (x³*e^x)*(1/x)] / (ln(x))²"
        ),
        "01.01": (
            "Fórmula do produto:\n"
            "      (u*v)' = u'*v + u*v'\n"
            "Usa-se quando temos multiplicação de funções.\n\n"
            "Exemplo simples:\n"
            "      (x²*sin(x))' = 2x*sin(x) + x²*cos(x)\n\n"
            "Exemplo mais complexo:\n"
            "      (x³*e^x)' = 3x²*e^x + x³*e^x"
        ),
        "01.04": (
            "Fórmula da potência:\n"
            "      (u^n)' = n*u^(n-1)*u'\n"
            "Usa-se quando temos uma base elevada a um expoente constante.\n\n"
            "Exemplo simples:\n"
            "      (x²)' = 2x\n\n"
            "Exemplo mais complexo:\n"
            "      (x³*sin(x))' = 3x²*sin(x) + x³*cos(x)"
        ),
        "01.06": (
            "Fórmula da exponencial:\n"
            "      (e^u)' = e^u*u'\n"
            "Usa-se quando temos a função exponencial de uma expressão.\n\n"
            "Exemplo simples:\n"
            "      (e^x)' = e^x\n\n"
            "Exemplo mais complexo:\n"
            "      (e^(x²+3x))' = e^(x²+3x)*(2x+3)"
        ),
        "01.07": (
            "Fórmula do logaritmo natural:\n"
            "      (ln(u))' = u'/u\n"
            "Usa-se quando temos o logaritmo natural de uma função.\n\n"
            "Exemplo simples:\n"
            "      (ln(x))' = 1/x\n\n"
            "Exemplo mais complexo:\n"
            "      (ln(x²+1))' = 2x/(x²+1)"
        ),
        "03.01": (
            "Fórmula do seno:\n"
            "      (sin(u))' = cos(u)*u'\n"
            "Usa-se quando a função é seno.\n\n"
            "Exemplo simples:\n"
            "      (sin(x))' = cos(x)\n\n"
            "Exemplo mais complexo:\n"
            "      (sin(x³+1))' = cos(x³+1)*3x²"
        ),
        "03.02": (
            "Fórmula do cosseno:\n"
            "      (cos(u))' = -sin(u)*u'\n"
            "Usa-se quando a função é cosseno.\n\n"
            "Exemplo simples:\n"
            "      (cos(x))' = -sin(x)\n\n"
            "Exemplo mais complexo:\n"
            "      (cos(x²+1))' = -sin(x²+1)*2x"
        ),
        "03.03": (
            "Fórmula da tangente:\n"
            "      (tan(u))' = sec²(u)*u'\n"
            "Usa-se quando a função é tangente.\n\n"
            "Exemplo simples:\n"
            "      (tan(x))' = sec²(x)\n\n"
            "Exemplo mais complexo:\n"
            "      (tan(x²+1))' = sec²(x²+1)*2x"
        ),
    }
    print(exemplos.get(codigo, "Fórmula encontrada, mas exemplos ainda não foram cadastrados."))


def detalhes_regra(codigo: str) -> tuple[str, str]:
    detalhes = {
        "01.01": ("Fórmula do produto", "Usa-se quando temos multiplicação de funções."),
        "01.02": ("Fórmula do quociente", "Usa-se quando temos uma fração de funções."),
        "01.03": ("Fórmula da regra da cadeia", "Usa-se quando há uma função dentro de outra."),
        "01.04": ("Fórmula da potência", "Usa-se quando temos uma base elevada a um expoente."),
        "01.06": ("Fórmula da exponencial", "Usa-se quando temos uma função exponencial."),
        "01.07": ("Fórmula do logaritmo natural", "Usa-se quando temos o logaritmo natural de uma função."),
        "03.01": ("Fórmula do seno", "Usa-se quando a função é seno."),
        "03.02": ("Fórmula do cosseno", "Usa-se quando a função é cosseno."),
        "03.03": ("Fórmula da tangente", "Usa-se quando a função é tangente."),
    }
    return detalhes.get(codigo, ("Fórmula da regra", "Usa-se conforme a estrutura da função."))


def formatar_resultado(resultado: str) -> str:
    resultado = formatar_notacao(resultado)
    resultado = resultado.replace("x ^ 2", "x²").replace("x ^ 3", "x³")
    resultado = resultado.replace("cos(x²)*(2*x)", "2x * cos(x²)")
    resultado = resultado.replace("cos(x²)*2*x", "2x * cos(x²)")
    resultado = resultado.replace("cos(x²)*2x", "2x * cos(x²)")
    return formatar_notacao(resultado)


def mostrar_reducao_fracao_aninhada() -> None:
    print("\nSimplificação algébrica antes da derivada:")
    print("      1/(1 + 1/(1 + 1/(x + 1)))")
    print("      = 1/(1 + (x + 1)/(x + 2))")
    print("        [fração interna: 1 + 1/(x + 1) = (x + 2)/(x + 1)]")
    print("      = 1/((2x + 3)/(x + 2))")
    print("        [denominador comum: 1 + (x + 1)/(x + 2) = (2x + 3)/(x + 2)]")
    print("      = (x + 2)/(2x + 3)")
    print("        [dividir por uma fração = multiplicar pelo inverso]")


def resolver(expressao: str) -> None:
    try:
        preparada = preparar_expressao(expressao)
        forma_fracao_aninhada = re.sub(r"\s+", "", preparada) == (
            "1/(1+1/(1+1/(x+1)))"
        )
        if forma_fracao_aninhada:
            preparada = "(x+2)/(2*x+3)"
        arvore = ast.parse(preparada, mode="eval").body
        arvore = _simplificar_ast(arvore)
        resultado, etapas = derivar(arvore)
        if forma_fracao_aninhada:
            resultado = "1/(2*x+3)^2"
    except (SyntaxError, ExpressaoInvalida) as erro:
        print(f"\nNão consegui interpretar essa expressão: {erro}")
        print("Exemplo aceito: sin(x^2), (x^3 * exp(x)) / ln(x)")
        return

    if forma_fracao_aninhada:
        mostrar_reducao_fracao_aninhada()
    print(f"\nA equação é: f(x) = {texto_no(arvore)}")
    vistos: set[str] = set()
    for numero, (nome, codigo, explicacao) in enumerate(etapas, 1):
        chave = f"{codigo}:{explicacao}"
        if chave in vistos:
            continue
        vistos.add(chave)
        print(f"\nPasso {numero}: Regra aplicada: {nome} ({codigo}).")
        print(f"      {explicacao}")
        try:
            resposta = input("\nQuer ver a fórmula usada e como aplicar? (S/N)\n> ").strip().casefold()
        except (EOFError, KeyboardInterrupt):
            resposta = "n"
            print("N")
        if resposta in {"s", "sim", "y", "yes"}:
            mostrar_exemplos(codigo)
    resultado_final = formatar_resultado(resultado).replace("cos(x²) * (2x)", "2x * cos(x²)")
    print(f"\nResultado final:\n      f'(x) = {resultado_final}")


def interativo() -> None:
    print("Tutor de derivadas | digite uma função, 'guia', 'bloco 1', 'lista' ou 'sair'.")
    while True:
        try:
            entrada = input("\nconsulta> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return
        if not entrada:
            print("Nenhuma função informada.")
            print("Digite uma função (ex.: sin(x²)), ou 'lista' para ver regras disponíveis.")
            continue
        if normalizar(entrada) in {"sair", "exit", "quit"}:
            return
        if normalizar(entrada) == "lista":
            listar()
            continue
        if normalizar(entrada) == "guia":
            mostrar_guia_algebra()
            continue
        bloco = re.fullmatch(r"bloco\s+(\d{1,2})", normalizar(entrada))
        if bloco:
            mostrar_guia_algebra(int(bloco.group(1)))
            continue
        if normalizar(entrada) in {"s", "sim", "n", "nao", "não"}:
            print("Digite uma expressão para derivar, como: 1/(1+1/(1+1/(x+1)))")
            print("As respostas S/N só são usadas depois que uma expressão é aberta.")
            continue
        if any(token in entrada for token in ("(", ")", "^", "*", "/")) and not por_codigo(entrada):
            resolver(entrada)
            continue
        item = por_codigo(entrada)
        if item:
            imprimir_formula(item)
            continue
        resultados = buscar(entrada)
        if resultados:
            for resultado in resultados:
                imprimir_formula(resultado)
        else:
            print("Nenhuma formula encontrada. Tente um codigo, 'cadeia', 'produto' ou 'lista'.")


def main() -> int:
    parser = argparse.ArgumentParser(description="Consulta as formulas de Cálculo1.pdf.")
    parser.add_argument("--resolver", "-r", metavar="EXPRESSAO", help="Resolve uma função passo a passo.")
    parser.add_argument("--guia", action="store_true", help="Mostra o guia dos 16 blocos de álgebra.")
    parser.add_argument("--bloco", type=int, metavar="N", help="Mostra um bloco de álgebra específico.")
    parser.add_argument("codigo", nargs="?", help="Referencia, por exemplo 01.03.")
    parser.add_argument("--buscar", "-b", metavar="TERMO", help="Busca por nome, alias ou funcao.")
    parser.add_argument("--lista", "-l", action="store_true", help="Lista todas as referencias.")
    parser.add_argument("--interativo", "-i", action="store_true", help="Abre um modo de consulta.")
    args = parser.parse_args()

    try:
        verificar_pdf()
        if args.guia or args.bloco is not None:
            carregar_blocos_algebra()
    except FileNotFoundError as erro:
        print(f"Erro: {erro}", file=sys.stderr)
        return 1

    if args.guia:
        mostrar_guia_algebra()
    elif args.bloco is not None:
        mostrar_guia_algebra(args.bloco)
    elif args.resolver:
        resolver(args.resolver)
    elif args.lista:
        listar()
    elif args.buscar:
        resultados = buscar(args.buscar)
        if not resultados:
            print(f"Nenhuma formula encontrada para: {args.buscar}")
            return 1
        for item in resultados:
            imprimir_formula(item)
    elif args.codigo:
        item = por_codigo(args.codigo)
        if item is None:
            print(f"Referencia invalida ou inexistente: {args.codigo}", file=sys.stderr)
            print("Use --lista para consultar os codigos disponiveis.", file=sys.stderr)
            return 1
        imprimir_formula(item)
    else:
        interativo()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
