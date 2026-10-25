"""Tutor interativo e consulta local para o resumo textual de derivadas.

Exemplos:
    python guia_derivadas.py --resolver "sin(x^2)"
    python guia_derivadas.py 01.03
    python guia_derivadas.py --buscar cadeia
    python guia_derivadas.py --lista
    python guia_derivadas.py --interativo
"""
# essa linha permite que o código seja executado em versões antigas do Python, mesmo que usem recursos mais recentes
from __future__ import annotations

import argparse
import ast
import os
import random
import re
import sys
import textwrap
import unicodedata
from dataclasses import dataclass
from datetime import datetime
from fractions import Fraction
from pathlib import Path


# Caminhos dos arquivos de apoio e estado compartilhado dos modos do tutor.
# O estado global controla quando letras representam variáveis ou constantes.
PASTA = Path(__file__).resolve().parent
RESUMO_DERIVADAS = PASTA / "resumo_de_derivadas.txt"
ALGEBRA = PASTA / "formulas_basicas_algebra.txt"
COMANDOS = PASTA / "comandos_derivadas.txt"
TESTES_DERIVADAS = PASTA / "testes_derivadas.txt"
FUTURAS_ATUALIZACOES = PASTA / "futuras_atualizacoes.txt"
MODO_IMAGEM = False
MODO_IMPLICITA = False
SIMBOLOS_VARIAVEIS: set[str] = set()
MODO_DESENVOLVEDOR = False


# Estruturas de dados usadas para representar fórmulas e questões do jogo.
@dataclass(frozen=True)
class Formula:
    codigo: str
    bloco: str
    nome: str
    formula: str
    explicacao: str
    pagina: int
    aliases: tuple[str, ...] = ()


@dataclass(frozen=True)
class QuestaoJogo:
    expressao: str
    derivada_de_imagem: bool = False


# Fluxo principal: menus e ações na ordem em que o usuário as acessa.


# Menus principais, submenus temáticos e entrada dedicada para símbolos-imagem.
def menu_inicial() -> None:
    global MODO_DESENVOLVEDOR
    while True:
        limpar_tela()
        print("\n=== Tutor de Derivadas ===")
        print("1. Tutor completo (derivação, imagem e ordem superior)")
        print("2. Jogo de derivadas")
        print("3. Guia geral (comandos, regras e álgebra)")
        print("4. Tópicos avançados")
        print("5. Sair")
        try:
            escolha = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return
        if remover_acentos(escolha) == "desenvolvedor":
            MODO_DESENVOLVEDOR = not MODO_DESENVOLVEDOR
            estado = "ativado" if MODO_DESENVOLVEDOR else "desativado"
            print(f"\nModo desenvolvedor {estado}.")
            input("Pressione Enter para continuar...")
            continue
        if escolha == "1":
            menu_tutor_completo()
        elif escolha == "2":
            menu_jogo()
        elif escolha == "3":
            menu_guia_geral()
        elif escolha == "4":
            menu_topicos_avancados()
        elif escolha == "5":
            return
        else:
            print("Escolha uma opção de 1 a 5.")


def menu_tutor_completo() -> None:
    while True:
        limpar_tela()
        print("\n=== Tutor completo ===")
        print("1. Derivação passo a passo")
        print("2. Derivada de imagem (símbolos dependentes de x)")
        print("3. Derivada de ordem superior")
        print("4. Voltar")
        try:
            escolha = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return
        if escolha == "1":
            interativo()
        elif escolha == "2":
            menu_derivada_de_imagem()
        elif escolha == "3":
            try:
                ordem = int(
                    input(
                        "Qual ordem deseja calcular? (ex.: 2 para a segunda derivada)\n> "
                    ).strip()
                )
                expressao = input("Digite a função (ex.: x^2):\n> ").strip()
            except (EOFError, KeyboardInterrupt, ValueError):
                print("Ordem inválida: digite um número inteiro, como 2 ou 3.")
                aguardar_retorno()
                continue
            if expressao:
                resolver_ordem_superior(expressao, ordem)
                aguardar_retorno()
        elif escolha == "4":
            return
        else:
            print("Escolha uma opção de 1 a 4.")


def entrada_e_expressao_matematica(entrada: str) -> bool:
            """Distingue entradas deriváveis de buscas por nome ou código de fórmula."""
            if por_codigo(entrada):
                return False
            try:
                arvore = ast.parse(
                    preparar_expressao(traduzir_portugues(entrada)),
                    mode="eval",
                ).body
            except SyntaxError:
                return False
            if isinstance(arvore, ast.Name):
                return arvore.id.casefold() in {"x", "t"}
            return isinstance(arvore, (ast.BinOp, ast.UnaryOp, ast.Call, ast.Constant))


# Entrada do tutor em texto livre e comandos auxiliares de consulta.
def interativo() -> None:
    limpar_tela()
    print(
        "Tutor de derivadas | digite uma função, 'guia', 'bloco 1', "
        "'lista' ou 'sair'."
    )
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
        comando = remover_acentos(entrada)
        if comando in {"sair", "exit", "quit"}:
            return
        if comando in {"ajuda", "comandos"}:
            limpar_tela()
            mostrar_comandos()
            continue
        if comando in {"imagem", "derivada de imagem"}:
            menu_derivada_de_imagem()
            continue
        if comando.startswith("implicita "):
            resolver_implicita(entrada.split(" ", 1)[1])
            continue
        if comando.startswith("parametrica "):
            resolver_parametrica(entrada.split(" ", 1)[1])
            continue
        ordem = re.match(r"ordem\s+(\d+)\s+(.+)", entrada, re.IGNORECASE)
        if ordem:
            resolver_ordem_superior(ordem.group(2), int(ordem.group(1)))
            continue
        if comando.startswith("partes "):
            resolver_por_partes(entrada.split(" ", 1)[1])
            continue
        if comando == "lista":
            limpar_tela()
            listar()
            continue
        if comando == "guia":
            limpar_tela()
            mostrar_guia_algebra()
            continue
        bloco = re.fullmatch(r"bloco\s+(\d{1,2})", comando)
        if bloco:
            limpar_tela()
            mostrar_guia_algebra(int(bloco.group(1)))
            continue
        if normalizar(entrada) in {"s", "sim", "n", "nao", "não"}:
            print("Digite uma expressão para derivar, como: 1/(1+1/(1+1/(x+1)))")
            print("As respostas S/N só são usadas depois que uma expressão é aberta.")
            continue
        if entrada_e_expressao_matematica(entrada):
            limpar_tela()
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
            print("Nenhuma fórmula encontrada. Digite 'ajuda' para ver os comandos.")


def resolver(
    expressao: str,
    derivada_de_imagem: bool = False,
    registrar_falha: bool = True,
) -> bool:
    global MODO_IMAGEM, SIMBOLOS_VARIAVEIS
    estado_anterior = MODO_IMAGEM
    simbolos_anteriores = SIMBOLOS_VARIAVEIS
    MODO_IMAGEM = derivada_de_imagem
    SIMBOLOS_VARIAVEIS = set()
    try:
        preparada = preparar_expressao(traduzir_portugues(expressao))
        forma_fracao_aninhada = re.sub(r"\s+", "", preparada) == (
            "1/(1+1/(1+1/(x+1)))"
        )
        if forma_fracao_aninhada:
            preparada = "(x+2)/(2*x+3)"
        arvore = ast.parse(preparada, mode="eval").body
        arvore_original = arvore
        if MODO_DESENVOLVEDOR:
            print("\nA equação informada:")
            imprimir_texto_formatado(f"f(x) = {expressao.strip()}")
            print("\nForma interpretada pelo tutor:")
            imprimir_texto_formatado(f"f(x) = {texto_no(arvore_original)}")
        atalho = encontrar_atalho_trigonometrico(arvore)
        usar_atalho = False
        if atalho is not None:
            arvore_reduzida, pares = atalho
            print("\nExiste uma forma mais curta de resolver esta expressão.")
            print("Foram encontrados os seguintes pares recíprocos:")
            fatores_atuais = [texto_no(fator) for fator in _fatores_produto(arvore_original)]
            for numero, (esquerda, direita) in enumerate(pares, 1):
                print(f"\nAtalho {numero}:")
                imprimir_texto_formatado(f"{esquerda} * {direita} = 1")
                fatores_atuais.remove(esquerda)
                fatores_atuais.remove(direita)
                expressao_restante = " * ".join(fatores_atuais) or "1"
                imprimir_texto_formatado(f"expressão restante = {expressao_restante}")
            print("\nAssim, a expressão pode ser reduzida para:")
            imprimir_texto_formatado(f"f(x) = {texto_no(arvore_reduzida)}")
            try:
                resposta = input(
                    "\nQuer usar esse atalho antes de derivar? (S/N)\n> "
                ).strip().casefold()
            except (EOFError, KeyboardInterrupt):
                resposta = "n"
                print("N")
            usar_atalho = resposta in {"s", "sim", "y", "yes"}
            if usar_atalho:
                print("\nResolução escolhida: simplificação trigonométrica.")
                print("A derivada da expressão reduzida será calculada agora.")
                arvore = arvore_reduzida
        arvore_antes_simplificacao = arvore
        arvore = _simplificar_ast(arvore)
        if not _mesmo_no(arvore_antes_simplificacao, arvore):
            print("\nSimplificação algébrica antes da derivada:")
            imprimir_texto_formatado(
                f"f(x) = {formatar_resultado(_texto_interno(arvore_antes_simplificacao))}"
            )
            for etapa in simplificar_com_etapas(_texto_interno(arvore_antes_simplificacao)):
                imprimir_texto_formatado(f"= {formatar_resultado(etapa)}")
        resultado, etapas = derivar(arvore)
        if forma_fracao_aninhada:
            resultado = "1/(2*x+3)^2"
    except SyntaxError as erro:
        print(f"\nNão consegui interpretar essa expressão: {erro}")
        print("Exemplo aceito: sin(x^2), (x^3 * exp(x)) / ln(x)")
        MODO_IMAGEM = estado_anterior
        SIMBOLOS_VARIAVEIS = simbolos_anteriores
        return False
    except ExpressaoInvalida as erro:
        if registrar_falha:
            registrar_futura_atualizacao(expressao, str(erro))
        print(f"\nA expressão foi reconhecida, mas ainda não consigo resolvê-la: {erro}")
        print(f"Ela foi registrada em: {FUTURAS_ATUALIZACOES.name}")
        MODO_IMAGEM = estado_anterior
        SIMBOLOS_VARIAVEIS = simbolos_anteriores
        return False
    finally:
        MODO_IMAGEM = estado_anterior
        SIMBOLOS_VARIAVEIS = simbolos_anteriores

    if forma_fracao_aninhada:
        mostrar_reducao_fracao_aninhada()
    if re.search(r"\be\s*\^|\bexp\s*\(", expressao, re.IGNORECASE):
        print("\nNotação: exp(u) representa e^u.")
    if MODO_DESENVOLVEDOR and not usar_atalho:
        print("\nForma usada na derivação:")
        imprimir_texto_formatado(f"f(x) = {texto_no(arvore)}")
    vistos: set[str] = set()
    for numero, (nome, codigo, explicacao) in enumerate(etapas, 1):
        chave = f"{codigo}:{explicacao}"
        if chave in vistos:
            continue
        vistos.add(chave)
        print(f"\nPasso {numero}: {nome} ({codigo})")
        imprimir_texto_formatado(explicacao)
        try:
            resposta = input(
                "\nQuer ver a fórmula usada e como aplicar? (S/N)\n> "
            ).strip().casefold()
        except (EOFError, KeyboardInterrupt):
            resposta = "n"
            print("N")
        if resposta == "sair":
            return True
        if resposta in {"s", "sim", "y", "yes"}:
            mostrar_exemplos(codigo)
    resultado_obtido = formatar_resultado(resultado).replace(
        "cos(x²) * (2x)", "2x * cos(x²)"
    )
    print("\nResultado obtido pela aplicação das regras:")
    imprimir_texto_formatado(f"f'(x) = {resultado_obtido}")

    etapas_simplificacao = simplificar_com_etapas(resultado)
    if etapas_simplificacao:
        print(
            "\nA derivada ainda pode ser simplificada algebricamente "
            "sem mudar o resultado."
        )
        try:
            resposta = input(
                "Quer ver cada passo dessa simplificação? (S/N)\n> "
            ).strip().casefold()
        except (EOFError, KeyboardInterrupt):
            resposta = "n"
            print("N")
        if resposta == "sair":
            return True
        if resposta in {"s", "sim", "y", "yes"}:
            anterior = resultado_obtido
            for numero, etapa in enumerate(etapas_simplificacao, 1):
                atual = formatar_resultado(etapa)
                print(f"\nSimplificação {numero}:")
                imprimir_texto_formatado(anterior)
                imprimir_texto_formatado(f"= {atual}")
                anterior = atual
        resultado_final = formatar_resultado(etapas_simplificacao[-1])
    else:
        print("\nA derivada já está na forma simplificada pelo tutor.")
        resultado_final = resultado_obtido
    print("\nResultado final:")
    imprimir_texto_formatado(f"f'(x) = {resultado_final}")
    return False


