"""Interface gráfica opcional do tutor de derivadas."""

try:
    import customtkinter as ctk
except ModuleNotFoundError as erro:
    if erro.name != "customtkinter":
        raise
    raise SystemExit(
        "A interface gráfica precisa do CustomTkinter. "
        "Instale com: python -m pip install -r requirements-gui.txt"
    ) from erro

try:
    from matplotlib import mathtext
    from matplotlib.font_manager import FontProperties
    from PIL import Image
except ModuleNotFoundError as erro:
    if erro.name not in {"matplotlib", "PIL"}:
        raise
    raise SystemExit(
        "A renderização matemática precisa do Matplotlib e do Pillow. "
        "Instale com: python -m pip install -r requirements-gui.txt"
    ) from erro

from io import BytesIO
import re
import tkinter as tk

import guia_derivadas as tutor


def _converter_chamadas(texto: str) -> str:
    comandos = {
        "sin": r"\sin",
        "cos": r"\cos",
        "tan": r"\tan",
        "cot": r"\cot",
        "sec": r"\sec",
        "csc": r"\csc",
        "arcsin": r"\mathrm{arcsin}",
        "arccos": r"\mathrm{arccos}",
        "arctan": r"\mathrm{arctan}",
        "arccot": r"\mathrm{arccot}",
        "arcsec": r"\mathrm{arcsec}",
        "arccsc": r"\mathrm{arccsc}",
        "sinh": r"\mathrm{sinh}",
        "cosh": r"\mathrm{cosh}",
        "tanh": r"\mathrm{tanh}",
        "coth": r"\mathrm{coth}",
        "sech": r"\mathrm{sech}",
        "csch": r"\mathrm{csch}",
        "asinh": r"\mathrm{asinh}",
        "acosh": r"\mathrm{acosh}",
        "atanh": r"\mathrm{atanh}",
        "acoth": r"\mathrm{acoth}",
        "asech": r"\mathrm{asech}",
        "acsch": r"\mathrm{acsch}",
        "ln": r"\ln",
        "log": r"\log",
        "exp": r"\mathrm{exp}",
    }
    partes: list[str] = []
    indice = 0
    while indice < len(texto):
        chamada = re.match(r"([A-Za-z]+\d*)\s*\(", texto[indice:])
        if chamada is None:
            partes.append(texto[indice])
            indice += 1
            continue

        nome = chamada.group(1).casefold()
        inicio_argumentos = indice + chamada.end()
        profundidade = 1
        fim_argumentos = inicio_argumentos
        while fim_argumentos < len(texto) and profundidade:
            caractere = texto[fim_argumentos]
            if caractere == "(":
                profundidade += 1
            elif caractere == ")":
                profundidade -= 1
            fim_argumentos += 1
        if profundidade:
            partes.append(texto[indice])
            indice += 1
            continue

        argumentos = texto[inicio_argumentos : fim_argumentos - 1]
        argumentos_tex = _converter_chamadas(argumentos)
        if nome == "sqrt":
            partes.append(r"\sqrt{" + argumentos_tex + "}")
        elif nome == "root" or re.fullmatch(r"root\d+", nome):
            if nome == "root":
                indice_raiz, separador, radicando = argumentos.partition(",")
            else:
                indice_raiz, separador, radicando = nome[4:], ",", argumentos
            if separador:
                partes.append(
                    r"\sqrt["
                    + indice_raiz.strip()
                    + "]{"
                    + _converter_chamadas(radicando.strip())
                    + "}"
                )
            else:
                partes.append("root(" + argumentos_tex + ")")
        elif nome == "abs":
            partes.append(r"\left|" + argumentos_tex + r"\right|")
        elif nome in comandos:
            partes.append(
                comandos[nome] + r"\left(" + argumentos_tex + r"\right)"
            )
        else:
            partes.append(
                chamada.group(1)
                + "("
                + argumentos_tex
                + ")"
            )
        indice = fim_argumentos
    return "".join(partes)


