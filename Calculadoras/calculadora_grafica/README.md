# Calculadora científica gráfica

Projeto independente, separado de `calculadora.ipynb` e `calculadora.py`.
Usa somente a biblioteca padrão do Python e não exige instalação de pacotes.

## Executar

No Windows, dê dois cliques em `CalculadoraGrafica.exe`. O executável inclui
o Python e a interface gráfica; não é necessário instalar Python para usar
essa versão.

Para executar o código-fonte com Python instalado, rode:

```text
py -3 interface_grafica.py
```

## Recursos

- Operações: adição, subtração, multiplicação, divisão e potência.
- Funções: raiz quadrada, seno, cosseno, tangente, funções trigonométricas
  inversas, logaritmo natural, logaritmo de base 10 e valor absoluto.
- Constantes `pi` e `e`.
- Alternância entre graus e radianos.
- Entrada pelo teclado ou pelos botões da janela.
- Mensagens para expressões inválidas, divisão por zero e domínio matemático
  inválido.

Funções devem ser escritas com parênteses, por exemplo `sin(30)` ou
`sqrt(25)`. O modo inicial é graus. Use `^` para potência; a multiplicação
deve ser explícita, como em `2*pi`.

## Testes

```text
python -m unittest discover -s . -v
```

O avaliador aceita somente operações e funções matemáticas listadas no código;
não executa comandos Python fornecidos na expressão.