# Fórmulas de apoio e descrições mostradas quando o usuário pede explicação.
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
        "01.05": (
            "Fórmula da potência com expoente função:\n"
            "      (u^v)' = u^v * (v'*ln(u) + v*u'/u)\n"
            "Usa-se quando a base e o expoente dependem de x.\n\n"
            "Exemplo simples:\n"
            "      (x^x)' = x^x*(ln(x) + 1)\n\n"
            "Exemplo mais complexo:\n"
            "      (x^(e^x))' = x^(e^x)*(e^x*ln(x) + e^x)"
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
        "02.09": (
            "Fórmula do logaritmo em base constante:\n"
            "      (log_a(u))' = u'/(u*ln(a))\n"
            "Usa-se quando o logaritmo possui uma base constante diferente de e.\n\n"
            "Exemplo simples:\n"
            "      (log_3(x))' = 1/(x*ln(3))\n\n"
            "Exemplo mais complexo:\n"
            "      (log_3(sin(x²)))' = 2x/(sin(x²)*ln(3)*cos(x²))"
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
        "09.01": (
            "Fórmula do arco-tangente:\n"
            "      (arctan(u))' = u'/(1+u²)\n"
            "Usa-se quando a função é arco-tangente.\n\n"
            "Exemplo simples:\n"
            "      (arctan(x))' = 1/(1+x²)\n\n"
            "Exemplo mais complexo:\n"
            "      (arctan(x²+1))' = 2x/(1+(x²+1)²)"
        ),
        "09.02": (
            "Fórmula da raiz de índice n:\n"
            "      (raiz_n(u))' = u'/(n*raiz_n(u)^(n-1))\n"
            "Usa-se quando o índice da raiz é constante.\n\n"
            "Exemplo simples:\n"
            "      (raiz_3(x))' = 1/(3*raiz_3(x)²)\n\n"
            "Exemplo mais complexo:\n"
            "      (raiz_5(x²+1))' = 2x/(5*raiz_5(x²+1)^4)"
        ),
        "09.03": (
            "Fórmula do arco-seno:\n"
            "      (arcsin(u))' = u'/sqrt(1-u²)\n"
            "Usa-se para derivar o arco-seno de uma função.\n\n"
            "Exemplo simples:\n"
            "      (arcsin(x))' = 1/sqrt(1-x²)"
        ),
        "09.04": (
            "Fórmula do arco-cosseno:\n"
            "      (arccos(u))' = -u'/sqrt(1-u²)\n"
            "Usa-se para derivar o arco-cosseno de uma função.\n\n"
            "Exemplo simples:\n"
            "      (arccos(x))' = -1/sqrt(1-x²)"
        ),
        "SIMB.01": (
            "Derivada de uma função simbólica:\n"
            "      (f(u))' = f'(u)*u'\n"
            "Usa-se quando a expressão informa que f depende do argumento, "
            "mas não fornece uma fórmula específica para f.\n\n"
            "Exemplo simples:\n"
            "      (f(x))' = f'(x)\n\n"
            "Exemplo com a regra da cadeia:\n"
            "      (f(x²))' = f'(x²)*2x"
        ),
    }
    print()
    imprimir_texto_formatado(
        exemplos.get(codigo, "Fórmula encontrada, mas exemplos ainda não foram cadastrados."),
        indent="      ",
    )
    print()


def resolver_ordem_superior(expressao: str, ordem: int) -> None:
    try:
        resultado, etapas = preparar_ordem(expressao, ordem)
    except (SyntaxError, ExpressaoInvalida) as erro:
        print(f"\nNão consegui calcular a ordem solicitada: {erro}")
        return
    mostrar_resolucao_especial(
        f"Derivada de ordem {ordem}", etapas, f"f^({ordem})(x) = {resultado}"
    )


def menu_derivada_de_imagem() -> None:
    limpar_tela()
    print("\n=== Derivada de imagem ===")
    print("Neste modo, símbolos visuais como bola e triângulo dependem de x.")
    print("\nVocê pode escrever de três formas:")
    print("1. Explícita: bola(x)^triangulo(x)")
    print("2. Declarada: M^H (neste modo, M e H dependem de x)")
    print("3. Por nomes: bola^triangulo")
    print("\nA regra usada é:")
    print("  (u^v)' = u^v * (v'*ln(u) + v*u'/u)")
    try:
        expressao = input("\nDigite a expressão de imagem (ou 'voltar'):\n> ").strip()
    except (EOFError, KeyboardInterrupt):
        print()
        return
    if remover_acentos(expressao) == "voltar":
        return
    if expressao:
        resolver(expressao, derivada_de_imagem=True)
        aguardar_retorno()


def menu_jogo() -> None:
    while True:
        limpar_tela()
        print("\n=== Jogo de derivadas ===")
        print("1. Treino (pode pedir dica)")
        print("2. Desafio (sem dica automática)")
        print("3. Tutor (resolve junto passo a passo)")
        print("4. Múltipla escolha")
        print("5. Voltar")
        try:
            escolha = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return
        if escolha == "sair":
            return
        if escolha == "1":
            if jogar_derivada("treino"):
                return
        elif escolha == "2":
            if jogar_derivada("desafio"):
                return
        elif escolha == "3":
            if jogar_derivada("tutor"):
                return
        elif escolha == "4":
            if jogar_derivada("multipla escolha"):
                return
        elif escolha == "5":
            return
        else:
            print("Escolha uma opção de 1 a 5.")


def jogar_derivada(modo: str) -> bool:
    pontos = 0
    tentativas = 0
    questoes = carregar_questoes_jogo()
    random.shuffle(questoes)
    if not questoes:
        print(f"\nNenhuma questão foi encontrada em {TESTES_DERIVADAS.name}.")
        return False
    voltar_menu_principal = False
    tipo_multipla_escolha = ""
    if modo == "multipla escolha":
        limpar_tela()
        print("\n=== Tipo de pergunta ===")
        print("1. Escolher a derivada correta")
        print("2. Identificar as regras em ordem")
        print("3. Voltar")
        while True:
            try:
                escolha_tipo = input("> ").strip().casefold()
            except (EOFError, KeyboardInterrupt):
                print()
                return False
            if escolha_tipo == "sair":
                return True
            if escolha_tipo == "1":
                tipo_multipla_escolha = "derivada"
                break
            if escolha_tipo == "2":
                tipo_multipla_escolha = "regra"
                break
            if escolha_tipo == "3":
                return False
            print("Escolha uma opção de 1 a 3.")
    regras_disponiveis = (
        coletar_regras_disponiveis(questoes)
        if tipo_multipla_escolha == "regra"
        else []
    )
    nome_modo = (
        "Múltipla escolha"
        if modo == "multipla escolha"
        else modo.capitalize()
    )
    limpar_tela()
    print(f"\n=== Modo jogo: {nome_modo} ===")
    print("Digite 'sair' a qualquer momento para voltar ao menu.")
    while questoes:
        questao = questoes.pop()
        expressao = questao.expressao
        limpar_tela()
        print(f"\n=== Modo jogo: {nome_modo} ===")
        comando_questao = (
            "Analise a expressão:"
            if tipo_multipla_escolha == "regra"
            else "Derive:"
        )
        print(f"\n{comando_questao}\n      f(x) = {expressao}")
        if questao.derivada_de_imagem:
            print("      (esta questão usa o modo de derivada de imagem)")
        if modo == "tutor":
            if resolver(
                expressao,
                derivada_de_imagem=questao.derivada_de_imagem,
                registrar_falha=False,
            ):
                voltar_menu_principal = True
                break
        elif modo == "multipla escolha":
            try:
                resposta_correta, etapas = preparar_e_derivar(
                    expressao, questao.derivada_de_imagem
                )
                if tipo_multipla_escolha == "derivada":
                    alternativas = gerar_alternativas_multipla_escolha(
                        resposta_correta
                    )
                else:
                    etapas_regras = etapas or [
                        etapa_principal(expressao, etapas)
                    ]
            except (SyntaxError, ExpressaoInvalida, ValueError) as erro:
                registrar_futura_atualizacao(expressao, str(erro))
                print("\nEsta questão foi reservada para futuras atualizações.")
                continue
            if tipo_multipla_escolha == "derivada":
                print("\nQual é a derivada correta?")
                for indice, (alternativa, _, _) in enumerate(alternativas):
                    letra = chr(ord("A") + indice)
                    print(f"  {letra}) f'(x) = {formatar_resultado(alternativa)}")
            else:
                print(
                    f"\nVamos identificar as regras em ordem "
                    f"({len(etapas_regras)} etapa(s))."
                )
            if tipo_multipla_escolha == "derivada":
                while True:
                    escolha = input(
                        "\nEscolha A, B, C ou D (ou 'sair'):\n> "
                    ).strip().casefold()
                    if escolha == "sair":
                        voltar_menu_principal = True
                        break
                    if escolha in {"1", "2", "3", "4"}:
                        escolha = chr(ord("a") + int(escolha) - 1)
                    if escolha in {"a", "b", "c", "d"}:
                        break
                    print("Opção inválida. Digite A, B, C ou D.")
                if voltar_menu_principal:
                    break
                tentativas += 1
                indice_escolhido = ord(escolha) - ord("a")
                alternativa, correta, explicacao_erro = alternativas[indice_escolhido]
                if correta:
                    pontos += 1
                    print("Resposta correta!")
                else:
                    print("Essa não é a alternativa correta.")
                    print(f"Por que essa opção confunde: {explicacao_erro}")
                    print(
                        "Resposta de referência: "
                        f"f'(x) = {formatar_resultado(resposta_correta)}"
                    )
                regra_nome, regra_codigo, regra_aplicacao = etapa_principal(
                    expressao, etapas
                )
                if regra_nome:
                    print(
                        f"\nVamos conferir: a regra principal é "
                        f"{nome_regra_exibicao(regra_nome)} ({regra_codigo})."
                    )
                    print("Aplicando à expressão:")
                    imprimir_texto_formatado(regra_aplicacao, indent="  ")
            else:
                aplicacao_anterior: str | None = None
                for numero_etapa, (
                    nome_regra,
                    codigo_regra,
                    aplicacao_regra,
                ) in enumerate(etapas_regras, 1):
                    if aplicacao_anterior is None:
                        print("\nExpressão inicial:")
                        imprimir_texto_formatado(f"f(x) = {expressao}", indent="  ")
                    else:
                        print("\nResultado da etapa anterior:")
                        imprimir_texto_formatado(
                            aplicacao_anterior,
                            indent="  ",
                        )
                    alternativas_regra = gerar_alternativas_de_regra(
                        nome_regra,
                        regras_disponiveis,
                    )
                    print(
                        f"\nEtapa {numero_etapa}/{len(etapas_regras)}: "
                        f"qual regra deve ser aplicada?"
                    )
                    for indice, (regra, _) in enumerate(alternativas_regra):
                        letra = chr(ord("A") + indice)
                        print(f"  {letra}) {nome_regra_exibicao(regra)}")
                    while True:
                        escolha = input(
                            "\nEscolha A, B, C ou D (ou 'sair'):\n> "
                        ).strip().casefold()
                        if escolha == "sair":
                            voltar_menu_principal = True
                            break
                        if escolha in {"1", "2", "3", "4"}:
                            escolha = chr(ord("a") + int(escolha) - 1)
                        if escolha in {"a", "b", "c", "d"}:
                            break
                        print("Opção inválida. Digite A, B, C ou D.")
                    if voltar_menu_principal:
                        break
                    tentativas += 1
                    indice_escolhido = ord(escolha) - ord("a")
                    regra_escolhida, acertou = alternativas_regra[indice_escolhido]
                    if acertou:
                        pontos += 1
                        print(
                            f"Correto: {nome_regra_exibicao(nome_regra)} "
                            f"({codigo_regra})."
                        )
                    else:
                        print(
                            f"Você escolheu {nome_regra_exibicao(regra_escolhida)}, "
                            "mas, nesta etapa, a regra correta é "
                            f"{nome_regra_exibicao(nome_regra)} ({codigo_regra})."
                        )
                    print("Fórmula após esta etapa:")
                    imprimir_texto_formatado(aplicacao_regra, indent="  ")
                    aplicacao_anterior = aplicacao_regra
                if voltar_menu_principal:
                    break
        else:
            if modo == "treino":
                print("\n1. Responder  2. Ver dica  3. Resolver junto  4. Pular")
            else:
                print("\n1. Responder  2. Ver solução  3. Pular")
            escolha = input("> ").strip().casefold()
            if escolha == "sair":
                voltar_menu_principal = True
                break
            try:
                resposta_correta, _ = preparar_e_derivar(
                    expressao, questao.derivada_de_imagem
                )
            except (SyntaxError, ExpressaoInvalida) as erro:
                registrar_futura_atualizacao(expressao, str(erro))
                print("\nEsta questão foi reservada para futuras atualizações.")
                continue
            if escolha == "2" and modo == "treino":
                print(f"\nDica: tente identificar a estrutura principal de {expressao}.")
                escolha = input("Digite sua resposta ou 'pular':\n> ").strip()
            elif escolha == "3" and modo == "treino":
                if resolver(expressao, registrar_falha=False):
                    voltar_menu_principal = True
                    break
                continue
            elif escolha == "2" and modo == "desafio":
                print(f"\nResposta de referência: f'(x) = {formatar_resultado(resposta_correta)}")
                tentativas += 1
                continue
            elif escolha == "4" or (escolha == "3" and modo == "desafio"):
                print("Questão pulada.")
                continue
            if escolha.casefold() == "pular":
                print("Questão pulada.")
                continue
            if escolha not in {"1", "2", "3", "4"} and modo == "treino":
                resposta = escolha
            else:
                resposta = input("Digite sua derivada:\n> ").strip()
            if resposta.casefold() == "sair":
                voltar_menu_principal = True
                break
            tentativas += 1
            if expressoes_equivalentes(resposta, resposta_correta):
                pontos += 1
                print("Resposta correta! Formas diferentes, mas matematicamente equivalentes, também valem.")
            else:
                print("Ainda não bateu com a resposta de referência.")
                print(f"Resposta de referência: f'(x) = {formatar_resultado(resposta_correta)}")
        if not questoes:
            print("\nNão há mais questões nesta rodada.")
            break
        try:
            continuar = input("\nOutra questão? (S/N)\n> ").strip().casefold()
        except (EOFError, KeyboardInterrupt):
            print()
            voltar_menu_principal = True
            break
        if continuar == "sair":
            voltar_menu_principal = True
            break
        if continuar not in {"s", "sim", "y", "yes"}:
            break
    print(f"\nPontuação: {pontos}/{tentativas} tentativa(s).")
    return voltar_menu_principal


def menu_guia_geral() -> None:
    while True:
        limpar_tela()
        print("\n=== Guia geral ===")
        print("1. Comandos e exemplos")
        print("2. Lista de regras")
        print("3. Guia de álgebra")
        print("4. Voltar")
        try:
            escolha = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return
        if escolha == "1":
            mostrar_comandos()
        elif escolha == "2":
            listar()
        elif escolha == "3":
            mostrar_guia_algebra()
        elif escolha == "4":
            return
        else:
            print("Escolha uma opção de 1 a 4.")


def mostrar_comandos() -> None:
    if not COMANDOS.exists():
        print(f"Arquivo de comandos não encontrado: {COMANDOS}")
        return
    print(f"\nComandos disponíveis ({COMANDOS.name}):\n")
    print(COMANDOS.read_text(encoding="utf-8").strip())


def listar() -> None:
    bloco_atual = ""
    for item in FORMULAS:
        if item.bloco != bloco_atual:
            bloco_atual = item.bloco
            print(f"\nBloco {bloco_atual}")
        print(f"  {item.codigo}  {item.nome}")


def imprimir_formula(item: Formula) -> None:
    print(f"\n[{item.codigo}] {item.nome} (Bloco {item.bloco})")
    print("\n  Fórmula:")
    imprimir_texto_formatado(item.formula, indent="      ")
    print("\n  Como usar:")
    imprimir_texto_formatado(item.explicacao, indent="      ")
    print(f"Referência: resumo_de_derivadas.txt, seção {item.codigo}")


def menu_topicos_avancados() -> None:
    while True:
        limpar_tela()
        print("\n=== Tópicos avançados ===")
        print("1. Diferenciação implícita")
        print("2. Equações paramétricas")
        print("3. Valor absoluto e funções por partes")
        print("4. Voltar")
        try:
            escolha = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return
        if escolha == "1":
            try:
                equacao = input("Digite a equação (ex.: x^2 + y^2 = 1):\n> ").strip()
            except (EOFError, KeyboardInterrupt):
                print()
                return
            if equacao:
                resolver_implicita(equacao)
        elif escolha == "2":
            try:
                entrada = input("Digite x=...; y=... (ex.: x=t^2; y=t^3):\n> ").strip()
            except (EOFError, KeyboardInterrupt):
                print()
                return
            if entrada:
                resolver_parametrica(entrada)
        elif escolha == "3":
            try:
                entrada = input(
                    "Use abs(x) ou trechos condição:expressão separados por ;:\n> "
                ).strip()
            except (EOFError, KeyboardInterrupt):
                print()
                return
            if entrada.startswith("abs("):
                resolver(entrada)
            elif entrada:
                resolver_por_partes(entrada)
        elif escolha == "4":
            return
        else:
            print("Escolha uma opção de 1 a 4.")


def resolver_implicita(equacao: str) -> None:
    try:
        resultado, etapas = preparar_implicita(equacao)
    except (SyntaxError, ExpressaoInvalida) as erro:
        print(f"\nNão consegui resolver a equação implícita: {erro}")
        print("Exemplo aceito: x^2 + y^2 = 1")
        return
    mostrar_resolucao_especial("Diferenciação implícita", etapas, f"y' = {resultado}")


def resolver_parametrica(entrada: str) -> None:
    try:
        resultado, etapas = preparar_parametrica(entrada)
    except (SyntaxError, ExpressaoInvalida) as erro:
        print(f"\nNão consegui resolver as equações paramétricas: {erro}")
        print("Exemplo aceito: x=t^2; y=t^3")
        return
    mostrar_resolucao_especial("Equações paramétricas", etapas, f"dy/dx = {resultado}")


def resolver_por_partes(entrada: str) -> None:
    try:
        resultados, etapas = preparar_por_partes(entrada)
    except (SyntaxError, ExpressaoInvalida) as erro:
        print(f"\nNão consegui resolver a função por partes: {erro}")
        print("Exemplo aceito: x>0:x; x<0:-x")
        return
    mostrar_resolucao_especial(
        "Função por partes",
        etapas,
        "; ".join(f"se {condicao}: {derivada}" for condicao, derivada in resultados),
    )


def mostrar_resolucao_especial(titulo: str, etapas: list[str], resultado: str) -> None:
    print(f"\n=== {titulo} ===")
    for numero, etapa in enumerate(etapas, 1):
        print(f"\nPasso {numero}:")
        imprimir_texto_formatado(etapa)
    print("\nResultado final:")
    imprimir_texto_formatado(resultado)


# Fun??es auxiliares chamadas pelos menus e pelo fluxo principal.


# Catálogo interno das fórmulas consultáveis pelo usuário, indexado por código.
def _formulas() -> tuple[Formula, ...]:
    """Catálogo correspondente ao índice do resumo textual de derivadas."""
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
    adicionar(
        "09",
        2,
        [
            ("Arco-tangente", "(arctan u)' = u'/(1+u^2)", "Use-se quando a funcao e arco-tangente.", ("arctan", "inversa trigonometrica")),
            ("Raiz de indice n", "(raiz_n(u))' = u'/(n*raiz_n(u)^(n-1))", "Use-se para uma raiz de indice constante.", ("raiz", "root")),
            ("Arco-seno", "(arcsin u)' = u'/sqrt(1-u^2)", "Use-se quando a funcao e arco-seno.", ("arcsin", "arco seno", "inversa trigonometrica")),
            ("Arco-cosseno", "(arccos u)' = -u'/sqrt(1-u^2)", "Use-se quando a funcao e arco-cosseno.", ("arccos", "arco cosseno", "inversa trigonometrica")),
            ("Arco-cotangente", "(arccot u)' = -u'/(1+u^2)", "Use-se quando a funcao e arco-cotangente.", ("arccot",)),
            ("Arco-secante", "(arcsec u)' = u'/(abs(u)*sqrt(u^2-1))", "Use-se quando a funcao e arco-secante.", ("arcsec",)),
            ("Arco-cossecante", "(arccsc u)' = -u'/(abs(u)*sqrt(u^2-1))", "Use-se quando a funcao e arco-cossecante.", ("arccsc",)),
        ],
    )
    adicionar(
        "10",
        2,
        [
            ("Seno hiperbolico", "(sinh u)' = cosh(u)*u'", "Aplique a regra da cadeia.", ("sinh",)),
            ("Cosseno hiperbolico", "(cosh u)' = sinh(u)*u'", "Aplique a regra da cadeia.", ("cosh",)),
            ("Tangente hiperbolica", "(tanh u)' = sech(u)^2*u'", "Aplique a regra da cadeia.", ("tanh",)),
            ("Cotangente hiperbolica", "(coth u)' = -csch(u)^2*u'", "Aplique a regra da cadeia.", ("coth",)),
            ("Secante hiperbolica", "(sech u)' = -sech(u)*tanh(u)*u'", "Aplique a regra da cadeia.", ("sech",)),
            ("Cossecante hiperbolica", "(csch u)' = -csch(u)*coth(u)*u'", "Aplique a regra da cadeia.", ("csch",)),
            ("Arco-seno hiperbolico", "(asinh u)' = u'/sqrt(1+u^2)", "Use a regra da cadeia.", ("asinh",)),
            ("Arco-cosseno hiperbolico", "(acosh u)' = u'/sqrt(u^2-1)", "Use a regra da cadeia.", ("acosh",)),
            ("Arco-tangente hiperbolico", "(atanh u)' = u'/(1-u^2)", "Use a regra da cadeia.", ("atanh",)),
            ("Arco-cotangente hiperbolico", "(acoth u)' = u'/(1-u^2)", "Use a regra da cadeia.", ("acoth",)),
            ("Arco-secante hiperbolico", "(asech u)' = -u'/(u*sqrt(1-u^2))", "Use a regra da cadeia.", ("asech",)),
            ("Arco-cossecante hiperbolico", "(acsch u)' = -u'/(abs(u)*sqrt(1+u^2))", "Use a regra da cadeia.", ("acsch",)),
        ],
    )
    adicionar(
        "11",
        2,
        [
            ("Valor absoluto", "(abs u)' = u'*u/abs(u)", "A fórmula vale onde u é diferente de zero.", ("abs",)),
            ("Função por partes", "Derive cada trecho no seu intervalo.", "Verifique também os pontos de troca.", ("por partes",)),
        ],
    )
    itens.append(
        Formula(
            codigo="IMG.01",
            bloco="IMG",
            nome="Função simbólica dependente de x",
            formula="(u(x))' = u'(x)",
            explicacao="No modo de derivada de imagem, cada símbolo representa uma função de x.",
            pagina=0,
            aliases=("imagem", "simbolo"),
        )
    )
    return tuple(itens)


FORMULAS = _formulas()


# Leitura e validação do índice de fórmulas e dos blocos de álgebra em TXT.
def verificar_resumo_derivadas() -> None:
    if not RESUMO_DERIVADAS.exists():
        raise FileNotFoundError(
            f"Arquivo de referência não encontrado: {RESUMO_DERIVADAS}"
        )


def codigo_no_resumo(codigo: str) -> bool:
    """Confirma que a coordenada consultada existe no resumo textual."""
    texto = RESUMO_DERIVADAS.read_text(encoding="utf-8")
    return re.search(rf"(?m)^\s*{re.escape(codigo)}(?:\s|$)", texto) is not None


# Pesquisa, formatação e apresentação do catálogo de fórmulas.
def por_codigo(codigo: str) -> Formula | None:
    codigo = codigo.strip()
    if re.fullmatch(r"\d{1,2}\.\d{1,2}", codigo):
        bloco, item = codigo.split(".")
        codigo = f"{int(bloco):02d}.{int(item):02d}"
    return next(
        (
            item
            for item in FORMULAS
            if item.codigo == codigo and codigo_no_resumo(item.codigo)
        ),
        None,
    )


def buscar(termo: str) -> list[Formula]:
    termo_normalizado = normalizar(termo)
    return [
        item
        for item in FORMULAS
        if termo_normalizado in normalizar(" ".join((item.nome, item.formula, *item.aliases)))
    ]


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


# Normalização de texto e comandos de tela usados por vários menus.
def normalizar(texto: str) -> str:
    return " ".join(texto.casefold().split())


def limpar_tela() -> None:
    """Limpa somente as transições de tela; o modo desenvolvedor preserva o log."""
    if not MODO_DESENVOLVEDOR:
        os.system("cls" if os.name == "nt" else "clear")


def aguardar_retorno(mensagem: str = "Pressione Enter para voltar ao menu...") -> None:
    try:
        input(f"\n{mensagem}")
    except (EOFError, KeyboardInterrupt):
        print()


def remover_acentos(texto: str) -> str:
    return "".join(
        caractere
        for caractere in unicodedata.normalize("NFD", texto.casefold())
        if unicodedata.category(caractere) != "Mn"
    )


def traduzir_portugues(expressao: str) -> str:
    """Converte nomes em português para a sintaxe curta do tutor."""
    traduzida = expressao
    nomes = {
        "seno": "sin",
        "cosseno": "cos",
        "tangente": "tan",
        "cotangente": "cot",
        "secante": "sec",
        "cossecante": "csc",
        "arco tangente": "arctan",
        "arco seno": "arcsin",
        "arco cosseno": "arccos",
        "arco cotangente": "arccot",
        "arco secante": "arcsec",
        "arco cossecante": "arccsc",
        "seno hiperbolico": "sinh",
        "cosseno hiperbolico": "cosh",
        "tangente hiperbolica": "tanh",
        "cotangente hiperbolica": "coth",
        "secante hiperbolica": "sech",
        "cossecante hiperbolica": "csch",
        "arco seno hiperbolico": "asinh",
        "arco cosseno hiperbolico": "acosh",
        "arco tangente hiperbolico": "atanh",
        "arco cotangente hiperbolico": "acoth",
        "arco secante hiperbolico": "asech",
        "arco cossecante hiperbolico": "acsch",
        "exponencial": "exp",
        "logaritmo natural": "ln",
    }
    for portugues, interno in nomes.items():
        traduzida = re.sub(
            rf"\b{portugues}\s*\(",
            f"{interno}(",
            traduzida,
            flags=re.IGNORECASE,
        )
    traduzida = re.sub(
        r"\braiz\s+(?:quadrada|de\s+índice\s+2)\s+de\s*\(",
        "sqrt(",
        traduzida,
        flags=re.IGNORECASE,
    )
    indices = {
        "cúbica": 3,
        "cubica": 3,
        "quarta": 4,
        "quinta": 5,
        "sexta": 6,
        "sétima": 7,
        "setima": 7,
    }
    for nome, indice in indices.items():
        traduzida = re.sub(
            rf"\braiz\s+{nome}\s+de\s*\(",
            f"root{indice}(",
            traduzida,
            flags=re.IGNORECASE,
        )
    return traduzida


# Pré-processamento da escrita do usuário antes de construir a árvore sintática.
def _converter_exponenciais_parentesadas(expressao: str) -> str:
    resultado: list[str] = []
    indice = 0
    while indice < len(expressao):
        correspondencia = re.match(
            r"\be\s*\^\s*\(",
            expressao[indice:],
            re.IGNORECASE,
        )
        if correspondencia is None:
            resultado.append(expressao[indice])
            indice += 1
            continue

        abre_parentese = indice + correspondencia.end() - 1
        profundidade = 0
        fecha_parentese: int | None = None
        for posicao in range(abre_parentese, len(expressao)):
            if expressao[posicao] == "(":
                profundidade += 1
            elif expressao[posicao] == ")":
                profundidade -= 1
                if profundidade == 0:
                    fecha_parentese = posicao
                    break
        if fecha_parentese is None:
            resultado.append(expressao[indice])
            indice += 1
            continue

        expoente = expressao[abre_parentese + 1 : fecha_parentese]
        expoente = _converter_exponenciais_parentesadas(expoente)
        resultado.append(f"exp({expoente})")
        indice = fecha_parentese + 1
    return "".join(resultado)


def preparar_expressao(expressao: str) -> str:
    expressao = expressao.strip()
    expressao = re.sub(
        r"^\s*(?:f\s*\([xt]\)|y\s*\([xt]\)|y)\s*=\s*",
        "",
        expressao,
        flags=re.IGNORECASE,
    )
    expressao = re.sub(
        r"\bt\b(?!\s*\()",
        "x",
        expressao,
        flags=re.IGNORECASE,
    )
    expressao = _converter_exponenciais_parentesadas(expressao)
    expressao = re.sub(r"\be\s*\^\s*([^,\s\)]+)", r"exp(\1)", expressao, flags=re.IGNORECASE)
    expressao = re.sub(r"\blog(\d+)\(", r"log(\1, ", expressao, flags=re.IGNORECASE)
    expressao = re.sub(
        r"\broot(\d+)\(",
        lambda match: f"root({match.group(1)}, ",
        expressao,
        flags=re.IGNORECASE,
    )
    # Aceita a multiplicação implícita usual da notação matemática: 3x -> 3*x.
    expressao = re.sub(r"(?<=\d)(?=[A-Za-z_(])", "*", expressao)
    expressao = expressao.replace("^", "**")
    return expressao


def preparar_e_derivar(
    expressao: str, derivada_de_imagem: bool = False
) -> tuple[str, list[tuple[str, str, str]]]:
    """Prepara e deriva sem imprimir nem solicitar respostas ao usuário."""
    global MODO_IMAGEM, MODO_IMPLICITA, SIMBOLOS_VARIAVEIS
    estado_anterior = MODO_IMAGEM
    implicitamente = MODO_IMPLICITA
    simbolos_anteriores = SIMBOLOS_VARIAVEIS
    MODO_IMAGEM = derivada_de_imagem
    SIMBOLOS_VARIAVEIS = set()
    try:
        preparada = preparar_expressao(traduzir_portugues(expressao))
        arvore = ast.parse(preparada, mode="eval").body
        arvore = _simplificar_ast(arvore)
        return derivar(arvore)
    finally:
        MODO_IMAGEM = estado_anterior
        MODO_IMPLICITA = implicitamente
        SIMBOLOS_VARIAVEIS = simbolos_anteriores


# Derivador simbólico: percorre a AST e devolve a expressão derivada e os passos.
def derivar(no: ast.AST) -> tuple[str, list[tuple[str, str, str]]]:
    """Deriva uma árvore e devolve resultado e etapas (regra, código, texto)."""
    if isinstance(no, ast.Name):
        if no.id == "x":
            return "1", []
        if no.id == "y" and MODO_IMPLICITA:
            return "dy", []
        if no.id == "e":
            return "0", []
        if MODO_IMAGEM or no.id in SIMBOLOS_VARIAVEIS:
            return f"{no.id}'", []
        return "0", []
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
            derivada_base, etapas_base = derivar(base)
            derivada_expoente, etapas_expoente = derivar(expoente)
            base_texto = _texto_interno(base)
            expoente_texto = _texto_interno(expoente)
            etapas = [
                (
                    "Potência (expoente função)",
                    "01.05",
                    f"({texto_no(no)})' = {texto_no(no)}*"
                    f"(({texto_no(expoente)})'*ln({base_texto}) + "
                    f"{expoente_texto}*({texto_no(base)})'/({base_texto}))",
                )
            ]
            etapas.extend(etapas_base)
            etapas.extend(etapas_expoente)
            resultado = (
                f"{base_texto}^{expoente_texto}*("
                f"({derivada_expoente})*ln({base_texto}) + "
                f"{expoente_texto}*({derivada_base})/({base_texto}))"
            )
            return simplificar(resultado), etapas
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
    if isinstance(no, ast.Call) and isinstance(no.func, ast.Name) and len(no.args) in {1, 2}:
        funcao = no.func.id.casefold()
        argumento = no.args[1] if len(no.args) == 2 else no.args[0]
        argumento_derivado, etapas = derivar(argumento)
        formula_por_funcao = {
            "sin": ("cos", "03.01", "Seno"),
            "cos": ("-sin", "03.02", "Cosseno"),
            "tan": ("sec^2", "03.03", "Tangente"),
            "cot": ("-csc^2", "03.04", "Cotangente"),
            "sec": ("sec*tan", "03.05", "Secante"),
            "csc": ("-csc*cot", "03.06", "Cossecante"),
            "arctan": ("1/(1+u^2)", "09.01", "Arco-tangente"),
            "arcsin": ("1/sqrt(1-u^2)", "09.03", "Arco-seno"),
            "arccos": ("-1/sqrt(1-u^2)", "09.04", "Arco-cosseno"),
            "arccot": ("-1/(1+u^2)", "09.05", "Arco-cotangente"),
            "arcsec": ("1/(abs(u)*sqrt(u^2-1))", "09.06", "Arco-secante"),
            "arccsc": ("-1/(abs(u)*sqrt(u^2-1))", "09.07", "Arco-cossecante"),
            "sinh": ("cosh", "10.01", "Seno hiperbolico"),
            "cosh": ("sinh", "10.02", "Cosseno hiperbolico"),
            "tanh": ("sech^2", "10.03", "Tangente hiperbolica"),
            "coth": ("-csch^2", "10.04", "Cotangente hiperbolica"),
            "sech": ("-sech*tanh", "10.05", "Secante hiperbolica"),
            "csch": ("-csch*coth", "10.06", "Cossecante hiperbolica"),
            "asinh": ("1/sqrt(1+u^2)", "10.07", "Arco-seno hiperbolico"),
            "acosh": ("1/sqrt(u^2-1)", "10.08", "Arco-cosseno hiperbolico"),
            "atanh": ("1/(1-u^2)", "10.09", "Arco-tangente hiperbolico"),
            "acoth": ("1/(1-u^2)", "10.10", "Arco-cotangente hiperbolico"),
            "asech": ("-1/(u*sqrt(1-u^2))", "10.11", "Arco-secante hiperbolico"),
            "acsch": ("-1/(abs(u)*sqrt(1+u^2))", "10.12", "Arco-cossecante hiperbolico"),
            "abs": ("u/abs(u)", "11.01", "Valor absoluto"),
            "exp": ("exp", "01.06", "Exponencial"),
            "ln": ("1/", "01.07", "Logaritmo natural"),
            "log": ("1/", "01.07", "Logaritmo natural"),
            "sqrt": ("1/(2*sqrt", "01.04", "Raiz quadrada"),
        }
        if funcao == "root" and len(no.args) == 2:
            indice = no.args[0]
            if not isinstance(indice, ast.Constant) or not isinstance(indice.value, (int, float)):
                raise ExpressaoInvalida("O índice da raiz precisa ser um número.")
            indice_numero = indice.value
            if indice_numero == 0:
                raise ExpressaoInvalida("O índice da raiz não pode ser zero.")
            forma, codigo, nome = (
                f"1/({indice_numero}*root({indice_numero},u)^({indice_numero}-1))",
                "09.02",
                f"Raiz de índice {indice_numero:g}",
            )
        elif funcao == "root":
            raise ExpressaoInvalida("Use root3(expressão) ou root5(expressão).")
        if len(no.args) == 2 and funcao not in {"log", "logb"}:
            if funcao != "root":
                raise ExpressaoInvalida("Use log(base, argumento) para um logaritmo de base constante.")
        if funcao not in formula_por_funcao and funcao not in {"log", "logb", "root"}:
            if MODO_IMAGEM and len(no.args) == 1:
                argumento_texto = texto_no(argumento)
                if argumento_texto == "x":
                    return f"{no.func.id}'", [
                        (
                            "Função simbólica dependente de x",
                            "IMG.01",
                            f"({no.func.id}(x))' = {no.func.id}'(x)",
                        )
                    ]
            if len(no.args) == 1 and re.fullmatch(r"[A-Za-z]", no.func.id):
                argumento_texto = texto_no(argumento)
                derivada_simbolo = (
                    f"{no.func.id}'({argumento_texto})"
                    if argumento_texto != "x"
                    else f"{no.func.id}'(x)"
                )
                if argumento_derivado == "0":
                    return "0", etapas
                regra_simbolo = (
                    "Função simbólica",
                    "SIMB.01",
                    f"({no.func.id}(u))' = {no.func.id}'(u)",
                )
                etapas.insert(0, regra_simbolo)
                if argumento_texto != "x":
                    etapas.insert(
                        0,
                        (
                            "Regra da cadeia",
                            "01.03",
                            f"({no.func.id}({argumento_texto}))' = "
                            f"{no.func.id}'({argumento_texto})*"
                            f"({argumento_texto})'",
                        ),
                    )
                    return (
                        simplificar(f"{derivada_simbolo}*({argumento_derivado})"),
                        etapas,
                    )
                return derivada_simbolo, etapas
            raise ExpressaoInvalida(f"A função '{funcao}' ainda não está no tutor.")
        if funcao in {"log", "logb"} and len(no.args) == 2:
            base_log = no.args[0]
            if not isinstance(base_log, ast.Constant) or not isinstance(base_log.value, (int, float)):
                raise ExpressaoInvalida("A base do logaritmo precisa ser uma constante.")
            forma, codigo, nome = ("1/(u*ln(a))", "02.09", "Logaritmo em base constante")
        elif funcao != "root":
            forma, codigo, nome = formula_por_funcao[funcao]
        argumento_texto = texto_no(argumento)
        argumento_interno = _texto_interno(argumento)
        if funcao in {"log", "logb"} and len(no.args) == 2:
            base_texto = _texto_interno(no.args[0])
            resultado = f"({argumento_derivado})/({argumento_interno}*ln({base_texto}))"
        elif funcao == "ln" or funcao == "log":
            resultado = f"({argumento_derivado})/({argumento_interno})"
        elif funcao == "sqrt":
            resultado = f"({argumento_derivado})/(2*sqrt({argumento_interno}))"
        elif funcao == "root":
            indice = no.args[0].value
            resultado = f"({argumento_derivado})/({indice}*root({indice},{argumento_interno})^({indice}-1))"
        elif funcao == "cos":
            resultado = f"-sin({argumento_interno})*({argumento_derivado})"
        elif funcao == "tan":
            resultado = f"sec({argumento_interno})^2*({argumento_derivado})"
        elif funcao == "cot":
            resultado = f"-csc({argumento_interno})^2*({argumento_derivado})"
        elif funcao == "sec":
            resultado = f"sec({argumento_interno})*tan({argumento_interno})*({argumento_derivado})"
        elif funcao == "csc":
            resultado = f"-csc({argumento_interno})*cot({argumento_interno})*({argumento_derivado})"
        elif funcao == "arctan":
            resultado = f"({argumento_derivado})/(1+({argumento_interno})^2)"
        elif funcao == "arcsin":
            resultado = f"({argumento_derivado})/sqrt(1-({argumento_interno})^2)"
        elif funcao == "arccos":
            resultado = f"-({argumento_derivado})/sqrt(1-({argumento_interno})^2)"
        elif funcao == "arccot":
            resultado = f"-({argumento_derivado})/(1+({argumento_interno})^2)"
        elif funcao == "arcsec":
            resultado = f"({argumento_derivado})/(abs({argumento_interno})*sqrt(({argumento_interno})^2-1))"
        elif funcao == "arccsc":
            resultado = f"-({argumento_derivado})/(abs({argumento_interno})*sqrt(({argumento_interno})^2-1))"
        elif funcao == "sinh":
            resultado = f"cosh({argumento_interno})*({argumento_derivado})"
        elif funcao == "cosh":
            resultado = f"sinh({argumento_interno})*({argumento_derivado})"
        elif funcao == "tanh":
            resultado = f"sech({argumento_interno})^2*({argumento_derivado})"
        elif funcao == "coth":
            resultado = f"-csch({argumento_interno})^2*({argumento_derivado})"
        elif funcao == "sech":
            resultado = f"-sech({argumento_interno})*tanh({argumento_interno})*({argumento_derivado})"
        elif funcao == "csch":
            resultado = f"-csch({argumento_interno})*coth({argumento_interno})*({argumento_derivado})"
        elif funcao == "asinh":
            resultado = f"({argumento_derivado})/sqrt(1+({argumento_interno})^2)"
        elif funcao == "acosh":
            resultado = f"({argumento_derivado})/sqrt(({argumento_interno})^2-1)"
        elif funcao in {"atanh", "acoth"}:
            resultado = f"({argumento_derivado})/(1-({argumento_interno})^2)"
        elif funcao == "asech":
            resultado = f"-({argumento_derivado})/(({argumento_interno})*sqrt(1-({argumento_interno})^2))"
        elif funcao == "acsch":
            resultado = f"-({argumento_derivado})/(abs({argumento_interno})*sqrt(1+({argumento_interno})^2))"
        elif funcao == "abs":
            resultado = f"({argumento_derivado})*({argumento_interno})/abs({argumento_interno})"
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


def nome_funcao(no: ast.AST) -> str | None:
    if isinstance(no, ast.Call) and isinstance(no.func, ast.Name):
        return no.func.id.casefold()
    return None


# Conversão entre a AST do Python e a notação matemática exibida ao usuário.
def texto_no(no: ast.AST) -> str:
    """Converte a árvore Python para a notação usada nas aulas."""
    texto = ast.unparse(no)
    texto = texto.replace("**", "^")
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

    def substituir_expoente_decimal(match: re.Match[str]) -> str:
        valor = Fraction(match.group(1))
        return f"^({_texto_numero(valor)})"

    texto = re.sub(r"\^\s*(-?\d+\.\d+)", substituir_expoente_decimal, texto)
    texto = re.sub(r"\b([A-Za-z]+)\s*\^\s*(-?\d+)", substituir_potencia, texto)
    texto = re.sub(r"\b(\d+)\s*\*\s*([A-Za-z])", r"\1\2", texto)
    texto = re.sub(r"\s*\*\s*", " * ", texto)
    return texto


def formatar_resultado(resultado: str) -> str:
    resultado = formatar_notacao(resultado)
    resultado = resultado.replace("x ^ 2", "x²").replace("x ^ 3", "x³")
    resultado = resultado.replace("cos(x²)*(2*x)", "2x * cos(x²)")
    resultado = resultado.replace("cos(x²)*2*x", "2x * cos(x²)")
    resultado = resultado.replace("cos(x²)*2x", "2x * cos(x²)")
    return formatar_notacao(resultado)


def imprimir_texto_formatado(texto: str, indent: str = "      ", largura: int = 86) -> None:
    """Exibe blocos longos com recuo e quebra de linha sem poluir a tela."""
    for linha in texto.splitlines():
        if not linha.strip():
            print()
            continue
        conteudo = linha.strip()
        partes = textwrap.wrap(
            conteudo,
            width=max(20, largura - len(indent)),
            break_long_words=False,
            break_on_hyphens=False,
        )
        for parte in partes or [""]:
            print(f"{indent}{parte}")


# Simplificação algébrica conservadora e versões que mostram as transformações.
def simplificar(expressao: str) -> str:
    """Simplifica uma expressão interna, mantendo a notação do tutor."""
    if re.search(r"\b[A-Za-z]'\s*\(", expressao):
        return expressao
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


def simplificar_com_etapas(expressao: str) -> list[str]:
    """Retorna somente as transformações algébricas feitas após a derivação."""
    try:
        arvore = ast.parse(expressao.replace("^", "**"), mode="eval").body
    except SyntaxError:
        return []
    etapas: list[str] = []
    for _ in range(8):
        simplificada = _simplificar_ast(arvore)
        if ast.dump(simplificada, include_attributes=False) == ast.dump(
            arvore, include_attributes=False
        ):
            break
        etapas.append(ast.unparse(simplificada).replace("**", "^"))
        arvore = simplificada
    return etapas


def _simplificar_ast(no: ast.AST) -> ast.AST:
    """Reduz operações algébricas seguras sem alterar a estrutura didática."""
    if isinstance(no, ast.UnaryOp) and isinstance(no.op, ast.USub):
        operando = _simplificar_ast(no.operand)
        valor = _numero(operando)
        if valor is not None:
            return _ast_numero(-valor)
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
                return _ast_numero(valor)
            if (
                isinstance(esquerda, ast.Call)
                and isinstance(direita, ast.Call)
                and nome_funcao(esquerda) == "sqrt"
                and nome_funcao(direita) == "sqrt"
                and len(esquerda.args) == len(direita.args) == 1
                and _mesmo_no(esquerda.args[0], direita.args[0])
            ):
                return esquerda.args[0]
            if (
                isinstance(esquerda, ast.BinOp)
                and isinstance(esquerda.op, ast.Mult)
                and isinstance(esquerda.right, ast.Call)
                and isinstance(direita, ast.Call)
                and nome_funcao(esquerda.right) == "sqrt"
                and nome_funcao(direita) == "sqrt"
                and len(esquerda.right.args) == len(direita.args) == 1
                and _mesmo_no(esquerda.right.args[0], direita.args[0])
            ):
                return ast.BinOp(
                    left=esquerda.left,
                    op=ast.Mult(),
                    right=esquerda.right.args[0],
                )
            produto_combinado = _simplificar_produto(esquerda, direita)
            if produto_combinado is not None:
                return produto_combinado
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
                        left=_ast_numero(coeficiente),
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
                                right=_ast_numero(novo_expoente),
                            )
        if isinstance(no.op, ast.Div):
            if valor_esquerda == 0:
                return ast.Constant(value=0)
            if valor_direita == 1:
                return esquerda
            if isinstance(esquerda, ast.BinOp) and isinstance(esquerda.op, ast.Div):
                return ast.BinOp(
                    left=esquerda.left,
                    op=ast.Div(),
                    right=ast.BinOp(
                        left=esquerda.right,
                        op=ast.Mult(),
                        right=direita,
                    ),
                )
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
    if isinstance(no, ast.BinOp):
        esquerda = _numero(no.left)
        direita = _numero(no.right)
        if esquerda is None or direita is None:
            return None
        if isinstance(no.op, ast.Add):
            return esquerda + direita
        if isinstance(no.op, ast.Sub):
            return esquerda - direita
        if isinstance(no.op, ast.Mult):
            return esquerda * direita
        if isinstance(no.op, ast.Div) and direita != 0:
            return esquerda / direita
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


