# Guia de derivadas

O arquivo `resumo_de_derivadas.txt` é a fonte textual das fórmulas. O script
`guia_derivadas.py` funciona como um tutor: recebe uma função, identifica as
regras necessárias, resolve por etapas e pergunta se você quer ver a fórmula
e exemplos simples e complexos em cada etapa.

O resumo também contém um catálogo ampliado de cálculo diferencial para
referência e futuras extensões: regras gerais, funções trigonométricas e
inversas, funções hiperbólicas e inversas, diferenciação implícita e
paramétrica, derivadas de ordem superior, várias variáveis e algumas funções
especiais. Estar registrado no resumo não significa que cada função já esteja
aceita pelo parser.

Para os assuntos que ainda não fazem parte do tutor, há também o arquivo
`estudos_futuros_calculo.txt`. Ele explica brevemente cada tema e traz dois
exemplos por função ou categoria, sem colocá-los automaticamente no jogo.

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
python guia_derivadas.py --comandos
python guia_derivadas.py --jogo
python guia_derivadas.py --implicita "x^2+y^2=1"
python guia_derivadas.py --parametrica "x=t^2; y=t^3"
python guia_derivadas.py --ordem 2 --resolver "x^4"
python guia_derivadas.py --partes "x>0:x; x<0:-x"
```

Sem argumentos, o programa abre um menu inicial compacto. A opção **Tutor
completo** reúne a derivação passo a passo, a derivada de imagem e as
derivadas de ordem superior. A opção **Guia geral** reúne comandos, lista de
regras e guia de álgebra. A opção **Tópicos avançados** reúne diferenciação
implícita, equações paramétricas, valor absoluto e funções por partes.
Também é possível usar `--interativo` para entrar diretamente no tutor.

No Tutor completo, a derivação comum continua sendo o caminho principal. A
ordem superior precisa ser escolhida explicitamente porque uma expressão como
`x^4` não informa se o usuário quer a primeira, segunda ou terceira derivada.
O modo de imagem também permanece explícito porque, no modo normal, letras
diferentes de `x` são constantes; assim o programa não pode adivinhar com
segurança se `M^H` representa constantes ou símbolos dependentes de `x`.

No modo interativo, digite uma função como `sin(x^2)`. A multiplicação
implícita comum da matemática também é aceita, como `3x^2`, `2sin(x)` e
`4(x+1)`. O tutor mostrará cada
passo e perguntará:

```text
Quer ver a fórmula usada e como aplicar? (S/N)
```

Cada passo mostra primeiro somente a transformação aplicada à expressão. A
fórmula geral, a explicação e os exemplos da regra aparecem apenas quando a
resposta for `S`.

As fórmulas, exemplos e resultados são exibidos em blocos separados, com
recuo e espaçamento entre as seções. Expressões longas são quebradas em mais
de uma linha sem cortar palavras, para facilitar a leitura no terminal.

Ao resolver uma expressão, o tutor preserva três referências visuais:

1. a equação exatamente como foi digitada;
2. a forma que o parser interpretou;
3. qualquer simplificação algébrica feita antes da derivação.

Por exemplo, em `x^2*3x^2`, ele mostra a transformação `x² * 3x² =
3x⁴` antes de aplicar a regra do produto. Assim, a forma reduzida nunca
aparece sem explicar de onde veio.

## Limpeza da tela e modo desenvolvedor

No modo normal, o programa limpa a tela somente ao trocar de contexto: ao
abrir um menu, iniciar uma nova questão ou começar uma nova expressão. A
conversa do tutor não é apagada enquanto uma expressão está sendo resolvida;
assim, os passos, fórmulas e resultado permanecem visíveis juntos.

Na tela inicial, digite `desenvolvedor` para alternar o modo desenvolvedor.
Nesse modo nenhuma limpeza automática é feita, permitindo acompanhar todo o
histórico do terminal e investigar possíveis erros. Digite `desenvolvedor`
novamente na tela inicial para desativá-lo.

Depois que todas as regras são aplicadas, o tutor mostra o resultado obtido.
Se ainda existir uma redução algébrica segura, ele avisa que a expressão pode
ser simplificada e pergunta se você quer ver cada transformação. Assim, a
simplificação nunca substitui os passos da derivação:

```text
Resultado obtido pela aplicação das regras:
      f'(x) = 1 / (2 * sqrt(x)) / sqrt(x)

A derivada ainda pode ser simplificada algebricamente sem mudar o resultado.
Quer ver cada passo dessa simplificação? (S/N)
> S

Simplificação 1:
      1 / (2 * sqrt(x)) / sqrt(x)
      = 1 / (2 * x)

Resultado final:
      f'(x) = 1 / (2 * x)
