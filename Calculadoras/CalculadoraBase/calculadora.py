def calcular(valor1, valor2, operacao):
    if operacao == "+":
        return valor1 + valor2
    if operacao == "-":
        return valor1 - valor2
    if operacao == "*":
        return valor1 * valor2
    if operacao == "/":
        if valor2 == 0:
            raise ValueError("Não é possível dividir por zero.")
        return valor1 / valor2

    raise ValueError("Operação inválida.")


def ler_numero(mensagem):
    while True:
        entrada = input(mensagem).strip().replace(",", ".")
        try:
            return float(entrada)
        except ValueError:
            print("Digite um número válido.")


def main():
    valor1 = ler_numero("Digite o primeiro valor: ")
    operacao = input("Escolha a operação (+, -, *, /): ").strip()
    valor2 = ler_numero("Digite o segundo valor: ")

    try:
        resultado = calcular(valor1, valor2, operacao)
    except ValueError as erro:
        print(erro)
        return

    print(f"Resultado: {resultado:g}")


if __name__ == "__main__":
    main()