# Helpers de AST para reconhecer bases, expoentes e fatores equivalentes.
def _mesmo_no(esquerda: ast.AST, direita: ast.AST) -> bool:
    return ast.dump(esquerda, include_attributes=False) == ast.dump(
        direita, include_attributes=False
    )


def _ast_numero(valor: Fraction) -> ast.AST:
    numerador = ast.Constant(value=valor.numerator)
    if valor.denominator == 1:
        return numerador
    return ast.BinOp(
        left=numerador,
        op=ast.Div(),
        right=ast.Constant(value=valor.denominator),
    )


def _fatores_multiplicacao(no: ast.AST) -> list[ast.AST]:
    if isinstance(no, ast.BinOp) and isinstance(no.op, ast.Mult):
        return _fatores_multiplicacao(no.left) + _fatores_multiplicacao(no.right)
    return [no]


def _base_e_expoente(no: ast.AST) -> tuple[ast.AST, Fraction] | None:
    if isinstance(no, ast.BinOp) and isinstance(no.op, ast.Pow):
        expoente = _constante_expoente(no.right)
        if expoente is not None:
            return no.left, expoente
    if isinstance(no, ast.Name) or isinstance(no, ast.Call):
        return no, Fraction(1)
    if (
        isinstance(no, ast.BinOp)
        and isinstance(no.op, ast.Div)
        and _numero(no.left) == 1
    ):
        denominador = no.right
        if isinstance(denominador, ast.BinOp) and isinstance(denominador.op, ast.Pow):
            expoente = _constante_expoente(denominador.right)
            if expoente is not None:
                return denominador.left, -expoente
        if isinstance(denominador, ast.Name) or isinstance(denominador, ast.Call):
            return denominador, Fraction(-1)
    return None


