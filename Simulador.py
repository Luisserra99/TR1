import CamadaFisica
from Transmissor import iniciar_transmissao
from Receptor import iniciar_recepcao

def simular(mensagem, config):
    """
    Função que simula o fluxo completo de transmissão e recepção de uma mensagem.
    :parâmetro mensagem: A string digitada pelo usuário na InterfaceGUI.
    :parâmetro configuracoes: Dicionário contendo os parâmetros escolhidos na GUI.
    :return: A mensagem recebida após todo o processo de transmissão e recepção.
    """
    print("=== SIMULAÇÃO DE FLUXO COMPLETO ===")
    
    # Inicia a transmissão da mensagem
    sinal_tx  = iniciar_transmissao(mensagem, config)
    
    # Aplica o ruído ao sinal transmitido
    x = config["ruido_media"]
    sigma = config["ruido_desvio"]
    sinal_rx  = CamadaFisica.aplicar_ruido(sinal_tx, x, sigma)
    
    # Simula a recepção do sinal transmitido
    resultado = iniciar_recepcao(sinal_rx, config)
    
    print("=== SIMULAÇÃO CONCLUÍDA ===")
    return resultado


# Execução direta para teste rápido sem GUI
if __name__ == '__main__':
    config_teste = {
        'tipo_edc'           : 'Hamming',
        'tipo_enquadramento' : 'Inserção de bytes',
        'tamanho_maximo_quadro': 32,
        'tamanho_checksum'   : 16,
        'tipo_modulacao_digital'   : 'nenhum',
        'tipo_modulacao_analogica' : 'ASK',
        'ruido_media'   : 0.0,
        'ruido_desvio'  : 0.0,
    }

    texto = input('Mensagem a transmitir: ').strip()
    if not texto:
        texto = 'UnB TR1'

    resultado = simular(texto, config_teste)
    
    print(resultado)
    
    sep = '─' * 50
    print(sep)
    print(f'TX enviou : {texto}')
    print(f'RX recebeu: {resultado["mensagem"]}')
    print(f'EDC OK    : {resultado["edc_ok"]}')
