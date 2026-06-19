import CamadaFisica
import CamadaEnlace
import utils


def iniciar_recepcao(sinal, config):
    """
    Função principal que orquestra o Fluxo RX: sinal -> física -> enlace -> bits -> texto.
    
    :parâmetro sinal: O sinal recebido do meio de comunicação.
    
    :parâmetro config: Dicionário contendo os parâmetros escolhidos na GUI:
        - 'tipo_modulacao_analogica': 'ASK', 'FSK', 'PSK', 'QPSK', '16-QAM' ou 'nenhum'
        - 'tipo_modulacao_digital': 'NRZ-Polar', 'Manchester', 'Bipolar' ou 'nenhum'
        - 'tipo_enquadramento': 'Contagem de caracteres', 'Inserção de bytes', 'Inserção de bits' ou 'nenhum'
        - 'tipo_edc': 'Paridade', 'Checksum', 'CRC-32', 'Hamming' ou 'nenhum'
    
    :return: Dicionário com as seguintes chaves:
        - 'mensagem': O texto decodificado a partir dos bits.
        - 'bits_fisicos': A lista de bits obtida após a camada física.
        - 'bits_enlace': A lista de bits após o desenquadramento na camada de enlace.
        - 'bits_enlace_erro_corrigidos': A lista de bits após a correção de erros na camada de enlace (se aplicável).
    """

    # ==========================================
    # 1. CAMADA FÍSICA
    # ==========================================

    #    1.1 Demodulação por portadora (ASK / FSK / PSK / QPSK / 16-QAM)
    tipo_portadora = config['tipo_modulacao_analogica']
    if tipo_portadora != 'nenhum':
        bits = CamadaFisica.demodulator(sinal, tipo_portadora)
    
    #    1.2 Decodificação banda-base (NRZ-Polar / Manchester / Bipolar)
    else:
        tipo_digital = config['tipo_modulacao_digital']
        bits = CamadaFisica.decoder(sinal, tipo_digital)

    bits_fisicos = list(bits)


    # ==========================================
    # 2. CAMADA DE ENLACE DE DADOS
    # ==========================================

    # 2.1 Desenquadramento (contagem de caracteres / inserção de bytes / inserção de bits)
    # Remove os cabeçalhos inseridos pelo TX e recupera os bits de dados.
    tipo = config['tipo_enquadramento']
    
    if tipo == 'Contagem de caracteres':
        bits = CamadaEnlace.deframing_char_count(bits)
    elif tipo == 'Inserção de bytes':
        bits = CamadaEnlace.deframing_byte_stuffing(bits)
    elif tipo == 'Inserção de bits':
        bits = CamadaEnlace.deframing_bit_stuffing(bits)

    bits_enlace = list(bits)

    # 2.2 Verificação e correção de  erros (paridade / checksum / CRC-32 / Hamming)
    
    '''
    TODO: Caso exista essa função na camada de enlace, caso contrário corrijo colocando os if's para cada tipo de EDC
    '''
    
    # Verificação de erros (paridade / checksum / CRC-32)
    # Corrige erros (Hamming)

    bits   = CamadaEnlace.remover_controle_erro(bits_enlace, config['tipo_edc']) 
    bits_enlace_erro_corrigidos = list(bits)

    # ==========================================
    # 3. APLICAÇÃO DE REDE
    # ==========================================
    
    # 3.1 Conversão bits para texto
    # Agrupa os bits em bytes (8 bits) e reconstrói a mensagem original.
    mensagem = utils.bits_para_texto(bits)

    return {
        "mensagem": mensagem,
        "bits_fisicos": bits_fisicos,
        "bits_enlace": bits_enlace,
        "bits_enlace_erro_corrigidos": bits_enlace_erro_corrigidos
    }   