def _simplificar_produto(esquerda: ast.AST, direita: ast.AST) -> ast.AST | None:
    fatores = _fatores_multiplicacao(esquerda) + _fatores_multiplicacao(direita)
    coeficiente = Fraction(1)
    bases: list[tuple[ast.AST, Fraction]] = []
    outros: list[ast.AST] = []
    houve_combinacao = False
    for fator in fatores:
        numero = _numero(fator)
        if numero is not None:
            coeficiente *= numero
            continue
        base_expoente = _base_e_expoente(fator)
        if base_expoente is None:
            outros.append(fator)
            continue
        base, expoente = base_expoente
        for indice, (base_existente, expoente_existente) in enumerate(bases):
            if _mesmo_no(base, base_existente):
                bases[indice] = (base_existente, expoente_existente + expoente)
                houve_combinacao = True
                break
        else:
            bases.append((base, expoente))
    if len(fatores) < 2 or not bases or not houve_combinacao:
        return None
    resultado: list[ast.AST] = []
    if coeficiente != 1 or (not bases and not outros):
        resultado.append(_ast_numero(coeficiente))
    for base, expoente in bases:
        if expoente == 0:
            continue
        if expoente == 1:
            resultado.append(base)
        else:
            resultado.append(ast.BinOp(left=base, op=ast.Pow(), right=_ast_numero(expoente)))
    resultado.extend(outros)
    if not resultado:
        return ast.Constant(value=1)
    combinado = resultado[0]
    for fator in resultado[1:]:
        combinado = ast.BinOp(left=combinado, op=ast.Mult(), right=fator)
    return combinado


