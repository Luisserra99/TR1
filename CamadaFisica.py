AMOSTRAS_POR_BIT = 10
NIVEL_ALTO = 1.5 # Volts
NIVEL_BAIXO = -NIVEL_ALTO
NIVEL_ZERO = 0.0



# 1. NRZ-Polar (Non-Return to Zero Polar)
"""
Regra: bit 1 → +V; bit 0 → −V. Nível constante durante todo o tempo do bit.
"""

def nrz_polar(bits: list[int]) -> list[float]:
    """Codifica bits em NRZ-Polar: 1 -> +V, 0 -> -V."""
    sinal = []
    for bit in bits:
        if bit == 1:
            sinal.extend([NIVEL_ALTO] * AMOSTRAS_POR_BIT)
        else:
            sinal.extend([NIVEL_BAIXO] * AMOSTRAS_POR_BIT)
    return sinal

def nrz_polar_decoder(sinal: list[float]) -> list[int]:
    """Amostra o sinal no meio de cada bit: nível > 0 -> 1, senão 0."""
    bits = []
    for i in range(0, len(sinal), AMOSTRAS_POR_BIT):
        # calcula a média das amostras do bit para lidar com ruído
        media = sum(sinal[i:i + AMOSTRAS_POR_BIT]) / AMOSTRAS_POR_BIT
        if media > NIVEL_ZERO:
            bits.append(1)
        else:
            bits.append(0)
    return bits

# 2. Manchester
"""
Regra: XOR do bit com o clock. Convenção (IEEE 802.3): bit 1 = transição alto→baixo;
bit 0 = transição baixo→alto. Cada bit tem duas metades (meio-período).
"""

def manchester(bits: list[int]) -> list[float]:
    """Cada bit vira duas metades com transição no meio do período."""
    sinal = []
    for bit in bits:
        if bit == 1:
            sinal.extend( [NIVEL_ALTO,NIVEL_ZERO] * AMOSTRAS_POR_BIT)
        else:
            sinal.extend([NIVEL_ZERO, NIVEL_ALTO] * AMOSTRAS_POR_BIT)
    return sinal

def manchester_decoder(sinal: list[float]) -> list[int]:
    """Identifica a transição no meio do bit para recuperar o valor."""
    bits = []
    for i in range(0, len(sinal), int(2 * AMOSTRAS_POR_BIT)):
        # calcula a média das amostras do bit para lidar com ruído
        media = 0
        for j in range(AMOSTRAS_POR_BIT):
            if sinal[i + 2*j] > sinal[i + 1 + 2*j]: # se é uma borda de descida é 1
                media+=1
        media = media / AMOSTRAS_POR_BIT
        if media > 0.5:
            bits.append(1)
        else:
            bits.append(0)
    return bits

# 3. Bipolar (AMI — Alternate Mark Inversion)
"""
Regra: bit 0 → 0; bit 1 → alterna entre +V e −V a cada ocorrência.
"""


def bipolar(bits: list[int]) -> list[float]:
    """0 -> 0V; 1 -> alterna +V / -V."""
    sinal = []
    #guarda o ultimo nível para alternar entre +V e -V
    ultimo_nivel = NIVEL_BAIXO
    for bit in bits:
        if bit == 1:
            if ultimo_nivel == NIVEL_ALTO:
                sinal.extend([NIVEL_BAIXO] * AMOSTRAS_POR_BIT)
                ultimo_nivel = NIVEL_BAIXO
            else:
                sinal.extend([NIVEL_ALTO] * AMOSTRAS_POR_BIT)
                ultimo_nivel = NIVEL_ALTO
        else:
            sinal.extend([NIVEL_ZERO] * AMOSTRAS_POR_BIT)
    return sinal

def bipolar_decoder(sinal: list[float]) -> list[int]:
    """Nível != 0 -> 1; nível == 0 -> 0 (usar limiar para o ruído)."""
    bits = []
    for i in range(0, len(sinal), AMOSTRAS_POR_BIT):
        # calcula a média das amostras do bit para lidar com ruído
        media = sum(sinal[i:i + AMOSTRAS_POR_BIT]) / AMOSTRAS_POR_BIT
        if (media > (NIVEL_ALTO + NIVEL_ZERO) / 2) or (media < (NIVEL_BAIXO + NIVEL_ZERO) / 2):
            bits.append(1)
        else:
            bits.append(0)
    return bits