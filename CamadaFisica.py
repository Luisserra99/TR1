import numpy as np
import utils

AMOSTRAS_POR_BIT = 100
NIVEL_ALTO = 1.5 # Volts
NIVEL_BAIXO = -NIVEL_ALTO
NIVEL_ZERO = 0.0
FREQUENCIA_PORTADORA = 2 # maximo permitido AMOSTRAS_POR_BIT//2

###########################################
# MODULAÇÃO DE SINAL DIGITAL
###########################################

# 1. NRZ-Polar (Non-Return to Zero Polar)
"""
Regra: bit 1 → +V; bit 0 → −V. Nível constante durante todo o tempo do bit.
"""

def nrz_polar(bits: list[int]) -> np.ndarray:
    """Codifica bits em NRZ-Polar: 1 -> +V, 0 -> -V."""
    sinal = []
    for bit in bits:
        if bit == 1:
            sinal.extend([NIVEL_ALTO]* AMOSTRAS_POR_BIT )
        else:
            sinal.extend([NIVEL_BAIXO]* AMOSTRAS_POR_BIT )
    return np.array(sinal)

def nrz_polar_decoder(sinal: np.ndarray) -> list[int]:
    """Amostra o sinal no meio de cada bit: nível > 0 -> 1, senão 0."""
    bits = []
    for i in range(0, len(sinal), AMOSTRAS_POR_BIT):
        # calcula a média das amostras do bit para lidar com ruído
        media = np.mean(sinal[i:i + AMOSTRAS_POR_BIT])
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

def manchester(bits: list[int]) -> np.ndarray:
    """Cada bit vira duas metades planas com transição no meio do período.
    IEEE 802.3: bit 1 = alto→baixo; bit 0 = baixo→alto.
    Cada bit ocupa AMOSTRAS_POR_BIT amostras no total (metade em cada nível).
    """
    sinal = []
    metade = AMOSTRAS_POR_BIT // 2
    for bit in bits:
        if bit == 1:
            sinal.extend([NIVEL_ALTO] * metade + [NIVEL_BAIXO] * metade)
        else:
            sinal.extend([NIVEL_BAIXO] * metade + [NIVEL_ALTO] * metade)
    return np.array(sinal)

def manchester_decoder(sinal: np.ndarray) -> list[int]:
    """Identifica a transição no meio do bit para recuperar o valor.
    Compara a média da primeira metade com a segunda: alto→baixo = 1, baixo→alto = 0.
    """
    bits = []
    metade = AMOSTRAS_POR_BIT // 2
    for i in range(0, len(sinal), AMOSTRAS_POR_BIT):
        primeira = np.mean(sinal[i:i + metade])
        segunda = np.mean(sinal[i + metade:i + AMOSTRAS_POR_BIT])
        bits.append(1 if primeira > segunda else 0)
    return bits

# 3. Bipolar (AMI — Alternate Mark Inversion)
"""
Regra: bit 0 → 0; bit 1 → alterna entre +V e −V a cada ocorrência.
"""


def bipolar(bits: list[int]) -> np.ndarray:
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
    return np.array(sinal)
    
def bipolar_decoder(sinal: np.ndarray) -> list[int]:
    """Nível != 0 -> 1; nível == 0 -> 0 (usar limiar para o ruído)."""
    bits = []
    for i in range(0, len(sinal), AMOSTRAS_POR_BIT):
        # calcula a média das amostras do bit para lidar com ruído
        media = np.mean(sinal[i:i + AMOSTRAS_POR_BIT])
        if (media > (NIVEL_ALTO + NIVEL_ZERO) / 2) or (media < (NIVEL_BAIXO + NIVEL_ZERO) / 2):
            bits.append(1)
        else:
            bits.append(0)
    return bits


###########################################
# MODULAÇÃO POR PORTADORA
###########################################

# 1 ASK — Amplitude Shift Keying
"""
Regra: bit 1 → portadora com amplitude A; bit 0 → amplitude 0 (ou menor).
"""

def ask_modulation(bits, f=FREQUENCIA_PORTADORA, A=NIVEL_ALTO, N=AMOSTRAS_POR_BIT) -> np.ndarray:
    sinal = np.zeros(len(bits) * N)
    t = np.arange(N) / N  # vetor de tempo para um bit
    portadora = A * np.sin(2 * np.pi * f * t)
    for i, bit in enumerate(bits):
        if bit == 1:
            sinal[i * N:(i + 1) * N] = portadora
    return sinal

