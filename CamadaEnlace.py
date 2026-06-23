import utils

# Tamanhos de enquadramento.
TAMANHO_CONTADOR_BITS = 16  # bits do contador de tamanho (contagem de caracteres); cabe quadros até 65535 bits
TAMANHO_CHECKSUM_BITS = 8   # tamanho default do bloco de checksum
TAMANHO_QUADRO = 212        # bits de payload por quadro (múltiplo de 8)

# Flag delimitadora (0x7E) e caractere de escape (0x7D), ambos em 8 bits.
FLAG = utils.int_para_bits(0x7E, utils.BITS_POR_BYTE)
ESCAPE = utils.int_para_bits(0x7D, utils.BITS_POR_BYTE)

###############################
#   ENQUADRAMENTO
###############################

# 1. Contagem de caracteres
"""
Regra: cada quadro inicia com um cabeçalho (ex.: 8 bits) 
indicando o tamanho do quadro.
"""

def framing_char_count(quadro_bits: list[int]) -> list[int]:
    """Enquadra UM quadro: prefixa o contador com o tamanho do payload."""
    contador = utils.int_para_bits(len(quadro_bits), TAMANHO_CONTADOR_BITS)
    return contador + quadro_bits

def deframing_char_count(bitstream: list[int]) -> list[list[int]]:
    """Lê o contador e fatia os quadros."""
    bits_desenquadrados = []
    # Só processa enquanto houver pelo menos um cabeçalho completo.
    while len(bitstream) >= TAMANHO_CONTADOR_BITS:
        # Lê o tamanho do quadro no cabeçalho
        tamanho = utils.bits_para_int(bitstream[:TAMANHO_CONTADOR_BITS])
        inicio = TAMANHO_CONTADOR_BITS
        fim = inicio + tamanho
        # Guarda contra resto: tamanho anunciado maior que o disponível => padding
        # físico residual (QPSK/16-QAM alinham a múltiplos de 2/4 bits). Descarta.
        if fim > len(bitstream):
            break
        # Extrai o quadro usando o tamanho lido e o remove do bitstream.
        bits_desenquadrados.append(bitstream[inicio:fim])
        bitstream = bitstream[fim:]
    return bits_desenquadrados


# 2. Flags com inserção de bytes/caracteres (byte stuffing)
"""
Regra: delimita o quadro com a flag 0x7E (01111110).
 Se a flag ou o caractere de escape
0x7D aparecer no payload, insere um byte de escape antes.
"""


def framing_byte_flags(quadro_bits: list[int]) -> list[int]:
    """Delimita cada quadro com a FLAG e aplica byte stuffing no payload.

    Byte stuffing opera byte a byte, então o payload é alinhado a múltiplos de 8
    bits. Para preservar o tamanho original, insere logo após a FLAG de abertura
    um byte com a quantidade de bits de padding (0..7) usada nesse alinhamento.
    """
    pad = (-len(quadro_bits)) % utils.BITS_POR_BYTE
    # corpo = [byte de padding] + payload + zeros de alinhamento (tudo múltiplo de 8 bits).
    corpo = utils.int_para_bits(pad, utils.BITS_POR_BYTE) + list(quadro_bits) + [0] * pad

    bits_enquadrados = list(FLAG)  # flag de abertura
    for j in range(0, len(corpo), utils.BITS_POR_BYTE):
        byte = corpo[j:j + utils.BITS_POR_BYTE]
        # Se o byte coincide com a FLAG ou o ESCAPE, insere ESCAPE antes dele.
        if byte == FLAG or byte == ESCAPE:
            bits_enquadrados += list(ESCAPE)
        bits_enquadrados += byte
    bits_enquadrados += list(FLAG)  # flag de fechamento
    return bits_enquadrados

