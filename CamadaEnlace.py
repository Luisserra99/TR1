import utils

# Tamanhos de enquadramento.
TAMANHO_CABECALHO_BITS = 8  # bits do contador de tamanho (contagem de caracteres)
TAMANHO_QUADRO = 248        # bits de payload por quadro (cabe em 8 bits e é múltiplo de 8)

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

def framing_char_count(bitstream: list[int],t=TAMANHO_QUADRO) -> list[int]:
    """Prefixa um contador (em bits) com o tamanho do quadro."""
    bits_enquadrados = []
    for i in range(0, len(bitstream), t):
        quadro_bits = bitstream[i:i+t]
        # O contador guarda o tamanho real do payload (último quadro pode ser menor).
        contador = utils.int_para_bits(len(quadro_bits), TAMANHO_CABECALHO_BITS)
        bits_enquadrados += contador + quadro_bits
    return bits_enquadrados

def deframing_char_count(bitstream: list[int]) -> list[list[int]]:
    """Lê o contador e fatia os quadros."""
    bits_desenquadrados = []
    while len(bitstream) > 0:
        # Lê o tamanho do quadro no cabeçalho
        tamanho = utils.bits_para_int(bitstream[:TAMANHO_CABECALHO_BITS])
        # Extrai o quadro usando o tamanho lido
        bits_desenquadrados.append(bitstream[TAMANHO_CABECALHO_BITS:TAMANHO_CABECALHO_BITS+tamanho])
        # Remove o quadro processado do bitstream
        bitstream = bitstream[TAMANHO_CABECALHO_BITS+tamanho:]
    return bits_desenquadrados


# 2. Flags com inserção de bytes/caracteres (byte stuffing)
"""
Regra: delimita o quadro com a flag 0x7E (01111110).
 Se a flag ou o caractere de escape
0x7D aparecer no payload, insere um byte de escape antes.
"""


def framing_byte_flags(quadro_bits: list[int], t=TAMANHO_QUADRO) -> list[int]:
    """Delimita cada quadro com a FLAG e aplica byte stuffing no payload."""
    # Byte stuffing opera byte a byte: garante alinhamento em múltiplos de 8 bits.
    quadro_bits = utils.adicionar_padding(quadro_bits, utils.BITS_POR_BYTE)

    bits_enquadrados = []
    for i in range(0, len(quadro_bits), t):
        quadro = quadro_bits[i:i + t]
        bits_enquadrados += list(FLAG)  # flag de abertura
        for j in range(0, len(quadro), utils.BITS_POR_BYTE):
            byte = quadro[j:j + utils.BITS_POR_BYTE]
            # Se o byte coincide com a FLAG ou o ESCAPE, insere ESCAPE antes dele.
            if byte == FLAG or byte == ESCAPE:
                bits_enquadrados += list(ESCAPE)
            bits_enquadrados += byte
        bits_enquadrados += list(FLAG)  # flag de fechamento
    return bits_enquadrados

def deframing_byte_flags(bitstream: list[int]) -> list[list[int]]:
    """Lê a sequência de bits delimitada por FLAGs e remove o byte stuffing."""
    quadros = []
    quadro_atual = []
    dentro_do_quadro = False
    escapado = False

    i = 0
    while i + utils.BITS_POR_BYTE <= len(bitstream):
        byte = bitstream[i:i + utils.BITS_POR_BYTE]
        i += utils.BITS_POR_BYTE

        if escapado:
            # Byte após o ESCAPE é sempre dado literal (FLAG ou ESCAPE).
            quadro_atual += byte
            escapado = False
        elif byte == FLAG:
            if dentro_do_quadro:
                # FLAG de fechamento: finaliza o quadro atual.
                quadros.append(quadro_atual)
                quadro_atual = []
                dentro_do_quadro = False
            else:
                # FLAG de abertura: começa um novo quadro.
                dentro_do_quadro = True
        elif byte == ESCAPE:
            # Próximo byte é literal; o ESCAPE não entra no payload.
            escapado = True
        else:
            quadro_atual += byte
    return quadros

# 3. Flags com inserção de bits (bit stuffing)
"""
Regra: flag 01111110. No payload, após cinco 1 consecutivos, insere um 0
(destuffing no RX remove esse 0).
"""

def framing_bit_flags(quadro_bits: list[int], t=TAMANHO_QUADRO) -> list[int]:
    """Delimita cada quadro com a FLAG e aplica bit stuffing (insere 0 após cinco 1s)."""
    bits_enquadrados = []
    for i in range(0, len(quadro_bits), t):
        quadro = quadro_bits[i:i + t]
        bits_enquadrados += list(FLAG)  # flag de abertura
        contador_1s = 0
        for bit in quadro:
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