def ask_demodulation(sinal, f=FREQUENCIA_PORTADORA, A=NIVEL_ALTO, N=AMOSTRAS_POR_BIT) -> list[int]:
    bits = []
    t = np.arange(N) / N  # vetor de tempo para um bit
    portadora = A * np.sin(2 * np.pi * f * t)
    # limiar = metade da energia do símbolo "1": dot(portadora,portadora) ≈ N*A²/2
    limiar = N * A * A / 4
    for i in range(0, len(sinal), N):
        segmento = sinal[i:i + N]
        correlacao = np.dot(segmento, portadora)
        bits.append(1 if correlacao > limiar else 0)
    return bits


# 2. FSK — Frequency Shift Keying
"""
Regra: bit 1 → frequência f1; bit 0 → frequência f0.
"""

def fsk_modulation(bits, f=FREQUENCIA_PORTADORA, A=NIVEL_ALTO, N=AMOSTRAS_POR_BIT) -> np.ndarray: 
    f0 = f / 2 # frequência para bit 0 (metade da frequência de amostragem)
    f1 = f     # frequência para bit 1 (igual à frequência de amostragem)
    sinal = np.zeros(len(bits) * N)
    t = np.arange(N) / N  # vetor de tempo para um bit
    portadora1 = A * np.sin(2 * np.pi * f1 * t)
    portadora0 = A * np.sin(2 * np.pi * f0 * t)
    for i, bit in enumerate(bits):
        if bit == 1:
            sinal[i * N:(i + 1) * N] = portadora1
        else:
            sinal[i * N:(i + 1) * N] = portadora0
    return sinal

def fsk_demodulation(sinal, f=FREQUENCIA_PORTADORA, A=NIVEL_ALTO, N=AMOSTRAS_POR_BIT) -> list[int]:
    bits = []
    f0 = f / 2 # frequência para bit 0 (metade da frequência de amostragem)
    f1 = f     # frequência para bit 1 (igual à frequência de amostragem)
    t = np.arange(N) / N  # vetor de tempo para um bit
    portadora1 = A * np.sin(2 * np.pi * f1 * t)
    portadora0 = A * np.sin(2 * np.pi * f0 * t)
    for i in range(0, len(sinal), N):
        segmento = sinal[i:i + N]
        correlacao1 = np.dot(segmento, portadora1)
        correlacao0 = np.dot(segmento, portadora0)
        bits.append(1 if correlacao1 > correlacao0 else 0)
    return bits


# 3. PSK / QPSK — Phase Shift Keying
"""
BPSK: bit 1 → fase 0; bit 0 → fase π.
QPSK: processa 2 bits por símbolo, cada par mapeado a uma das 4 fases
(45°, 135°, 225°, 315°).
"""

def psk_modulation(bits, f=FREQUENCIA_PORTADORA, A=NIVEL_ALTO, N=AMOSTRAS_POR_BIT) -> np.ndarray: 
    sinal = np.zeros(len(bits) * N)
    t = np.arange(N) / N  # vetor de tempo para um bit
    portadora1 = A * np.sin(2 * np.pi * f * t)
    portadora0 = A * np.sin(2 * np.pi * f * t + np.pi) # fase invertida para bit 0
    for i, bit in enumerate(bits):
        if bit == 1:
            sinal[i * N:(i + 1) * N] = portadora1
        else:
            sinal[i * N:(i + 1) * N] = portadora0
    return sinal

def psk_demodulation(sinal, f=FREQUENCIA_PORTADORA, A=NIVEL_ALTO, N=AMOSTRAS_POR_BIT) -> list[int]: 
    bits = []
    t = np.arange(N) / N  # vetor de tempo para um bit
    portadora1 = A * np.sin(2 * np.pi * f * t)
    portadora0 = A * np.sin(2 * np.pi * f * t + np.pi) # fase invertida para bit 0
    for i in range(0, len(sinal), N):
        segmento = sinal[i:i + N]
        correlacao1 = np.dot(segmento, portadora1)
        correlacao0 = np.dot(segmento, portadora0)
        bits.append(1 if correlacao1 > correlacao0 else 0)
    return bits

def qpsk_modulation(bits, f=FREQUENCIA_PORTADORA, A=NIVEL_ALTO, N=AMOSTRAS_POR_BIT) -> np.ndarray:
    t = np.arange(N) / N  # vetor de tempo para 2 bits
    portadora11 = A * np.sin(2 * np.pi * f * t + np.pi/4) # 45°
    portadora10 = A * np.sin(2 * np.pi * f * t + 3*np.pi/4) # 135°
    portadora00 = A * np.sin(2 * np.pi * f * t + 5*np.pi/4) # 225°
    portadora01 = A * np.sin(2 * np.pi * f * t + 7*np.pi/4) # 315°
    bits = utils.adicionar_padding(bits, 2) # garante múltiplos de 2 bits
    bits = utils.fatiar_em_payloads(bits, 2) # divide em pares de bits
    sinal = np.zeros(len(bits) * N)
    for i, bit in enumerate(bits):
        if bit == [0,0]:
            sinal[i * N:(i + 1) * N] = portadora00
        elif bit == [0,1]:
            sinal[i * N:(i + 1) * N] = portadora01
        elif bit == [1,1]:
            sinal[i * N:(i + 1) * N] = portadora11
        else: # bit == [1,0]
            sinal[i * N:(i + 1) * N] = portadora10
    return sinal