def deframing_byte_flags(bitstream: list[int]) -> list[list[int]]:
    """Lê a sequência delimitada por FLAGs, remove o byte stuffing e restaura o
    tamanho original (descarta o byte de padding e os bits de alinhamento)."""
    quadros = []
    corpo_atual = []
    dentro_do_quadro = False
    escapado = False

    i = 0
    while i + utils.BITS_POR_BYTE <= len(bitstream):
        byte = bitstream[i:i + utils.BITS_POR_BYTE]
        i += utils.BITS_POR_BYTE

        if escapado:
            # Byte após o ESCAPE é sempre dado literal (FLAG ou ESCAPE).
            corpo_atual += byte
            escapado = False
        elif byte == FLAG:
            if dentro_do_quadro:
                # FLAG de fechamento: 1º byte do corpo = padding; remove-o e os bits finais.
                pad = utils.bits_para_int(corpo_atual[:utils.BITS_POR_BYTE])
                payload = corpo_atual[utils.BITS_POR_BYTE:]
                if pad:
                    payload = payload[:-pad]
                quadros.append(payload)
                corpo_atual = []
                dentro_do_quadro = False
            else:
                # FLAG de abertura: começa um novo quadro.
                dentro_do_quadro = True
        elif byte == ESCAPE:
            # Próximo byte é literal; o ESCAPE não entra no corpo.
            escapado = True
        else:
            corpo_atual += byte
    return quadros

# 3. Flags com inserção de bits (bit stuffing)
"""
Regra: flag 01111110. No payload, após cinco 1 consecutivos, insere um 0
(destuffing no RX remove esse 0).
"""

def framing_bit_flags(quadro_bits: list[int]) -> list[int]:
    """Delimita cada quadro com a FLAG e aplica bit stuffing (insere 0 após cinco 1s)."""
    bits_enquadrados = list(FLAG)  # flag de abertura
    contador_1s = 0
    for bit in quadro_bits:
        bits_enquadrados.append(bit)
        if bit == 1:
            contador_1s += 1
            # Após cinco 1s consecutivos, insere um 0 (impede gerar a FLAG no payload).
            if contador_1s == 5:
                bits_enquadrados.append(0)
                contador_1s = 0
        else:
            contador_1s = 0
    bits_enquadrados += list(FLAG)  # flag de fechamento
    return bits_enquadrados

def deframing_bit_flags(bitstream: list[int]) -> list[list[int]]:
    """Lê a sequência delimitada por FLAGs e remove o bit stuffing."""
    quadros = []
    quadro_atual = []
    dentro_do_quadro = False
    contador_1s = 0

    i = 0
    n = len(bitstream)
    while i < n:
        # A FLAG (01111110) nunca aparece no payload já com stuffing: serve de delimitador.
        if bitstream[i:i + utils.BITS_POR_BYTE] == FLAG:
            if dentro_do_quadro:
                # FLAG de fechamento: finaliza o quadro atual.
                quadros.append(quadro_atual)
                quadro_atual = []
                dentro_do_quadro = False
            else:
                # FLAG de abertura: começa um novo quadro.
                dentro_do_quadro = True
            i += utils.BITS_POR_BYTE
            contador_1s = 0
            continue

        if dentro_do_quadro:
            bit = bitstream[i]
            quadro_atual.append(bit)
            if bit == 1:
                contador_1s += 1
                if contador_1s == 5:
                    # O próximo bit é o 0 de stuffing inserido no TX: descarta.
                    i += 1
                    contador_1s = 0
            else:
                contador_1s = 0
        i += 1
    return quadros

###############################
#   DETECÇÃO DE ERROS
###############################

# 1. Bit de paridade par

def parity_insert(bits: list[int]) -> list[int]:
    # 0 se a soma for par, 1 se for ímpar
    paridade = sum(bits) % 2
    return bits + [paridade]
def parity_check(bits: list[int]) -> bool:
    # Verifica se a soma dos bits é par
    return sum(bits) % 2 == 0
def parity_remove(bits: list[int]) -> list[int]:
    # Remove o bit de paridade
    return bits[:-1]

# 2. Checksum

# Função auxiliar para soma
def _soma_um_complemento(blocos: list[list[int]], k: int) -> int:
    """Soma blocos de k bits em complemento de um (carry circular nos k bits)."""
    mascara = (2 ** k) - 1
    soma = 0
    for bloco in blocos:
        soma += utils.bits_para_int(bloco)
        # Carry-around: realimenta o estouro nos k bits menos significativos.
        soma = (soma & mascara) + (soma >> k)
    while soma >> k:
        soma = (soma & mascara) + (soma >> k)
    return soma

