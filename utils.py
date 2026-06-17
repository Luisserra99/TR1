# ASCII/UTF-8 usam 8 bits por byte.
BITS_POR_BYTE = 8



# 1. Conversões base
def int_para_bits(valor: int, n_bits: int) -> list[int]:
    # Converte um inteiro sem sinal em uma lista de `n_bits` bits (MSB primeiro).

    if valor < 0:
        raise ValueError("Inteiro negativo não é suportado.")
    
    if valor >= (1 << n_bits):
        raise ValueError(f"O valor {valor} não cabe em {n_bits} bits.")
    
    # Desloca cada bit para a posição 0 e isola com & 1. Percorre do MSB ao LSB.
    l = []
    for i in range(n_bits):
        l.append((valor >> (n_bits - 1 - i)) & 1)
    return l


def bits_para_int(bits: list[int]) -> int:
    # Converte uma lista de bits (MSB primeiro) em inteiro sem sinal.

    valor = 0
    for bit in bits:
        # Desloca o acumulado e insere o próximo bit na posição menos significativa.
        valor = (valor << 1) | (bit & 1)
    return valor


def adicionar_padding(bits: list[int], multiplo: int) -> list[int]:
    # Acrescenta zeros à direita até o comprimento ser múltiplo.

    if multiplo <= 0:
        raise ValueError("multiplo deve ser inteiro positivo.")
    # resto = tamanho atual MOD multiplo
    resto = len(bits) % multiplo 
    if resto == 0:
        return list(bits)
    return list(bits) + [0] * (multiplo - resto)


def fatiar_em_payloads(bits: list[int], tam_max: int) -> list[list[int]]:
    # Divide a sequência de bits em blocos (payloads) de até tam_max bits.

    if tam_max <= 0:
        raise ValueError("tam_max deve ser inteiro positivo.")
    
    l =[]
    for i in range(0, len(bits), tam_max):
        l.append(bits[i:i + tam_max])
    return l



# 2. Aplicação — texto <-> bits
def texto_para_bits(texto: str) -> list[int]:
    # Codifica um texto em uma lista de bits ( UTF-8).

    bits = []
    for byte in texto.encode("utf-8"):
        bits.extend(int_para_bits(byte, BITS_POR_BYTE))
    return bits


def bits_para_texto(bits: list[int]) -> str:
    # Reconstrói o texto a partir de uma lista de bits (UTF-8).

    n_bytes = len(bits) // BITS_POR_BYTE
    valores = bytearray()
    for i in range(n_bytes):
        bloco = bits[i * BITS_POR_BYTE:(i + 1) * BITS_POR_BYTE]
        valores.append(bits_para_int(bloco))

    # errors="ignore" para não dar erro no codigo caso ocorra caracteres invalidos.
    return valores.decode("utf-8", errors="ignore")

