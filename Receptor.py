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

    print("--- INICIANDO RECEPÇÃO ---")

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
    print(f"Física: Demodulação/Decodificação concluída, obtidos {len(bits_fisicos)} bits.")


    # ==========================================
    # 2. CAMADA DE ENLACE DE DADOS
    # ==========================================

    # 2.1 Desenquadramento -> lista de quadros (cada um = payload + EDC/ECC).
    # Remove as flags/cabeçalhos inseridos pelo TX e separa os quadros.
    tipo = config['tipo_enquadramento']
    quadros = CamadaEnlace.remover_enquadramento(bits, tipo)
    bits_enlace = [bit for quadro in quadros for bit in quadro]  # achatado, p/ exibição
    print(f"Enlace: Desenquadramento concluído, obtidos {len(bits_enlace)} bits.")

    # 2.2 Verificação (paridade / checksum / CRC-32) e 2.3 Correção (Hamming), por quadro.
    # O Hamming corrige 1 bit antes de remover os bits de paridade.
    tipo_edc = config['tipo_edc']
    k = config.get('tamanho_checksum', CamadaEnlace.TAMANHO_CHECKSUM_BITS)

    bits = []
    edc_ok = True
    for quadro in quadros:
        payload, ok = CamadaEnlace.verificar_e_remover_controle_erro(quadro, tipo_edc, k)
        bits.extend(payload)
        edc_ok = edc_ok and ok

    bits_enlace_erro_corrigidos = list(bits)
    print(f"Enlace: Verificação e correção de erros concluídas, obtidos {len(bits_enlace_erro_corrigidos)} bits.")

    # ==========================================
    # 3. APLICAÇÃO DE REDE
    # ==========================================
    
    # 3.1 Conversão bits para texto
    # Agrupa os bits em bytes (8 bits) e reconstrói a mensagem original.
    mensagem = utils.bits_para_texto(bits) 
    print(f"Aplicação: Bits convertidos em texto, obtida a mensagem: '{mensagem}'.")

    print("--- RECEPÇÃO FINALIZADA ---")

    return {
        "mensagem": mensagem,
        "bits_fisicos": bits_fisicos,
        "bits_enlace": bits_enlace,
        "bits_enlace_erro_corrigidos": bits_enlace_erro_corrigidos,
        "edc_ok": edc_ok,
    }   