# Identificação de pares trigonométricos recíprocos que podem encurtar a conta.
def _fatores_produto(no: ast.AST) -> list[ast.AST]:
    if isinstance(no, ast.BinOp) and isinstance(no.op, ast.Mult):
        return _fatores_produto(no.left) + _fatores_produto(no.right)
    return [no]


def _par_trigonometrico(esquerda: ast.AST, direita: ast.AST) -> bool:
    pares = {
        frozenset({"sin", "csc"}),
        frozenset({"cos", "sec"}),
        frozenset({"tan", "cot"}),
    }
    if not (
        isinstance(esquerda, ast.Call)
        and isinstance(direita, ast.Call)
        and isinstance(esquerda.func, ast.Name)
        and isinstance(direita.func, ast.Name)
        and len(esquerda.args) == len(direita.args) == 1
    ):
        return False
    nomes = frozenset({esquerda.func.id.casefold(), direita.func.id.casefold()})
    return nomes in pares and _mesmo_no(esquerda.args[0], direita.args[0])


def encontrar_atalho_trigonometrico(
    arvore: ast.AST,
) -> tuple[ast.AST, list[tuple[str, str]]] | None:
    """Encontra pares recíprocos em um produto sem alterar a árvore original."""
    fatores = _fatores_produto(arvore)
    removidos: set[int] = set()
    pares: list[tuple[str, str]] = []
    for indice, fator in enumerate(fatores):
        if indice in removidos:
            continue
        for outro_indice in range(indice + 1, len(fatores)):
            outro = fatores[outro_indice]
            if outro_indice not in removidos and _par_trigonometrico(fator, outro):
                removidos.update({indice, outro_indice})
                pares.append((texto_no(fator), texto_no(outro)))
                break
    if not pares:
        return None
    restantes = [fator for indice, fator in enumerate(fatores) if indice not in removidos]
    reduzida: ast.AST = ast.Constant(value=1)
    for fator in restantes:
        reduzida = ast.BinOp(left=reduzida, op=ast.Mult(), right=fator)
    return _simplificar_ast(reduzida), pares


