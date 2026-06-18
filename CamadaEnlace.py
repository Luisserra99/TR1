import utils.py as utils

###############################
#   ENQUADRAMENTO
###############################

# 1. Contagem de caracteres
"""
Regra: cada quadro inicia com um cabeçalho (ex.: 8 bits) 
indicando o tamanho do quadro.
"""

def framing_char_count(quadro_bits: list[int]) -> list[int]:
    """Prefixa um contador (em bits) com o tamanho do quadro."""

def deframing_char_count(bitstream: list[int]) -> list[list[int]]:
    """Lê o contador e fatia os quadros."""


# 2. Flags com inserção de bytes/caracteres (byte stuffing)
"""
Regra: delimita o quadro com a flag 0x7E (01111110).
 Se a flag ou o caractere de escape
0x7D aparecer no payload, insere um byte de escape antes.
"""

def framing_byte_flags(quadro_bits: list[int]) -> list[int]: ...
def deframing_byte_flags(bitstream: list[int]) -> list[list[int]]: ...

# 3. Flags com inserção de bits (bit stuffing)
"""
Regra: flag 01111110. No payload, após cinco 1 consecutivos, insere um 0
(destuffing no RX remove esse 0).
"""

def framing_bit_flags(quadro_bits: list[int]) -> list[int]: ...
def deframing_bit_flags(bitstream: list[int]) -> list[list[int]]: ...

###############################
#   DETECÇÃO DE ERROS
###############################