def checksum_insert(bits: list[int], k: int = TAMANHO_CHECKSUM_BITS) -> list[int]:
    """Calcula o checksum (complemento de um da soma dos blocos de k bits) e anexa ao final."""
    # separa em blocos de k bits e adiciona o padding, nao altera o dado final
    blocos = utils.fatiar_em_payloads(utils.adicionar_padding(bits, k), k)
    soma = _soma_um_complemento(blocos, k)
    checksum = ((2 ** k) - 1) - soma  # complemento de um
    return bits + utils.int_para_bits(checksum, k)

def checksum_check(bits: list[int], k: int = TAMANHO_CHECKSUM_BITS) -> bool:
    """Verifica o checksum: soma dos dados + checksum deve dar todos os bits 1."""
    dados = utils.adicionar_padding(bits[:-k], k)
    blocos = utils.fatiar_em_payloads(dados, k) + [bits[-k:]]
    soma = _soma_um_complemento(blocos, k)
    return soma == (2 ** k) - 1

def checksum_remove(bits: list[int], k: int = TAMANHO_CHECKSUM_BITS) -> list[int]:
    """Remove os k bits de checksum do final."""
    return bits[:-k]

# 3. CRC

# Gerador CRC-32 (IEEE 802): poly 0x04C11DB7com o termo x^32 implícito (33 bits).
GERADOR_CRC32 = [1] + utils.int_para_bits(0x04C11DB7, 32)
GRAU_CRC32 = len(GERADOR_CRC32) - 1  # 32

# Função auxiliar para divisão
def _crc32_resto(bits: list[int]) -> list[int]:
    """Divisão polinomial binária (XOR) por GERADOR_CRC32; retorna os 32 bits de resto."""
    r = list(bits)  # cópia
    for i in range(len(r) - GRAU_CRC32):
        if r[i] == 1:
            for j in range(len(GERADOR_CRC32)):
                r[i + j] ^= GERADOR_CRC32[j]
    return r[-GRAU_CRC32:]

def crc32_insert(bits: list[int]) -> list[int]:
    """Anexa os 32 bits de CRC calculados por divisão polinomial."""
    resto = _crc32_resto(bits + [0] * GRAU_CRC32)  # divide msg·x^32
    return bits + resto

def crc32_check(bits: list[int]) -> bool:
    """Recalcula o CRC sobre msg+CRC; resto zero => sem erro detectado."""
    return sum(_crc32_resto(bits)) == 0

def crc32_remove(bits: list[int]) -> list[int]:
    """Remove os 32 bits de CRC do final."""
    return bits[:-GRAU_CRC32]


###############################
#   CORREÇÃO DE ERROS
###############################
"""
Regra: insere bits de paridade nas posições potências de 2
"""

def _hamming_n_paridade(m: int) -> int:
    """Menor r tal que 2^r >= m + r + 1 (r bits de paridade para m bits de dados)."""
    r = 0
    while (2 ** r) < (m + r + 1):
        r += 1
    return r

def _hamming_correction_n_paridade(n: int) -> int:
    """Menor r tal que 2^r >= n (r bits de paridade para n bits de dados)."""
    r = 0
    while (2 ** r) < (n):
        r += 1
    return r

def hamming_insert(bits: list[int]) -> list[int]:
    """Insere bits de paridade nas posições 1,2,4,8,... (paridade par)."""
    m = len(bits) # tamanho da mensagem
    r = _hamming_n_paridade(m)  # m<=244(mensagem max = 212 + 32 CRC-> r<=8
    n = m + r
    # pposicao 0 é ignorada para facilitar o cálculo das posições de paridade (1,2,4,...).
    # posições potência de 2 são paridade.
    code = [0] * (n + 1)
    j = 0
    for pos in range(1, n + 1):
        if (pos & (pos - 1)) != 0:  # não é potência de 2 -> bit de dado
            code[pos] = bits[j]
            j += 1
    # Cada bit de paridade p cobre posições cujo índice tem o bit p ligado.
    for i in range(r):
        p = 1 << i
        paridade = 0
        for pos in range(1, n + 1):
            if pos & p:
                paridade ^= code[pos]
        code[p] = paridade
    return code[1:]