def qpsk_demodulation(sinal, f=FREQUENCIA_PORTADORA, A=NIVEL_ALTO, N=AMOSTRAS_POR_BIT) -> list[int]: 
    bits = []
    t = np.arange(N) / N  # vetor de tempo para um bit
    portadora11 = A * np.sin(2 * np.pi * f * t + np.pi/4) # 45°
    portadora10 = A * np.sin(2 * np.pi * f * t + 3*np.pi/4) # 135°
    portadora00 = A * np.sin(2 * np.pi * f * t + 5*np.pi/4) # 225°
    portadora01 = A * np.sin(2 * np.pi * f * t + 7*np.pi/4) # 315°
    for i in range(0, len(sinal), N):
        segmento = sinal[i:i + N]
        correlacao11 = np.dot(segmento, portadora11)
        correlacao10 = np.dot(segmento, portadora10)
        correlacao00 = np.dot(segmento, portadora00)
        correlacao01 = np.dot(segmento, portadora01)
        # Simbolo com maior correlação, em caso de empate segue a ordem 11 > 10 > 00 > 01
        max_correlacao = max(correlacao11, correlacao10, correlacao00, correlacao01)
        if max_correlacao == correlacao11:
            bits.append([1, 1])
        elif max_correlacao == correlacao10:
            bits.append([1, 0])
        elif max_correlacao == correlacao00:
            bits.append([0, 0])
        else:
            bits.append([0, 1])
    # achata pares -> list[int] plano (consistente com ask/fsk/psk)
    return [b for par in bits for b in par]

# 4. 16-QAM — Quadrature Amplitude Modulation
"""
Regra: processa 4 bits por símbolo (constelação 4×4). Combina amplitude e fase
(componentes I e Q). Garanta padding para múltiplos de 4 bits.
"""

# Amplitudes dos eixos
_QAM16_PEQUENO = 1 / (3 * np.sqrt(2))
_QAM16_GRANDE = 1 / np.sqrt(2)

# Dicionário que mapeia cada quadribit (MSB primeiro) -> (I, Q) eixos (x,y)
_QAM16_CONSTELACAO = {
    (0, 1, 1, 1): (-_QAM16_GRANDE,  _QAM16_GRANDE),
    (0, 1, 0, 1): (-_QAM16_PEQUENO, _QAM16_GRANDE),
    (1, 1, 0, 1): ( _QAM16_PEQUENO, _QAM16_GRANDE),
    (1, 1, 1, 1): ( _QAM16_GRANDE,  _QAM16_GRANDE),
    (0, 1, 1, 0): (-_QAM16_GRANDE,  _QAM16_PEQUENO),
    (0, 1, 0, 0): (-_QAM16_PEQUENO, _QAM16_PEQUENO),
    (1, 1, 0, 0): ( _QAM16_PEQUENO, _QAM16_PEQUENO),
    (1, 1, 1, 0): ( _QAM16_GRANDE,  _QAM16_PEQUENO),
    (0, 0, 1, 0): (-_QAM16_GRANDE, -_QAM16_PEQUENO),
    (0, 0, 0, 0): (-_QAM16_PEQUENO, -_QAM16_PEQUENO),
    (1, 0, 0, 0): ( _QAM16_PEQUENO, -_QAM16_PEQUENO),
    (1, 0, 1, 0): ( _QAM16_GRANDE, -_QAM16_PEQUENO),
    (0, 0, 1, 1): (-_QAM16_GRANDE, -_QAM16_GRANDE),
    (0, 0, 0, 1): (-_QAM16_PEQUENO, -_QAM16_GRANDE),
    (1, 0, 0, 1): ( _QAM16_PEQUENO, -_QAM16_GRANDE),
    (1, 0, 1, 1): ( _QAM16_GRANDE, -_QAM16_GRANDE),
}