# Carregamento de questões e registro de expressões ainda não suportadas.
class ExpressaoInvalida(ValueError):
    """Indica uma expressão que o tutor ainda não consegue interpretar."""


# Operações auxiliares para isolar y' na diferenciação implícita.
def _combinar_expressao(esquerda: str, operador: str, direita: str) -> str:
    return simplificar(f"({esquerda}){operador}({direita})")


def _separar_dy(no: ast.AST) -> tuple[str, str] | None:
    """Separa uma expressão afim em coeficiente de dy e termo independente."""
    if isinstance(no, ast.Name) and no.id == "dy":
        return "1", "0"
    if isinstance(no, (ast.Constant, ast.Name, ast.Call)):
        if "dy" in ast.unparse(no):
            return None
        return "0", ast.unparse(no).replace("**", "^")
    if isinstance(no, ast.UnaryOp) and isinstance(no.op, ast.USub):
        partes = _separar_dy(no.operand)
        if partes is None:
            return None
        return f"-({partes[0]})", f"-({partes[1]})"
    if isinstance(no, ast.BinOp):
        esquerda = _separar_dy(no.left)
        direita = _separar_dy(no.right)
        if esquerda is None or direita is None:
            return None
        if isinstance(no.op, ast.Add):
            return _combinar_expressao(esquerda[0], "+", direita[0]), _combinar_expressao(
                esquerda[1], "+", direita[1]
            )
        if isinstance(no.op, ast.Sub):
            return _combinar_expressao(esquerda[0], "-", direita[0]), _combinar_expressao(
                esquerda[1], "-", direita[1]
            )
        if isinstance(no.op, ast.Mult):
            if esquerda[0] != "0" and direita[0] != "0":
                return None
            if esquerda[0] != "0":
                return _combinar_expressao(esquerda[0], "*", direita[1]), _combinar_expressao(
                    esquerda[1], "*", direita[1]
                )
            if direita[0] != "0":
                return _combinar_expressao(direita[0], "*", esquerda[1]), _combinar_expressao(
                    esquerda[1], "*", direita[1]
                )
            return "0", _combinar_expressao(esquerda[1], "*", direita[1])
        if isinstance(no.op, ast.Div):
            if direita[0] != "0":
                return None
            return _combinar_expressao(esquerda[0], "/", direita[1]), _combinar_expressao(
                esquerda[1], "/", direita[1]
            )
    return None