def _mathtext(expressao: str) -> str:
    """Converte a notação do tutor para o subconjunto matemático do Matplotlib."""
    superscritos = str.maketrans(
        {
            "⁰": "0",
            "¹": "1",
            "²": "2",
            "³": "3",
            "⁴": "4",
            "⁵": "5",
            "⁶": "6",
            "⁷": "7",
            "⁸": "8",
            "⁹": "9",
        }
    )
    texto = re.sub(
        r"[⁰¹²³⁴⁵⁶⁷⁸⁹]+",
        lambda match: "^{" + match.group().translate(superscritos) + "}",
        expressao,
    )
    texto = re.sub(
        r"(?<=[A-Za-z)])'",
        lambda _: r"^{\prime}",
        texto,
    )
    texto = re.sub(
        r"\bsqrt\s+([A-Za-z0-9]+)",
        lambda match: r"\sqrt{" + match.group(1) + "}",
        texto,
    )
    texto = re.sub(r"\s*\*\s*", r" \\cdot ", texto)
    texto = _converter_potencias(texto)
    texto = re.sub(r"\bpi\b", r"\\pi", texto)
    texto = _converter_chamadas(texto)
    return _converter_potencias(texto)


def _converter_potencias(texto: str) -> str:
    def ler_atom(inicio: int) -> tuple[str, int]:
        while inicio < len(texto) and texto[inicio].isspace():
            inicio += 1
        if inicio >= len(texto):
            return "", inicio
        if texto[inicio] == "(":
            profundidade = 1
            fim = inicio + 1
            while fim < len(texto) and profundidade:
                if texto[fim] == "(":
                    profundidade += 1
                elif texto[fim] == ")":
                    profundidade -= 1
                fim += 1
            if profundidade == 0:
                return _converter_potencias(texto[inicio + 1 : fim - 1]), fim
        if texto[inicio] == "{":
            profundidade = 1
            fim = inicio + 1
            while fim < len(texto) and profundidade:
                if texto[fim] == "{":
                    profundidade += 1
                elif texto[fim] == "}":
                    profundidade -= 1
                fim += 1
            if profundidade == 0:
                return _converter_potencias(texto[inicio + 1 : fim - 1]), fim
        if texto[inicio] in "+-":
            inicio += 1
        fim = inicio
        while fim < len(texto) and texto[fim].isalnum():
            fim += 1
        if fim == inicio:
            return texto[inicio : inicio + 1], inicio + 1
        if fim < len(texto) and texto[fim] == "(":
            profundidade = 1
            end_call = fim + 1
            while end_call < len(texto) and profundidade:
                if texto[end_call] == "(":
                    profundidade += 1
                elif texto[end_call] == ")":
                    profundidade -= 1
                end_call += 1
            if profundidade == 0:
                fim = end_call
                atom = texto[inicio:fim]
                return (
                    atom[: atom.index("(") + 1]
                    + _converter_potencias(atom[atom.index("(") + 1 : -1])
                    + ")",
                    fim,
                )
        while fim < len(texto) and texto[fim] == "^" and fim + 1 < len(texto):
            if texto[fim + 1] != "{":
                break
            profundidade = 1
            end_power = fim + 2
            while end_power < len(texto) and profundidade:
                if texto[end_power] == "{":
                    profundidade += 1
                elif texto[end_power] == "}":
                    profundidade -= 1
                end_power += 1
            if profundidade:
                break
            fim = end_power
        return texto[inicio:fim], fim

    def ler_expoente(inicio: int) -> tuple[str, int]:
        atom, fim = ler_atom(inicio)
        if not atom:
            return atom, fim
        depois = fim
        while depois < len(texto) and texto[depois].isspace():
            depois += 1
        if depois < len(texto) and texto[depois] == "^":
            proximo, fim_proximo = ler_expoente(depois + 1)
            return _anexar_expoente(atom, proximo), fim_proximo
        return atom, fim

    partes: list[str] = []
    indice = 0
    while indice < len(texto):
        if texto[indice] != "^":
            partes.append(texto[indice])
            indice += 1
            continue

        if indice + 1 < len(texto) and texto[indice + 1] == "{":
            partes.append("^")
            indice += 1
            continue
        expoente, fim = ler_expoente(indice + 1)
        if fim == indice + 1:
            partes.append("^")
            indice += 1
            continue
        partes.append("^{" + expoente + "}")
        indice = fim
    return "".join(partes)


def _anexar_expoente(atom: str, proximo: str) -> str:
    if atom.endswith("}"):
        profundidade = 0
        inicio = len(atom) - 1
        while inicio >= 0:
            if atom[inicio] == "}":
                profundidade += 1
            elif atom[inicio] == "{":
                profundidade -= 1
                if profundidade == 0:
                    break
            inicio -= 1
        if inicio > 0 and atom[inicio - 1] == "^":
            expoente = atom[inicio + 1 : -1]
            return (
                atom[: inicio - 1]
                + "^{"
                + _anexar_expoente(expoente, proximo)
                + "}"
            )
    return atom + "^{" + proximo + "}"