def hamming_correct(bits: list[int]) -> list[int]:
    """Calcula a síndrome, localiza e corrige o bit errado."""
    n = len(bits)
    r = _hamming_correction_n_paridade(n)
    code = [0] + list(bits)  # 1-indexado; posição 0 ignorada.

    # Cada bit de paridade p cobre as posições cujo índice tem o bit p ligado.
    # Acumulo em error_code para obter a posição do erro.
    error_code = 0
    for i in range(r):
        p = 1 << i
        paridade = 0
        for pos in range(1, n + 1):
            if pos & p:
                paridade ^= code[pos]
        if paridade:
            error_code += p
    if error_code != 0 and error_code <= n:
        code[error_code] ^= 1  # corrige o bit errado
    return code[1:]

def hamming_remove(bits: list[int]) -> list[int]:
    """Remove os bits de paridade (posições potência de 2), retornando os dados originais."""
    dados = []
    for pos in range(1, len(bits) + 1):
        if (pos & (pos - 1)) != 0:  # não é potência de 2 -> bit de dado
            dados.append(bits[pos - 1])
    return dados


###############################
#   DESPACHANTES (TX e RX)
###############################
# Pontos únicos de mapeamento string-da-GUI -> função, usados por Transmissor e Receptor.

def adicionar_controle_erro(bits: list[int], tipo_edc: str, k: int = TAMANHO_CHECKSUM_BITS) -> list[int]:
    """TX: anexa o EDC/ECC escolhido ao payload."""
    if tipo_edc == "Paridade":
        return parity_insert(bits)
    elif tipo_edc == "Checksum":
        return checksum_insert(bits, k)
    elif tipo_edc == "CRC-32":
        return crc32_insert(bits)
    elif tipo_edc == "Hamming":
        return hamming_insert(bits)
    elif tipo_edc == "nenhum":
        return list(bits)
    else:
        raise ValueError(f"Tipo de EDC desconhecido: {tipo_edc}")

def verificar_e_remover_controle_erro(bits: list[int], tipo_edc: str, k: int = TAMANHO_CHECKSUM_BITS) -> tuple[list[int], bool]:
    """RX: valida/corrige e remove o EDC/ECC. Retorna (payload, ok).
    Detecção -> ok = resultado do check; Hamming -> corrige 1 bit e ok=True.
    """
    if tipo_edc == "Paridade":
        ok = parity_check(bits)
        return parity_remove(bits), ok
    elif tipo_edc == "Checksum":
        ok = checksum_check(bits, k)
        return checksum_remove(bits, k), ok
    elif tipo_edc == "CRC-32":
        ok = crc32_check(bits)
        return crc32_remove(bits), ok
    elif tipo_edc == "Hamming":
        corrigido = hamming_correct(bits)
        return hamming_remove(corrigido), True
    elif tipo_edc == "nenhum":
        return list(bits), True
    else:
        raise ValueError(f"Tipo de EDC desconhecido: {tipo_edc}")

def aplicar_enquadramento(bits: list[int], tipo_enq: str) -> list[int]:
    """TX: enquadra UM quadro conforme o protocolo escolhido."""
    if tipo_enq == "Contagem de caracteres":
        return framing_char_count(bits)
    elif tipo_enq == "Inserção de bytes":
        return framing_byte_flags(bits)
    elif tipo_enq == "Inserção de bits":
        return framing_bit_flags(bits)
    elif tipo_enq == "nenhum":
        return list(bits)
    else:
        raise ValueError(f"Tipo de enquadramento desconhecido: {tipo_enq}")

def remover_enquadramento(bitstream: list[int], tipo_enq: str) -> list[list[int]]:
    """RX: separa o bitstream nos quadros originais (lista de quadros)."""
    if tipo_enq == "Contagem de caracteres":
        return deframing_char_count(bitstream)
    elif tipo_enq == "Inserção de bytes":
        return deframing_byte_flags(bitstream)
    elif tipo_enq == "Inserção de bits":
        return deframing_bit_flags(bitstream)
    elif tipo_enq == "nenhum":
        return [list(bitstream)]
    else:
        raise ValueError(f"Tipo de enquadramento desconhecido: {tipo_enq}")