```

Quando não há uma redução segura conhecida, o programa informa que a forma
final já está simplificada pelo tutor. Ele não usa uma biblioteca externa para
cancelar etapas ou esconder transformações.

O tutor também procura formas alternativas antes de começar a derivada. Em um
produto como:

```text
sin(x) * cos(x) * tan(x) * cot(x) * sec(x) * csc(x) * x^2
```

ele reconhece os pares recíprocos:

```text
sin(x) * csc(x) = 1
cos(x) * sec(x) = 1
tan(x) * cot(x) = 1
```

e pergunta se você quer usar o atalho. Se aceitar, a expressão vira `x^2` e
o programa deriva essa forma mais simples. Se recusar, ele mantém a
expressão original e aplica a regra do produto, mostrando a resolução longa.
Assim, o aluno pode comparar a resolução fácil, a moderada e a completa.

Na simplificação algébrica, o tutor também combina fatores seguros que têm a
mesma base:

```text
x^5 * x       -> x^6
x^2 * x^3     -> x^5
2*x * 3*x^2   -> 6*x^3
(1/x)*x^(1/2) -> x^(-1/2)
```

Isso usa `x^a*x^b = x^(a+b)` e `1/x = x^(-1)` somente quando a base é
realmente a mesma. Quando essa redução ocorre depois da aplicação das regras,
ela é apresentada como uma etapa separada de simplificação; ela não substitui
as regras de derivação nem as perguntas sobre as fórmulas.

Também é possível digitar `guia` para ver os 16 blocos de álgebra, `bloco 13`
para abrir um bloco específico, um código do resumo (`01.03`), `lista` ou
`imagem` para abrir o modo de derivada de imagem, ou `sair`. O arquivo
`comandos_derivadas.txt` contém a lista completa da sintaxe.

As expressões usadas para testar o tutor estão reunidas em
`testes_derivadas.txt`. O arquivo contém atualmente 88 entradas numeradas.
O jogo carrega 84 questões compatíveis com o modo normal, incluindo testes de
derivada de imagem, potências com expoentes variáveis, raízes, logaritmos,
simplificações algébricas e as novas funções implementadas. As quatro
entradas especiais restantes são apenas exemplos de diferenciação implícita,
paramétrica, ordem superior e funções por partes; elas ficam fora do sorteio e
devem ser executadas pelos comandos indicados no próprio arquivo.

Além do modo comum, o tutor aceita diferenciação implícita, equações
paramétricas, derivadas de ordem superior e funções por partes. Esses recursos
podem ser chamados pelos argumentos mostrados acima ou pelos comandos
correspondentes no modo interativo. Em equações paramétricas, a variável
apresentada no resultado é `t`, mesmo que o cálculo interno reutilize o
derivador principal baseado em `x`.

## Jogo de derivadas

O menu inicial inclui o **Jogo de derivadas**. Ele possui três modos:

1. **Treino**: permite pedir uma dica antes de responder;
2. **Desafio**: não oferece dica automática e contabiliza as tentativas;
3. **Tutor**: abre a resolução passo a passo junto com o aluno.

Também é possível abrir o jogo diretamente com:

```text
python guia_derivadas.py --jogo
```

Durante qualquer rodada do jogo, digite `sair` para interromper a questão,
a resolução ou a pergunta de continuação e retornar diretamente à tela
principal. No menu do jogo, `sair` também retorna à tela principal.

O jogo lê automaticamente as expressões numeradas de
`testes_derivadas.txt`. Assim, ao adicionar um novo teste válido ao arquivo,
ele poderá ser usado pelo jogo sem alterar a lista no código. O bloco de
entradas inválidas não entra no sorteio. Os testes 20 a 23 são marcados como
questões de derivada de imagem.

O jogo aceita respostas equivalentes. Por exemplo, estas duas formas são
consideradas iguais:

```text
2*x*cos(x^2)
cos(x^2)*2*x
```

O programa organiza os fatores e ignora diferenças de parênteses que não
alterem a expressão. A comparação ainda é conservadora: ela não afirma que
duas expressões são iguais apenas por terem aparência parecida.

Quando uma expressão tem sintaxe válida, mas usa uma função ou regra que o
tutor ainda não implementa, ela é registrada em
`futuras_atualizacoes.txt`. Erros de sintaxe, como uma potência incompleta,
não entram nesse arquivo. Assim, a lista representa trabalho futuro real,
separado dos erros de digitação.

## Derivada de imagem

Quando figuras ou letras representam funções dependentes de `x`, use o modo
**Derivada de imagem** no menu inicial. Ele aceita:

```text
bola(x)^triangulo(x)
M^H
bola^triangulo
```

Nesse modo, o tutor entende que os símbolos variam com `x` e aplica:

```text
(u^v)' = u^v * (v'*ln(u) + v*u'/u)
```

No modo comum, letras diferentes de `x` continuam sendo constantes. Essa
separação evita transformar acidentalmente uma constante em função.

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

O resolvedor aceita `x`, números e outras letras constantes, `+`, `-`, `*`,
`/`, `^`, expoentes racionais constantes e variáveis, `sqrt`, `root3`,
`root5`, `sin`, `cos`, `tan`, `cot`, `sec`, `csc`, `arctan`, `arcsin`,
`arccos`, `exp`, `e^...`,
a constante matemática `e`, `ln` e logaritmos de base constante. Para uma
base como 3, use `log3(expressão)`:

```text
python guia_derivadas.py --resolver "log3(sin(x^2))"
```

Potências com base e expoente variáveis usam a regra do bloco `01.05`:

```text
(u^v)' = u^v * (v'*ln(u) + v*u'/u)
```

Para raízes de outros índices, use `rootN(expressão)`, por exemplo:

```text
python guia_derivadas.py --resolver "root3(x^5-x^7)"
python guia_derivadas.py --resolver "root5((x^2-3*x^2)^2)"
python guia_derivadas.py --resolver "raiz quinta de ((x^2-3*x^2)^2)"
```
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

Os códigos seguem o índice de `resumo_de_derivadas.txt`:

- `01.01` a `01.07`: principais regras;
- `02.01` a `02.09`: kit básico de derivadas;
- `03.01` a `03.06`: derivadas trigonométricas;
- `04.01` a `04.06`: derivadas hiperbólicas;
- `05.01` a `05.06`: definições trigonométricas;
- `06.01` a `06.06`: derivadas trigonométricas organizadas;
- `07.01` a `07.06`: definições hiperbólicas;
- `08.01` a `08.06`: derivadas hiperbólicas organizadas.

O script confirma que `resumo_de_derivadas.txt` está na mesma pasta antes de
iniciar. O arquivo `formulas_basicas_algebra.txt` é mantido separado para a
futura parte de álgebra e não é usado como fonte das regras de derivação.