class TutorGrafico(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Tutor de Derivadas")
        self.geometry("960x760")
        self.minsize(720, 580)

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        cabecalho = ctk.CTkFrame(self, fg_color="transparent")
        cabecalho.grid(row=0, column=0, sticky="ew", padx=32, pady=(28, 18))
        ctk.CTkLabel(
            cabecalho,
            text="Tutor de Derivadas",
            font=ctk.CTkFont(size=30, weight="bold"),
        ).pack(anchor="w")
        ctk.CTkLabel(
            cabecalho,
            text="Digite uma função e acompanhe a resolução passo a passo.",
            font=ctk.CTkFont(size=14),
            text_color=("gray35", "gray70"),
        ).pack(anchor="w", pady=(4, 0))

        entrada_card = ctk.CTkFrame(self, corner_radius=16)
        entrada_card.grid(row=1, column=0, sticky="ew", padx=32, pady=(0, 18))
        entrada_card.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            entrada_card,
            text="Função para derivar",
            font=ctk.CTkFont(size=15, weight="bold"),
        ).grid(row=0, column=0, columnspan=2, sticky="w", padx=20, pady=(18, 8))

        self.entrada = ctk.CTkEntry(
            entrada_card,
            placeholder_text="Exemplo: sin(x^2)",
            height=44,
            font=ctk.CTkFont(size=16),
        )
        self.entrada.grid(
            row=1,
            column=0,
            sticky="ew",
            padx=(20, 10),
            pady=(0, 12),
        )
        self.entrada.bind("<Return>", self._ao_pressionar_enter)

        self.botao_derivar = ctk.CTkButton(
            entrada_card,
            text="Derivar",
            command=self.derivar,
            height=44,
            width=130,
            font=ctk.CTkFont(size=15, weight="bold"),
        )
        self.botao_derivar.grid(
            row=1,
            column=1,
            sticky="e",
            padx=(0, 20),
            pady=(0, 12),
        )

        self.modo_imagem = tk.BooleanVar(master=self, value=False)
        ctk.CTkCheckBox(
            entrada_card,
            text="Modo imagem: considerar letras além de x como funções de x",
            variable=self.modo_imagem,
            font=ctk.CTkFont(size=13),
        ).grid(row=2, column=0, columnspan=2, sticky="w", padx=20, pady=(0, 8))

        self.status = ctk.CTkLabel(
            entrada_card,
            text="Aceita x^2, sin(x), 3x^2 e outras expressões do tutor.",
            anchor="w",
            text_color=("gray35", "gray70"),
        )
        self.status.grid(
            row=3,
            column=0,
            columnspan=2,
            sticky="ew",
            padx=20,
            pady=(0, 16),
        )

        resultado_card = ctk.CTkFrame(self, corner_radius=16)
        resultado_card.grid(
            row=2,
            column=0,
            sticky="nsew",
            padx=32,
            pady=(0, 28),
        )
        resultado_card.grid_columnconfigure(0, weight=1)
        resultado_card.grid_rowconfigure(1, weight=1)
        ctk.CTkLabel(
            resultado_card,
            text="Resolução",
            font=ctk.CTkFont(size=17, weight="bold"),
        ).grid(row=0, column=0, sticky="w", padx=20, pady=(18, 10))

        self.resultado = ctk.CTkScrollableFrame(
            resultado_card,
            corner_radius=10,
        )
        self.resultado.grid(
            row=1,
            column=0,
            sticky="nsew",
            padx=20,
            pady=(0, 20),
        )
        self._imagens: list[ctk.CTkImage] = []
        self._mostrar_texto(
            "A resolução aparecerá aqui.\n\n"
            "O tutor mostrará as regras reconhecidas, as transformações "
            "e o resultado final."
        )
        self.entrada.focus_set()

    def _ao_pressionar_enter(self, evento: object) -> str:
        if getattr(evento, "keysym", None) == "Return":
            self.derivar()
        return "break"

    def _mostrar_texto(self, texto: str) -> None:
        self._limpar_resultado()
        for linha in texto.splitlines():
            ctk.CTkLabel(
                self.resultado,
                text=linha or " ",
                anchor="w",
                justify="left",
                wraplength=760,
                font=ctk.CTkFont(size=14),
            ).pack(fill="x", padx=14, pady=2)

    def _limpar_resultado(self) -> None:
        for widget in self.resultado.winfo_children():
            widget.destroy()
        self._imagens.clear()

    def _adicionar_texto(self, texto: str, *, destaque: bool = False) -> None:
        ctk.CTkLabel(
            self.resultado,
            text=texto,
            anchor="w",
            justify="left",
            wraplength=760,
            font=ctk.CTkFont(
                size=15 if destaque else 14,
                weight="bold" if destaque else "normal",
            ),
        ).pack(fill="x", padx=14, pady=(10 if destaque else 3, 3))

    def _adicionar_formula(self, expressao: str) -> None:
        buffer = BytesIO()
        try:
            mathtext.math_to_image(
                f"${_mathtext(expressao)}$",
                buffer,
                dpi=120,
                format="png",
                prop=FontProperties(size=16),
                color="#172033",
            )
        except ValueError as erro:
            self._adicionar_texto(
                f"Não foi possível renderizar esta fórmula; exibindo o texto "
                f"original. Detalhe: {erro}"
            )
            self._adicionar_texto(expressao)
            return
        buffer.seek(0)
        with Image.open(buffer) as imagem_aberta:
            imagem = imagem_aberta.convert("RGBA")
        largura_maxima = max(440, self.winfo_width() - 150)
        if imagem.width > largura_maxima:
            altura = round(imagem.height * largura_maxima / imagem.width)
            imagem = imagem.resize(
                (largura_maxima, altura),
                Image.Resampling.LANCZOS,
            )
        imagem_ctk = ctk.CTkImage(
            light_image=imagem,
            dark_image=imagem,
            size=imagem.size,
        )
        self._imagens.append(imagem_ctk)
        ctk.CTkLabel(
            self.resultado,
            text="",
            image=imagem_ctk,
            anchor="w",
            fg_color=("white", "gray95"),
            corner_radius=8,
        ).pack(anchor="w", padx=14, pady=4)

    def derivar(self) -> None:
        expressao = self.entrada.get().strip()
        if not expressao:
            self.status.configure(
                text="Digite uma função antes de pedir a derivada.",
                text_color=("#b42318", "#ff7b72"),
            )
            self.entrada.focus_set()
            return

        try:
            resultado, etapas = tutor.preparar_e_derivar(
                expressao,
                derivada_de_imagem=self.modo_imagem.get(),
            )
        except SyntaxError:
            self.status.configure(
                text="Não consegui interpretar essa expressão.",
                text_color=("#b42318", "#ff7b72"),
            )
            self._mostrar_texto(
                "Não consegui interpretar essa expressão.\n\n"
                "Exemplos aceitos: sin(x^2), (x^3 * exp(x)) / ln(x)"
            )
            return
        except tutor.ExpressaoInvalida as erro:
            self.status.configure(
                text="A expressão foi reconhecida, mas ainda não é resolvida pelo tutor.",
                text_color=("#b42318", "#ff7b72"),
            )
            self._mostrar_texto(f"Limitação do tutor:\n{erro}")
            return

        self._limpar_resultado()
        self._adicionar_texto("Função informada", destaque=True)
        self._adicionar_formula(f"f(x) = {expressao}")
        if re.search(r"\be\s*\^|\bexp\s*\(", expressao, re.IGNORECASE):
            self._adicionar_texto("Notação: exp(u) significa e^u.")
        for numero, (nome, codigo, explicacao) in enumerate(etapas, 1):
            self._adicionar_texto(
                f"Passo {numero}: {nome} ({codigo})",
                destaque=True,
            )
            self._adicionar_formula(explicacao)
        self._adicionar_texto("Resultado final", destaque=True)
        self._adicionar_formula(
            f"f'(x) = {tutor.formatar_resultado(resultado)}"
        )
        self.status.configure(
            text=f"Derivada calculada com {len(etapas)} etapa(s).",
            text_color=("#16794b", "#5bd39b"),
        )


def main() -> None:
    ctk.set_appearance_mode("system")
    ctk.set_default_color_theme("blue")
    app = TutorGrafico()
    app.mainloop()


if __name__ == "__main__":
    main()
