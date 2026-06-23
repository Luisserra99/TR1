import CamadaEnlace
import CamadaFisica
import utils 

def iniciar_transmissao(mensagem: str, configuracoes: dict):
    """
    Função principal que orquestra o Fluxo TX: texto -> bits -> enlace -> física -> sinal.
    :parâmetro mensagem: A string digitada pelo usuário na InterfaceGUI.
    :parâmetro configuracoes: Dicionário contendo os parâmetros escolhidos na GUI.
    :return: O sinal final (V/W) a ser enviado ao meio de comunicação.
    """
    print("--- INICIANDO TRANSMISSÃO ---")
    
    # ==========================================
    # 1. APLICAÇÃO DE REDE
    # ==========================================
    # Conversão de Texto para Bits
    bits_iniciais = utils.texto_para_bits(mensagem)
    print(f"Aplicação: Texto convertido em {len(bits_iniciais)} bits.")

    # Busca o tamanho máximo do quadro definido na Interface Gráfica
    # (Usando 32 como fallback de segurança caso não venha no dicionário)
    tamanho_maximo = configuracoes.get('tamanho_maximo_quadro', 32)
    
    # Divide a sequência gigante de bits em blocos menores (payloads)
    payloads = utils.fatiar_em_payloads(bits_iniciais, tamanho_maximo)
    print(f"Aplicação: Bits divididos em {len(payloads)} payload(s) de até {tamanho_maximo} bits.")

    
    # ==========================================
    # 2. CAMADA DE ENLACE DE DADOS
    # ==========================================
    quadros_finais_enlace = []
    
    # Processa cada bloco individualmente para montar os quadros
    for i, payload in enumerate(payloads):
        
        # 2.1 - Detecção e Correção de Erros
        # Se algum algoritmo (ex: Checksum) exigir um tamanho múltiplo específico,
        # você pode usar o utilis.adicionar_padding(payload, multiplo) dentro dessa função.
        k_checksum = configuracoes.get('tamanho_checksum', CamadaEnlace.TAMANHO_CHECKSUM_BITS)
        bits_com_edc = CamadaEnlace.adicionar_controle_erro(payload, configuracoes['tipo_edc'], k_checksum)
        
        # 2.2 - Enquadramento
        quadro_enquadrado = CamadaEnlace.aplicar_enquadramento(bits_com_edc, configuracoes['tipo_enquadramento'])
        
        # Concatena o quadro processado na lista final que irá para a camada física
        quadros_finais_enlace.extend(quadro_enquadrado)
        print(f"Enlace: Quadro {i+1}/{len(payloads)} processado com sucesso.")

    
    # ==========================================
    # 3. CAMADA FÍSICA
    # ==========================================
    # A física é OU por portadora OU banda-base (modelo de seleção, simétrico ao
    # Receptor): se uma modulação por portadora foi escolhida, ela modula os bits
    # diretamente; caso contrário, usa-se a codificação digital banda-base.
    tipo_portadora = configuracoes['tipo_modulacao_analogica']
    if tipo_portadora != 'nenhum':
        sinal = CamadaFisica.modulator(quadros_finais_enlace, tipo_portadora)
    else:
        sinal = CamadaFisica.coder(quadros_finais_enlace, configuracoes['tipo_modulacao_digital'])

    print("--- TRANSMISSÃO FINALIZADA ---")

    # Retorna o sinal para o Simulador.py, que vai aplicar o ruído e enviar pro receptor.py
    return sinal