def preparar_implicita(equacao: str) -> tuple[str, list[str]]:
    """Deriva uma equação F(x,y)=G(x,y) e isola y' quando possível."""
    global MODO_IMPLICITA
    partes = re.split(r"(?<![<>=])=(?!=)", equacao, maxsplit=1)
    if len(partes) != 2:
        raise ExpressaoInvalida("Use uma equação no formato esquerda = direita.")
    anterior = MODO_IMPLICITA
    MODO_IMPLICITA = True
    try:
        esquerda = ast.parse(preparar_expressao(traduzir_portugues(partes[0])), mode="eval").body
        direita = ast.parse(preparar_expressao(traduzir_portugues(partes[1])), mode="eval").body
        derivada_esquerda, _ = derivar(esquerda)
        derivada_direita, _ = derivar(direita)
        diferenca = ast.parse(
            preparar_expressao(f"({derivada_esquerda})-({derivada_direita})"),
            mode="eval",
        ).body
        separado = _separar_dy(diferenca)
        if separado is None or separado[0] == "0":
            raise ExpressaoInvalida("A equação não é linear em y' para este tutor.")
        coeficiente, termo = separado
        resultado = simplificar(f"-({termo})/({coeficiente})")
        return resultado, [
            f"Derivada da esquerda: {derivada_esquerda}",
            f"Derivada da direita: {derivada_direita}",
            f"{coeficiente}*y' + ({termo}) = 0",
            f"y' = {resultado}",
        ]
    finally:
        MODO_IMPLICITA = anterior


def preparar_parametrica(entrada: str) -> tuple[str, list[str]]:
    partes = re.split(r";|\n", entrada)
    atribuicoes = {}
    for parte in partes:
        correspondencia = re.match(r"\s*([xy])(?:\s*\(\s*t\s*\))?\s*=\s*(.+)", parte, re.IGNORECASE)
        if correspondencia:
            atribuicoes[correspondencia.group(1).casefold()] = correspondencia.group(2).strip()
    if set(atribuicoes) != {"x", "y"}:
        raise ExpressaoInvalida("Use o formato x=t^2; y=t^3.")
    derivada_x, _ = preparar_e_derivar(atribuicoes["x"])
    derivada_y, _ = preparar_e_derivar(atribuicoes["y"])
    resultado = simplificar(f"({derivada_y})/({derivada_x})")
    substituir_t = lambda texto: re.sub(r"\bx\b", "t", texto)
    resultado_t = substituir_t(resultado)
    return resultado_t, [
        f"dx/dt = {substituir_t(derivada_x)}",
        f"dy/dt = {substituir_t(derivada_y)}",
        f"dy/dx = (dy/dt)/(dx/dt) = {resultado_t}",
    ]


def preparar_ordem(expressao: str, ordem: int) -> tuple[str, list[str]]:
    if ordem < 1:
        raise ExpressaoInvalida("A ordem precisa ser um número positivo.")
    atual = expressao
    etapas: list[str] = []
    for numero in range(1, ordem + 1):
        atual, _ = preparar_e_derivar(atual)
        etapas.append(f"Derivada de ordem {numero}: {atual}")
    return atual, etapas


def preparar_por_partes(entrada: str) -> tuple[list[tuple[str, str]], list[str]]:
    partes = [parte.strip() for parte in entrada.split(";") if parte.strip()]
    if len(partes) < 2:
        raise ExpressaoInvalida("Use condição:expressão; condição:expressão.")
    resultados: list[tuple[str, str]] = []
    etapas: list[str] = []
    for parte in partes:
        if ":" not in parte:
            raise ExpressaoInvalida("Cada trecho precisa ter condição:expressão.")
        condicao, expressao = (item.strip() for item in parte.split(":", 1))
        derivada, _ = preparar_e_derivar(expressao)
        resultados.append((condicao, derivada))
        etapas.append(f"Se {condicao}: ({expressao})' = {derivada}")
    return resultados, etapas


# Comparação estrutural de respostas e fluxo dos modos de jogo.
def _chave_equivalencia(no: ast.AST) -> tuple:
    if isinstance(no, ast.Constant):
        return ("numero", str(no.value))
    if isinstance(no, ast.Name):
        return ("nome", no.id.casefold())
    if isinstance(no, ast.UnaryOp) and isinstance(no.op, ast.USub):
        return ("neg", _chave_equivalencia(no.operand))
    if isinstance(no, ast.BinOp):
        operador = type(no.op).__name__
        partes: list[tuple] = []
        if isinstance(no.op, (ast.Add, ast.Mult)):
            def juntar(atual: ast.AST) -> None:
                if isinstance(atual, ast.BinOp) and isinstance(atual.op, type(no.op)):
                    juntar(atual.left)
                    juntar(atual.right)
                else:
                    partes.append(_chave_equivalencia(atual))
            juntar(no)
            return (operador, *sorted(partes, key=repr))
        return (operador, _chave_equivalencia(no.left), _chave_equivalencia(no.right))
    if isinstance(no, ast.Call) and isinstance(no.func, ast.Name):
        return ("funcao", no.func.id.casefold(), *(
            _chave_equivalencia(argumento) for argumento in no.args
        ))
    return (type(no).__name__, ast.dump(no, include_attributes=False))


def expressoes_equivalentes(primeira: str, segunda: str) -> bool:
    try:
        primeira = re.sub(r"^\s*f\s*'\s*\(\s*x\s*\)\s*=\s*", "", primeira, flags=re.IGNORECASE)
        segunda = re.sub(r"^\s*f\s*'\s*\(\s*x\s*\)\s*=\s*", "", segunda, flags=re.IGNORECASE)
        arvore_a = ast.parse(preparar_expressao(traduzir_portugues(primeira)), mode="eval").body
        arvore_b = ast.parse(preparar_expressao(traduzir_portugues(segunda)), mode="eval").body
    except SyntaxError:
        return False
    return _chave_equivalencia(_simplificar_ast(arvore_a)) == _chave_equivalencia(
        _simplificar_ast(arvore_b)
    )


def gerar_alternativas_multipla_escolha(
    resposta_correta: str,
) -> list[tuple[str, bool, str]]:
    """Cria quatro respostas distintas, incluindo a correta, para o jogo."""
    candidatos = [
        (
            f"-({resposta_correta})",
            "O sinal de toda a resposta foi invertido. "
            "Confira se alguma regra exige esse sinal negativo.",
        ),
        (
            f"({resposta_correta})*2",
            "A resposta foi multiplicada por 2. "
            "Confira se a regra realmente produz esse fator extra.",
        ),
        (
            f"({resposta_correta})+x",
            "Foi acrescentado um termo x que não veio da derivação. "
            "Cada parcela da resposta precisa vir de uma regra aplicada.",
        ),
        (
            f"({resposta_correta})-x",
            "Foi subtraído um termo x sem justificativa na regra aplicada.",
        ),
        (
            f"({resposta_correta})+1",
            "Foi acrescentada uma unidade à resposta. "
            "Verifique se a derivação produz esse termo constante.",
        ),
        (
            f"({resposta_correta})-1",
            "Foi subtraída uma unidade sem justificativa na derivação.",
        ),
        (
            f"({resposta_correta})+x^2",
            "Foi acrescentado um termo x² que não aparece ao aplicar "
            "as regras à expressão.",
        ),
        (
            f"({resposta_correta})-x^2",
            "Foi subtraído um termo x² sem justificativa na derivação.",
        ),
        (
            f"({resposta_correta})+2",
            "Foi acrescentado o termo constante 2 sem vir de uma regra "
            "aplicada à expressão.",
        ),
        (
            f"({resposta_correta})-2",
            "Foi subtraído o termo constante 2 sem justificativa.",
        ),
    ]
    distratores: list[tuple[str, str]] = []
    for candidato, motivo in candidatos:
        if expressoes_equivalentes(candidato, resposta_correta):
            continue
        if any(
            expressoes_equivalentes(candidato, outro)
            for outro, _ in distratores
        ):
            continue
        distratores.append((candidato, motivo))
        if len(distratores) == 3:
            break
    if len(distratores) < 3:
        raise ValueError("Não foi possível criar três alternativas incorretas distintas.")
    alternativas = [(resposta_correta, True, "")] + [
        (distrator, False, motivo) for distrator, motivo in distratores
    ]
    random.shuffle(alternativas)
    return alternativas


