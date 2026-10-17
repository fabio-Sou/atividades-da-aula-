# Guia de derivadas

O arquivo `Cálculo1.pdf` é o guia visual das fórmulas. O script
`guia_derivadas.py` funciona como um tutor: recebe uma função, identifica as
regras necessárias, resolve por etapas e pergunta se você quer ver a fórmula
e exemplos simples e complexos em cada etapa.

## Como usar

Abra um terminal nesta pasta e execute:

```text
python guia_derivadas.py --resolver "sin(x^2)"
python guia_derivadas.py --resolver "(x^3 * exp(x)) / ln(x)"
python guia_derivadas.py --guia
python guia_derivadas.py --bloco 13
python guia_derivadas.py
python guia_derivadas.py 01.03
python guia_derivadas.py --buscar cadeia
python guia_derivadas.py --lista
python guia_derivadas.py --interativo
```

No modo interativo, digite uma função como `sin(x^2)`. O tutor mostrará cada
passo e perguntará:

```text
Quer ver a fórmula usada e como aplicar? (S/N)
```

Cada passo mostra primeiro somente a transformação aplicada à expressão. A
fórmula geral, a explicação e os exemplos da regra aparecem apenas quando a
resposta for `S`.

Também é possível digitar `guia` para ver os 16 blocos de álgebra, `bloco 13`
para abrir um bloco específico, um código do PDF (`01.03`), `lista` ou `sair`.

## Organização do material de álgebra

O arquivo `formulas_basicas_algebra.txt` usa um sistema de coordenadas, como
uma batalha naval: o primeiro número indica o bloco e o segundo indica a
subseção dentro dele. Assim, `16.01` significa “bloco 16, primeira etapa do
roteiro”. O guia serve para bater o olho e descobrir qual coordenada usar.
Na seção detalhada, o bloco já aparece no título (`6. FATORAÇÃO`), por isso
as subseções aparecem somente como `01`, `02` e `03`; isso evita repetir o
número do bloco.

São 16 blocos, com subseções que correspondem às ideias reais do conteúdo
detalhado. Descrições aparecem somente quando o título não é suficiente para
explicar rapidamente um conceito mais abstrato:

1. Operações e ordem de resolução
2. Propriedades da soma e da subtração
3. Propriedades da multiplicação e da divisão
4. Termos algébricos e redução
5. Produtos notáveis
6. Fatoração
7. Potências
8. Raízes
9. Frações
10. Frações aninhadas
11. Equações do primeiro grau
12. Equações do segundo grau
13. Funções e composição
14. Logaritmos
15. Regras usadas como base para derivadas
16. Roteiro para simplificar uma expressão

Os blocos 1 a 14 formam a base algébrica e conceitual. O bloco 15 conecta
essa base às regras de derivação, e o bloco 16 funciona como roteiro prático
de preparação da expressão antes de derivá-la. No bloco 16, por exemplo, há
sete etapas reais (`16.01` a `16.07`), iguais às sete etapas numeradas na
seção detalhada.

O resolvedor aceita `x`, números, `+`, `-`, `*`, `/`, `^`, expoentes
racionais constantes, `sqrt`, `sin`, `cos`, `tan`, `exp`, `e^...`, a
constante matemática `e` em expressões como `x^e` e `ln`.
Por exemplo:

```text
python guia_derivadas.py --resolver "f(x) = sin(x^2)"
python guia_derivadas.py --resolver "sqrt(3*x+1)"
python guia_derivadas.py --resolver "(3*x^2+6*x-1)^(2/3)"
python guia_derivadas.py --resolver "1/(1+1/(1+1/(x+1)))"
```

As expressões intermediárias passam por uma simplificação algébrica segura,
que remove fatores nulos ou unitários e reduz operações simples sem substituir
as etapas didáticas pelas fórmulas de uma biblioteca externa.

A fração aninhada do exemplo acima é reconhecida e apresentada como
`(x+2)/(2x+3)`, cuja derivada é exibida como `1/(2x+3)^2`.

As propriedades algébricas usadas antes da derivação estão reunidas em
`formulas_basicas_algebra.txt`, incluindo operações com frações, potências,
raízes, produtos notáveis, fatoração, composição e regras básicas de
derivação.

Os códigos seguem o índice do PDF:

- `01.01` a `01.07`: principais regras;
- `02.01` a `02.09`: kit básico de derivadas;
- `03.01` a `03.06`: derivadas trigonométricas;
- `04.01` a `04.06`: derivadas hiperbólicas;
- `05.01` a `05.06`: definições trigonométricas;
- `06.01` a `06.06`: derivadas trigonométricas organizadas;
- `07.01` a `07.06`: definições hiperbólicas;
- `08.01` a `08.06`: derivadas hiperbólicas organizadas.

O script confirma que o PDF está na mesma pasta antes de iniciar, para
evitar consultas fora do material de referência.
