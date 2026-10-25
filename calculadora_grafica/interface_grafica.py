"""Interface gráfica da calculadora científica."""

import tkinter as tk
from tkinter import ttk

from calculadora import calcular


class CalculadoraGrafica:
    def __init__(self, janela: tk.Tk) -> None:
        self.janela = janela
        self.janela.title("Calculadora científica")
        self.janela.geometry("430x620")
        self.janela.minsize(360, 520)

        self.expressao = tk.StringVar()
        self.modo_angulo = tk.StringVar(value="Graus")
        self.mensagem = tk.StringVar(value="Digite uma expressão ou use os botões.")

        self._criar_interface()
        self.janela.bind("<Return>", self._calcular)
        self.janela.bind("<Escape>", self._limpar)

    def _criar_interface(self) -> None:
        estilo = ttk.Style()
        if "clam" in estilo.theme_names():
            estilo.theme_use("clam")

        principal = ttk.Frame(self.janela, padding=16)
        principal.grid(row=0, column=0, sticky="nsew")
        self.janela.grid_rowconfigure(0, weight=1)
        self.janela.grid_columnconfigure(0, weight=1)
        principal.grid_columnconfigure(0, weight=1)
        principal.grid_rowconfigure(4, weight=1)

        ttk.Label(
            principal,
            text="Calculadora científica",
            font=("Segoe UI", 20, "bold"),
        ).grid(row=0, column=0, sticky="w", pady=(0, 12))

        tela = ttk.Entry(
            principal,
            textvariable=self.expressao,
            font=("Segoe UI", 20),
            justify="right",
        )
        tela.grid(row=1, column=0, sticky="ew", ipady=10, pady=(0, 8))
        tela.focus_set()
        self.tela = tela

        ttk.Label(
            principal,
            textvariable=self.mensagem,
            wraplength=380,
        ).grid(row=2, column=0, sticky="w", pady=(0, 8))

        angulos = ttk.Frame(principal)
        angulos.grid(row=3, column=0, sticky="w", pady=(0, 10))
        ttk.Label(angulos, text="Ângulos:").pack(side="left", padx=(0, 8))
        ttk.Radiobutton(
            angulos,
            text="Graus",
            value="Graus",
            variable=self.modo_angulo,
        ).pack(side="left")
        ttk.Radiobutton(
            angulos,
            text="Radianos",
            value="Radianos",
            variable=self.modo_angulo,
        ).pack(side="left", padx=(8, 0))

        botoes = [
            ["sin(", "cos(", "tan(", "sqrt("],
            ["asin(", "acos(", "atan(", "ln("],
            ["log(", "abs(", "pi", "e"],
            ["(", ")", "^", "÷"],
            ["7", "8", "9", "×"],
            ["4", "5", "6", "−"],
            ["1", "2", "3", "+"],
            ["±", "0", ",", "="],
            ["Limpar", "⌫"],
        ]
        grade = ttk.Frame(principal)
        grade.grid(row=4, column=0, sticky="nsew")
        for coluna in range(4):
            grade.grid_columnconfigure(coluna, weight=1, uniform="botao")
        for linha, itens in enumerate(botoes):
            grade.grid_rowconfigure(linha, weight=1, uniform="linha")
            coluna = 0
            for texto in itens:
                if texto == "Limpar":
                    comando = self._limpar
                    coluna_span = 2
                elif texto == "⌫":
                    comando = self._apagar
                    coluna_span = 2
                elif texto == "=":
                    comando = self._calcular
                    coluna_span = 1
                elif texto == "±":
                    comando = self._alternar_sinal
                    coluna_span = 1
                else:
                    comando = lambda valor=texto: self._inserir(valor)
                    coluna_span = 1
                botao = ttk.Button(grade, text=texto, command=comando)
                botao.grid(
                    row=linha,
                    column=coluna,
                    columnspan=coluna_span,
                    sticky="nsew",
                    padx=3,
                    pady=3,
                )
                coluna += coluna_span

        ttk.Label(
            principal,
            text="Exemplos: 2^3 + sqrt(16)   |   sin(30) em graus",
            foreground="#555555",
        ).grid(row=5, column=0, sticky="w", pady=(10, 0))

    def _inserir(self, texto: str) -> None:
        substitutos = {"÷": "/", "×": "*", "−": "-", ",": "."}
        self.expressao.set(self.expressao.get() + substitutos.get(texto, texto))
        self.mensagem.set("Digite uma expressão ou use os botões.")
        self.tela.focus_set()

    def _limpar(self, evento: tk.Event | None = None) -> str:
        self.expressao.set("")
        self.mensagem.set("Digite uma expressão ou use os botões.")
        self.tela.focus_set()
        return "break"

    def _apagar(self) -> None:
        self.expressao.set(self.expressao.get()[:-1])
        self.tela.focus_set()

    def _alternar_sinal(self) -> None:
        expressao = self.expressao.get().strip()
        if not expressao:
            self.expressao.set("-")
        elif expressao.startswith("-(") and expressao.endswith(")"):
            self.expressao.set(expressao[2:-1])
        else:
            self.expressao.set(f"-({expressao})")
        self.tela.focus_set()

    def _calcular(self, evento: tk.Event | None = None) -> str:
        try:
            resultado = calcular(
                self.expressao.get(),
                graus=self.modo_angulo.get() == "Graus",
            )
        except (ValueError, OverflowError) as erro:
            self.mensagem.set(str(erro))
            self.tela.focus_set()
            return "break"
        self.expressao.set(f"{resultado:.12g}")
        self.mensagem.set("Resultado")
        self.tela.focus_set()
        return "break"


def main() -> None:
    janela = tk.Tk()
    CalculadoraGrafica(janela)
    janela.mainloop()


if __name__ == "__main__":
    main()