def qam16_modulation(bits, f=FREQUENCIA_PORTADORA, A=NIVEL_ALTO, N=AMOSTRAS_POR_BIT) -> np.ndarray:
    bits = utils.adicionar_padding(bits, 4)       # garante múltiplos de 4 bits
    bits = utils.fatiar_em_payloads(bits, 4)  # divide em quadribits
    t = np.arange(N) / N  # vetor de tempo para um símbolo (4 bits)
    cosseno = np.cos(2 * np.pi * f * t)
    seno = np.sin(2 * np.pi * f * t)
    sinal = np.zeros(len(bits) * N)
    for i, simbolo in enumerate(bits):
        I, Q = _QAM16_CONSTELACAO[tuple(simbolo)]
        # s(t) = A * (I*cos + Q*sin)
        sinal[i * N:(i + 1) * N] = A * (I * cosseno + Q * seno)
    return sinal

def qam16_demodulation(sinal, f=FREQUENCIA_PORTADORA, A=NIVEL_ALTO, N=AMOSTRAS_POR_BIT) -> list[int]:
    bits = []
    t = np.arange(N) / N  # vetor de tempo para um símbolo (4 bits)
    cosseno = np.cos(2 * np.pi * f * t)
    seno = np.sin(2 * np.pi * f * t)
    for i in range(0, len(sinal), N):
        segmento = sinal[i:i + N]
        I_hat = np.dot(segmento, cosseno) * 2 / (N * A)
        Q_hat = np.dot(segmento, seno) * 2 / (N * A)
        # Decide pelo ponto da constelação mais próximo (menor distância euclidiana).
        melhor_simbolo = None
        menor_distancia = float("inf")
        for simbolo, (I, Q) in _QAM16_CONSTELACAO.items():
            distancia = (I_hat - I) ** 2 + (Q_hat - Q) ** 2
            if distancia < menor_distancia:
                menor_distancia = distancia
                melhor_simbolo = simbolo
        bits.append(list(melhor_simbolo))
    # achata quadribits -> list[int] plano (consistente com ask/fsk/psk)
    return [b for quad in bits for b in quad]


###########################################
# SELETOR DE CODIFICAÇÃO / MODULAÇÃO
###########################################


def coder(bits: list[int], tipo: str) -> np.ndarray:
    """Despacha para nrz_polar / manchester / bipolar conforme 'tipo'."""
    if tipo == "nrz_polar":
        return nrz_polar(bits)
    elif tipo == "manchester":
        return manchester(bits)
    elif tipo == "bipolar":
        return bipolar(bits)
    else:
        raise ValueError(f"Tipo de codificação desconhecido: {tipo}")

def decoder(sinal: np.ndarray, tipo: str) -> list[int]:
    """Despacha para o decodificador banda-base correspondente."""
    if tipo == "nrz_polar":
        return nrz_polar_decoder(sinal)
    elif tipo == "manchester":
        return manchester_decoder(sinal)
    elif tipo == "bipolar":
        return bipolar_decoder(sinal)
    else:
        raise ValueError(f"Tipo de codificação desconhecido: {tipo}")

def modulator(bits, tipo: str, **params) -> np.ndarray:
    """Despacha para ask/fsk/psk/qpsk/qam16."""
    if tipo == "ask":
        return ask_modulation(bits, **params)
    elif tipo == "fsk":
        return fsk_modulation(bits, **params)
    elif tipo == "psk":
        return psk_modulation(bits, **params)
    elif tipo == "qpsk":
        return qpsk_modulation(bits, **params)
    elif tipo == "qam16":
        return qam16_modulation(bits, **params)
    else:
        raise ValueError(f"Tipo de modulação desconhecido: {tipo}")

def demodulator(sinal, tipo: str, **params) -> list[int]:
    if tipo == "ask":
        return ask_demodulation(sinal, **params)
    elif tipo == "fsk":
        return fsk_demodulation(sinal, **params)
    elif tipo == "psk":
        return psk_demodulation(sinal, **params)
    elif tipo == "qpsk":
        return qpsk_demodulation(sinal, **params)
    elif tipo == "qam16":
        return qam16_demodulation(sinal, **params)
    else:
        raise ValueError(f"Tipo de modulação desconhecido: {tipo}")


###########################################
# RUIDO
###########################################

"""
O meio recebe o sinal em V/W e adiciona ruído gaussiano n(x, σ):
"""

def aplicar_ruido(sinal: np.ndarray, x: float, sigma: float) -> np.ndarray:
    """
    Soma a cada amostra um ruído gaussiano de média x e desvio sigma.
    """
    # Gerar o ruído com o mesmo tamanho do sinal
    ruido = np.random.normal(loc=x, scale=sigma, size=sinal.shape)

    # Adicionar o ruído ao sinal
    sinal_ruidoso = sinal + ruido
    return sinal_ruidoso