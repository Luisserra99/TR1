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
        bits_com_edc = CamadaEnlace.adicionar_controle_erro(payload, configuracoes['tipo_edc'])
        
        # 2.2 - Enquadramento
        quadro_enquadrado = CamadaEnlace.aplicar_enquadramento(bits_com_edc, configuracoes['tipo_enquadramento'])
        
        # Concatena o quadro processado na lista final que irá para a camada física
        quadros_finais_enlace.extend(quadro_enquadrado)
        print(f"Enlace: Quadro {i+1}/{len(payloads)} processado com sucesso.")

    
    # ==========================================
    # 3. CAMADA FÍSICA
    # ==========================================
    # Se os quadros finais não forem múltiplos de 4, podemos aplicar o padding aqui:
    # quadros_finais_enlace = utils.adicionar_padding(quadros_finais_enlace, 4)

    # 3.1 - Codificador Banda Base / Modulação Digital (NRZ-Polar, Manchester, Bipolar)
    sinal_banda_base = CamadaFisica.codificacao_digital(quadros_finais_enlace, configuracoes['tipo_modulacao_digital'])
    
    # 3.2 - Modulador / Modulação por Portadora (ASK, FSK, QPSK, 16-QAM)
    sinal_modulado = CamadaFisica.modulacao_portadora(sinal_banda_base, configuracoes['tipo_modulacao_analogica'])
    
    print("--- TRANSMISSÃO FINALIZADA ---")
    
    # Retorna o sinal para o Simulador.py, que vai aplicar o ruído e enviar pro receptor.py
    return sinal_modulado