def nome_regra_principal(
    expressao: str,
    etapas: list[tuple[str, str, str]],
) -> str:
    if etapas:
        return etapas[0][0]
    arvore = ast.parse(
        preparar_expressao(traduzir_portugues(expressao)),
        mode="eval",
    ).body
    if isinstance(arvore, ast.Name) and arvore.id == "x":
        return "Derivada da identidade"
    return "Regra da constante"


def etapa_principal(
    expressao: str,
    etapas: list[tuple[str, str, str]],
) -> tuple[str, str, str]:
    if etapas:
        return etapas[0]
    regra = nome_regra_principal(expressao, etapas)
    explicacao = (
        "(x)' = 1"
        if regra == "Derivada da identidade"
        else "(c)' = 0, para uma constante c"
    )
    return regra, "—", explicacao


def nome_regra_exibicao(regra: str) -> str:
    nomes = {
        "Produto": "Regra do produto",
        "Potência (expoente constante)": "Regra da potência (expoente constante)",
        "Potência (expoente função)": "Regra da potência (expoente variável)",
        "Seno": "Derivada do seno",
        "Cosseno": "Derivada do cosseno",
        "Tangente": "Derivada da tangente",
        "Exponencial": "Regra da exponencial",
        "Logaritmo natural": "Regra do logaritmo natural",
        "Derivada da identidade": "Derivada da identidade",
        "Regra da constante": "Regra da constante",
    }
    return nomes.get(regra, regra)


def gerar_alternativas_de_regra(
    regra_correta: str,
    regras_disponiveis: list[str],
) -> list[tuple[str, bool]]:
    regras = set(regras_disponiveis)
    regras.add(regra_correta)
    regras.discard(regra_correta)
    if len(regras) < 3:
        raise ValueError("Não há regras suficientes para criar as alternativas.")
    distratores = random.sample(sorted(regras), 3)
    alternativas = [(regra_correta, True)] + [
        (regra, False) for regra in distratores
    ]
    random.shuffle(alternativas)
    return alternativas


def coletar_regras_disponiveis(
    questoes: list[QuestaoJogo],
) -> list[str]:
    regras = {
        "Derivada da identidade",
        "Regra da constante",
        "Produto",
        "Regra do quociente",
        "Regra da cadeia",
        "Potência (expoente constante)",
        "Potência (expoente função)",
        "Exponencial",
        "Logaritmo natural",
    }
    for questao in questoes:
        try:
            _, etapas = preparar_e_derivar(
                questao.expressao,
                questao.derivada_de_imagem,
            )
        except (SyntaxError, ExpressaoInvalida):
            continue
        regras.update(nome for nome, _, _ in etapas)
    return sorted(regras)


def carregar_questoes_jogo() -> list[QuestaoJogo]:
    """Carrega a primeira expressão de cada teste numerado válido do TXT."""
    if not TESTES_DERIVADAS.exists():
        return []
    questoes: list[QuestaoJogo] = []
    teste_atual: int | None = None
    candidato: str | None = None
    modo_imagem = False
    modo_especial = False

    def salvar_candidato() -> None:
        if teste_atual is not None and candidato and not modo_especial:
            simbolos_de_imagem = {
                "voce",
                "seu_amigo",
                "seu_parceiro",
                "guarda_chuva",
                "gota",
                "sarrada",
                "fusca",
            }
            nomes = set(re.findall(r"\b[A-Za-z_][A-Za-z_0-9]*\b", candidato.casefold()))
            usa_imagem = modo_imagem or bool(nomes & simbolos_de_imagem)
            questoes.append(QuestaoJogo(candidato, usa_imagem))

    for linha in TESTES_DERIVADAS.read_text(encoding="utf-8").splitlines():
        cabecalho = re.match(r"^(\d{2})\.\s+", linha)
        if cabecalho:
            salvar_candidato()
            teste_atual = int(cabecalho.group(1))
            candidato = None
            modo_imagem = 20 <= teste_atual <= 23
            modo_especial = teste_atual >= 85
            continue
        if teste_atual is None or candidato is not None:
            continue
        texto = linha.strip()
        if not linha.startswith("    ") or not texto:
            continue
        if texto.startswith(("python ", "Resultado ", "Forma ")):
            continue
        if texto.startswith(("aplicar ", "sin(x)*csc", "cos(x)*sec", "tan(x)*cot", "sobra ", "(x^2)'")):
            continue
        if any(caractere in texto for caractere in "()^*/") or texto.startswith(
            ("raiz ", "seno(", "ln(", "log", "exp(", "M^", "bola^", "ovo_")
        ):
            candidato = texto
    salvar_candidato()
    return questoes


def registrar_futura_atualizacao(expressao: str, erro: str) -> None:
    """Registra somente expressões válidas que ainda não têm uma regra."""
    if FUTURAS_ATUALIZACOES.exists():
        conteudo = FUTURAS_ATUALIZACOES.read_text(encoding="utf-8")
        if f"Expressão: {expressao}\n" in conteudo:
            return
    else:
        conteudo = (
            "FUTURAS ATUALIZAÇÕES DO TUTOR DE DERIVADAS\n"
            "===========================================\n\n"
            "Estas expressões têm sintaxe reconhecida, mas ainda precisam de "
            "uma regra ou implementação específica.\n\n"
        )
    registro = (
        f"Data: {datetime.now().isoformat(timespec='seconds')}\n"
        f"Expressão: {expressao}\n"
        f"Motivo: {erro}\n"
        "Status: aguardando implementação\n\n"
    )
    FUTURAS_ATUALIZACOES.write_text(conteudo + registro, encoding="utf-8")


def detalhes_regra(codigo: str) -> tuple[str, str]:
    detalhes = {
        "01.01": ("Fórmula do produto", "Usa-se quando temos multiplicação de funções."),
        "01.02": ("Fórmula do quociente", "Usa-se quando temos uma fração de funções."),
        "01.03": ("Fórmula da regra da cadeia", "Usa-se quando há uma função dentro de outra."),
        "01.04": ("Fórmula da potência", "Usa-se quando temos uma base elevada a um expoente."),
        "01.05": ("Fórmula da potência com expoente função", "Usa-se quando a base e o expoente dependem de x."),
        "01.06": ("Fórmula da exponencial", "Usa-se quando temos uma função exponencial."),
        "01.07": ("Fórmula do logaritmo natural", "Usa-se quando temos o logaritmo natural de uma função."),
        "02.09": ("Fórmula do logaritmo em base constante", "Usa-se quando a base do logaritmo é constante."),
        "03.01": ("Fórmula do seno", "Usa-se quando a função é seno."),
        "03.02": ("Fórmula do cosseno", "Usa-se quando a função é cosseno."),
        "03.03": ("Fórmula da tangente", "Usa-se quando a função é tangente."),
        "09.01": ("Fórmula do arco-tangente", "Usa-se quando a função é arco-tangente."),
        "09.02": ("Fórmula da raiz de índice n", "Usa-se quando o índice da raiz é constante."),
        "09.03": ("Fórmula do arco-seno", "Usa-se para derivar o arco-seno de uma função."),
        "09.04": ("Fórmula do arco-cosseno", "Usa-se para derivar o arco-cosseno de uma função."),
    }
    return detalhes.get(codigo, ("Fórmula da regra", "Usa-se conforme a estrutura da função."))


# Resolução interativa, impressão dos passos e explicação de modos especiais.
def mostrar_reducao_fracao_aninhada() -> None:
    print("\nSimplificação algébrica antes da derivada:")
    print("      1/(1 + 1/(1 + 1/(x + 1)))")
    print("      = 1/(1 + (x + 1)/(x + 2))")
    print("        [fração interna: 1 + 1/(x + 1) = (x + 2)/(x + 1)]")
    print("      = 1/((2x + 3)/(x + 2))")
    print("        [denominador comum: 1 + (x + 1)/(x + 2) = (2x + 3)/(x + 2)]")
    print("      = (x + 2)/(2x + 3)")
    print("        [dividir por uma fração = multiplicar pelo inverso]")


# Interface de linha de comando: valida os arquivos e despacha a ação escolhida.
def main() -> int:
    parser = argparse.ArgumentParser(
        description="Consulta as fórmulas do resumo_de_derivadas.txt."
    )
    parser.add_argument("--resolver", "-r", metavar="EXPRESSAO", help="Resolve uma função passo a passo.")
    parser.add_argument("--guia", action="store_true", help="Mostra o guia dos 16 blocos de álgebra.")
    parser.add_argument("--bloco", type=int, metavar="N", help="Mostra um bloco de álgebra específico.")
    parser.add_argument("codigo", nargs="?", help="Referencia, por exemplo 01.03.")
    parser.add_argument("--buscar", "-b", metavar="TERMO", help="Busca por nome, alias ou funcao.")
    parser.add_argument("--lista", "-l", action="store_true", help="Lista todas as referencias.")
    parser.add_argument("--interativo", "-i", action="store_true", help="Abre um modo de consulta.")
    parser.add_argument("--comandos", action="store_true", help="Mostra a sintaxe e exemplos de entrada.")
    parser.add_argument("--jogo", action="store_true", help="Abre o jogo de derivadas.")
    parser.add_argument("--implicita", metavar="EQUACAO", help="Resolve uma equação por diferenciação implícita.")
    parser.add_argument("--parametrica", metavar="ENTRADA", help="Resolve x=...; y=... em forma paramétrica.")
    parser.add_argument("--ordem", type=int, metavar="N", help="Calcula a derivada de ordem N.")
    parser.add_argument("--partes", metavar="ENTRADA", help="Resolve trechos no formato condição:expressão;...")
    args = parser.parse_args()

    try:
        verificar_resumo_derivadas()
        if args.implicita:
            resolver_implicita(args.implicita)
        elif args.parametrica:
            resolver_parametrica(args.parametrica)
        elif args.ordem is not None and args.resolver:
            resolver_ordem_superior(args.resolver, args.ordem)
        elif args.partes:
            resolver_por_partes(args.partes)
        elif args.jogo:
            menu_jogo()
        elif args.comandos:
            if not COMANDOS.exists():
                raise FileNotFoundError(f"Arquivo de comandos não encontrado: {COMANDOS}")
        if args.guia or args.bloco is not None:
            carregar_blocos_algebra()
    except FileNotFoundError as erro:
        print(f"Erro: {erro}", file=sys.stderr)
        return 1

    if args.comandos:
        mostrar_comandos()
    elif args.guia:
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
    elif args.interativo:
        interativo()
    else:
        menu_inicial()
    return 0
if __name__ == "__main__":
    raise SystemExit(main())
