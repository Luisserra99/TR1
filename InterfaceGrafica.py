"""Interface Gráfica (GTK 3 + Matplotlib) do simulador de TR1.

O programa roda em DUAS instâncias separadas, escolhidas na linha de comando:

    python InterfaceGrafica.py --modo rx     # RECEPTOR:    abra primeiro; fica ouvindo
    python InterfaceGrafica.py --modo tx     # TRANSMISSOR: codifica e envia o sinal

As duas conversam pelo "meio de comunicação" (Figura 1 do enunciado), aqui um socket TCP
LOCAL e fixo (127.0.0.1:5001). O ruído gaussiano n(x, σ) é aplicado no lado TX (o canal),
logo antes do envio; o RX recebe o sinal já ruidoso, junto da configuração usada, e o
decodifica:

    sinal_tx  = Transmissor.iniciar_transmissao(texto, config)
    sinal_rx  = CamadaFisica.aplicar_ruido(sinal_tx, x, sigma)   # canal (ruído)
    resultado = Receptor.iniciar_recepcao(sinal_rx, config)
"""

import argparse          # leitura do argumento --modo
import pickle            # serializa o dicionário {config, sinal} para enviar pelo socket
import socket            # o "meio de comunicação" entre TX e RX
import struct            # cabeçalho de tamanho (4 bytes) de cada mensagem TCP
import threading         # o RX escuta o socket numa thread separada (não trava a GUI)

import gi
gi.require_version("Gtk", "3.0")            # exige GTK 3 antes de importar do repositório
from gi.repository import Gtk, GLib         # Gtk = widgets; GLib = volta p/ a thread da GUI

# Matplotlib embarcado no GTK (sem pyplot): Figure desenha; FigureCanvas vira um widget GTK.
from matplotlib.figure import Figure
from matplotlib.backends.backend_gtk3cairo import FigureCanvasGTK3Cairo as FigureCanvas

# Backend do simulador (camadas já implementadas).
import utils
import CamadaFisica
import Transmissor
import Receptor

# ----------------------------------------------------------------------------------
# Opções dos menus. As strings são EXATAMENTE as que o backend espera (senão dá erro).
# ----------------------------------------------------------------------------------
DIGITAIS = ["NRZ-Polar", "Manchester", "Bipolar"]
PORTADORAS = ["nenhum", "ASK", "FSK", "PSK", "QPSK", "16-QAM"]
ENQUADRAMENTOS = ["Contagem de caracteres", "Inserção de bytes", "Inserção de bits", "nenhum"]
EDCS = ["nenhum", "Paridade", "Checksum", "CRC-32", "Hamming"]

# Conexão local fixa do "meio" (sem configuração de host/porta).
HOST = "127.0.0.1"
PORTA = 5001


# ==================================================================================
#  "Meio de comunicação": como uma mensagem trafega no socket TCP.
#  Cada mensagem = 4 bytes com o tamanho + os bytes do objeto (pickle). O tamanho é
#  necessário porque o TCP é um fluxo contínuo: ele diz onde a mensagem termina.
# ==================================================================================

def enviar_mensagem(sock, objeto):
    """Empacota o objeto com pickle e o envia precedido do seu tamanho (4 bytes)."""
    dados = pickle.dumps(objeto)                          # objeto -> bytes
    sock.sendall(struct.pack("!I", len(dados)) + dados)   # tamanho + conteúdo


def _receber_n(sock, n):
    """Lê EXATAMENTE n bytes do socket (recv pode devolver menos de uma vez)."""
    buffer = b""
    while len(buffer) < n:
        pedaco = sock.recv(n - len(buffer))
        if not pedaco:                # conexão fechou antes de completar -> aborta
            return None
        buffer += pedaco
    return buffer


def receber_mensagem(sock):
    """Lê o tamanho (4 bytes), depois o conteúdo, e devolve o objeto desempacotado."""
    cabecalho = _receber_n(sock, 4)
    if cabecalho is None:
        return None
    (tamanho,) = struct.unpack("!I", cabecalho)           # 4 bytes -> inteiro
    corpo = _receber_n(sock, tamanho)
    if corpo is None:
        return None
    return pickle.loads(corpo)                            # bytes -> objeto


# ==================================================================================
#  Janela principal. O papel (TX ou RX) é definido por self.modo.
# ==================================================================================

class JanelaSimulador(Gtk.Window):
    def __init__(self, modo):
        self.modo = modo                                  # "tx" ou "rx"
        papel = "Transmissor" if modo == "tx" else "Receptor"
        super().__init__(title=f"Simulador TR1 — {papel}")
        self.set_default_size(1000, 550)
        self.set_border_width(8)

        # Aumenta a fonte de toda a interface
        css = Gtk.CssProvider()
        css.load_from_data(b"* { font-size: 18pt; }")
        Gtk.StyleContext.add_provider_for_screen(
            self.get_screen(), css, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

        # Layout: painel de configuração à esquerda, painel de saídas à direita.
        raiz = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=14)
        self.add(raiz)
        raiz.pack_start(self._painel_config(), False, False, 0)
        raiz.pack_start(self._painel_saidas(), True, True, 0)

        # No Receptor a config é só informativa (vem do TX) e o servidor começa a ouvir.
        if self.modo == "rx":
            self._definir_config_sensivel(False)
            self._iniciar_servidor()

    # -------------------------------------------------------------- painel de config
    def _painel_config(self):
        """Monta a coluna de entradas (mensagem, parâmetros e, no TX, o botão)."""
        grade = Gtk.Grid(row_spacing=6, column_spacing=8)
        self._linha = 0

        def add(rotulo, widget):                          # rótulo na col. 0, widget na col. 1
            grade.attach(Gtk.Label(label=rotulo, xalign=0), 0, self._linha, 1, 1)
            grade.attach(widget, 1, self._linha, 1, 1)
            self._linha += 1

        # Campos de entrada.
        self.entry_msg = Gtk.Entry(text="Esse Trabalho merce um SS!!!")
        self.spin_quadro = Gtk.SpinButton.new_with_range(8, 208, 8)      # tam. máx. quadro (bits)
        self.spin_quadro.set_value(64)
        self.spin_k = Gtk.SpinButton.new_with_range(4, 32, 4)            # k do checksum (bits)
        self.spin_k.set_value(8)
        self.cmb_enq = self._combo(ENQUADRAMENTOS)
        self.cmb_edc = self._combo(EDCS)
        self.cmb_dig = self._combo(DIGITAIS)
        self.cmb_por = self._combo(PORTADORAS)
        self.spin_x = Gtk.SpinButton.new_with_range(-2.0, 2.0, 0.05)     # ruído: média
        self.spin_sigma = Gtk.SpinButton.new_with_range(0.0, 3.0, 0.05)  # ruído: desvio
        self.spin_x.set_digits(2)
        self.spin_sigma.set_digits(2)
        self.spin_x.set_value(0.0)
        self.spin_sigma.set_value(0.10)

        add("Mensagem:", self.entry_msg)
        add("Tam. máx. quadro:", self.spin_quadro)
        add("Enquadramento:", self.cmb_enq)
        add("Detecção/Correção:", self.cmb_edc)
        add("Tam. checksum (k):", self.spin_k)
        add("Modulação digital:", self.cmb_dig)
        add("Modulação portadora:", self.cmb_por)
        add("Ruído — média (x):", self.spin_x)
        add("Ruído — desvio padrão (σ):", self.spin_sigma)

        # Só o Transmissor tem o botão de enviar.
        if self.modo == "tx":
            botao = Gtk.Button(label="▶  TRANSMITIR")
            botao.connect("clicked", self._on_transmitir)
            grade.attach(botao, 0, self._linha, 2, 1)
            self._linha += 1

        # Linha de status (mensagens curtas para o usuário).
        self.lbl_status = Gtk.Label(xalign=0)
        self.lbl_status.set_line_wrap(True)
        grade.attach(self.lbl_status, 0, self._linha, 2, 1)
        return grade

    def _combo(self, itens):
        """Cria um menu suspenso já preenchido com 'itens' e a 1ª opção selecionada."""
        c = Gtk.ComboBoxText()
        for it in itens:
            c.append_text(it)
        c.set_active(0)
        return c

    def _definir_config_sensivel(self, sensivel):
        """Habilita/desabilita os campos de config (o RX usa False: apenas leitura)."""
        for w in (self.entry_msg, self.spin_quadro, self.spin_k, self.cmb_enq,
                  self.cmb_edc, self.cmb_dig, self.cmb_por, self.spin_x, self.spin_sigma):
            w.set_sensitive(sensivel)

    # -------------------------------------------------------------- painel de saídas
    def _painel_saidas(self):
        """Monta a área da direita: aba de texto/bits + aba de gráficos."""
        nb = Gtk.Notebook()

        # Aba 1 — texto e bits.
        cx = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        cx.set_border_width(6)
        self.lbl_texto_tx = self._label_saida()
        self.lbl_texto_rx = self._label_saida()
        self.lbl_bits_tx = self._label_saida()
        self.lbl_bits_rx = self._label_saida()
        self.lbl_edc = self._label_saida()

        # As linhas exibidas dependem do papel.
        if self.modo == "tx":
            linhas = [("Texto transmitido:", self.lbl_texto_tx),
                      ("Bits transmitidos:", self.lbl_bits_tx)]
        else:
            linhas = [("Texto enviado (TX):", self.lbl_texto_tx),
                      ("Texto recuperado (RX):", self.lbl_texto_rx),
                      ("Bits recebidos (RX):", self.lbl_bits_rx),
                      ("Status EDC:", self.lbl_edc)]
        for rotulo, widget in linhas:
            cx.pack_start(self._linha_saida(rotulo, widget), False, False, 0)
        sw_texto = Gtk.ScrolledWindow()
        sw_texto.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        sw_texto.add(cx)
        nb.append_page(sw_texto, Gtk.Label(label="Texto & Bits"))

        # Aba 2 — gráficos. TX mostra 2 (limpo/ruidoso); RX mostra 1 (recebido).
        self.figura = Figure(figsize=(6, 4), tight_layout=True)
        if self.modo == "tx":
            self.ax_tx = self.figura.add_subplot(211)
            self.ax_rx = self.figura.add_subplot(212)
        else:
            self.ax_tx = None
            self.ax_rx = self.figura.add_subplot(111)
        self.canvas = FigureCanvas(self.figura)           # a figura vira um widget GTK
        nb.append_page(self.canvas, Gtk.Label(label="Gráficos"))
        return nb

    def _label_saida(self):
        """Label de saída: quebra linha e permite selecionar/copiar o texto."""
        lbl = Gtk.Label(xalign=0)
        lbl.set_line_wrap(True)
        lbl.set_selectable(True)
        return lbl

    def _linha_saida(self, rotulo, widget):
        """Uma linha 'rótulo em negrito: valor' do painel de saídas."""
        linha = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        rot = Gtk.Label(xalign=0)
        rot.set_markup(f"<b>{rotulo}</b>")
        linha.pack_start(rot, False, False, 0)
        linha.pack_start(widget, True, True, 0)
        return linha

    # -------------------------------------------------------------- utilidades
    def _ler_configuracoes(self):
        """Lê os widgets e monta o dicionário de configuração que o backend espera."""
        return {
            "tamanho_maximo_quadro": int(self.spin_quadro.get_value()),
            "tamanho_checksum": int(self.spin_k.get_value()),
            "tipo_enquadramento": self.cmb_enq.get_active_text(),
            "tipo_edc": self.cmb_edc.get_active_text(),
            "tipo_modulacao_digital": self.cmb_dig.get_active_text(),
            "tipo_modulacao_analogica": self.cmb_por.get_active_text(),
            "ruido_media": float(self.spin_x.get_value()),
            "ruido_desvio": float(self.spin_sigma.get_value()),
        }

    def _aplicar_config_nos_widgets(self, cfg):
        """RX: mostra nos menus a configuração que veio do TX (apenas informativo)."""
        self.spin_quadro.set_value(cfg.get("tamanho_maximo_quadro", 64))
        self.spin_k.set_value(cfg.get("tamanho_checksum", 8))
        self.spin_x.set_value(cfg.get("ruido_media", 0.0))
        self.spin_sigma.set_value(cfg.get("ruido_desvio", 0.10))
        for combo, itens, chave in (
            (self.cmb_enq, ENQUADRAMENTOS, "tipo_enquadramento"),
            (self.cmb_edc, EDCS, "tipo_edc"),
            (self.cmb_dig, DIGITAIS, "tipo_modulacao_digital"),
            (self.cmb_por, PORTADORAS, "tipo_modulacao_analogica"),
        ):
            valor = cfg.get(chave)
            if valor in itens:
                combo.set_active(itens.index(valor))

    def _fmt_bits(self, bits):
        """Converte a lista de bits em texto, cortando se for muito longa."""
        s = "".join(str(b) for b in bits)
        return s if len(s) <= 512 else s[:512] + f"… ({len(s)} bits)"

    def _plotar(self, ax, sinal, titulo):
        """Desenha os primeiros ~40 bits do sinal (o sinal inteiro é grande demais)."""
        ax.clear()
        n = min(len(sinal), 40 * CamadaFisica.AMOSTRAS_POR_BIT)
        ax.plot(sinal[:n], linewidth=2)
        ax.set_title(titulo, fontsize=22)
        ax.set_ylabel("V/W", fontsize=22)
        ax.grid(True)

    def _status(self, texto):
        """Atualiza a linha de status."""
        self.lbl_status.set_text(texto)

    def _dialogo_erro(self, msg):
        """Mostra uma janela de erro (mensagem curta)."""
        d = Gtk.MessageDialog(transient_for=self, modal=True,
                              message_type=Gtk.MessageType.ERROR,
                              buttons=Gtk.ButtonsType.OK, text="Erro na simulação")
        d.format_secondary_text(msg)
        d.run()
        d.destroy()

    # -------------------------------------------------------------- TRANSMISSOR
    def _on_transmitir(self, _botao):
        """Clique em TRANSMITIR: gera o sinal, aplica ruído, mostra e envia ao RX."""
        try:
            cfg = self._ler_configuracoes()
            texto = self.entry_msg.get_text()
            x = self.spin_x.get_value()
            sigma = self.spin_sigma.get_value()

            # Pipeline: texto -> sinal limpo -> sinal com ruído (o "canal").
            sinal_tx = Transmissor.iniciar_transmissao(texto, cfg)
            sinal_rx = CamadaFisica.aplicar_ruido(sinal_tx, x, sigma)

            # Mostra o lado transmissor (texto, bits e os dois gráficos).
            self.lbl_texto_tx.set_text(texto)
            self.lbl_bits_tx.set_text(self._fmt_bits(utils.texto_para_bits(texto)))
            self._plotar(self.ax_tx, sinal_tx, "Sinal transmitido (limpo)")
            self._plotar(self.ax_rx, sinal_rx, f"Enviado ao meio (ruído x={x:.2f}, σ={sigma:.2f})")
            self.canvas.draw()

            # Envia {config, sinal ruidoso, texto} ao Receptor pelo socket local.
            payload = {"config": cfg, "sinal": sinal_rx, "texto_tx": texto}
            with socket.create_connection((HOST, PORTA), timeout=5) as s:
                enviar_mensagem(s, payload)
            self._status("Enviado ao Receptor ✓")
        except OSError:
            self._dialogo_erro("Não foi possível conectar. O Receptor está rodando?")
        except Exception as ex:
            self._dialogo_erro(f"{type(ex).__name__}: {ex}")

    # -------------------------------------------------------------- RECEPTOR
    def _iniciar_servidor(self):
        """Inicia, numa thread separada, o servidor que escuta o socket."""
        self._status("Aguardando o Transmissor …")
        threading.Thread(target=self._loop_servidor, daemon=True).start()

    def _loop_servidor(self):
        """Em segundo plano: aceita conexões e recebe um sinal por vez.
        Não pode mexer nos widgets aqui (outra thread) -> usa GLib.idle_add."""
        srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)   # reabrir a porta sem esperar
        srv.bind((HOST, PORTA))
        srv.listen(1)
        while True:
            conexao, _ = srv.accept()          # bloqueia até o TX conectar
            try:
                msg = receber_mensagem(conexao)
            finally:
                conexao.close()
            if msg is not None:
                # Devolve o processamento para a thread principal da GUI.
                GLib.idle_add(self._processar_recebido, msg)

    def _processar_recebido(self, msg):
        """Na thread da GUI: decodifica o sinal recebido e mostra os resultados."""
        try:
            cfg = msg["config"]
            sinal = msg["sinal"]
            self._aplicar_config_nos_widgets(cfg)          # reflete a config usada pelo TX

            resultado = Receptor.iniciar_recepcao(sinal, cfg)

            self.lbl_texto_tx.set_text(msg.get("texto_tx", "—"))
            self.lbl_texto_rx.set_text(resultado["mensagem"])
            self.lbl_bits_rx.set_text(self._fmt_bits(resultado["bits_enlace_erro_corrigidos"]))
            # Verde = sem erro; vermelho = erro detectado pelo EDC.
            if resultado["edc_ok"]:
                self.lbl_edc.set_markup("<span foreground='green'><b>✓ sem erro</b></span>")
            else:
                self.lbl_edc.set_markup("<span foreground='red'><b>✗ erro detectado</b></span>")

            self._plotar(self.ax_rx, sinal, "Sinal recebido")
            self.canvas.draw()
            self._status("Recebido ✓ — aguardando próxima transmissão …")
        except Exception as ex:
            self._dialogo_erro(f"{type(ex).__name__}: {ex}")
        return False   # GLib.idle_add: executa só uma vez


# ==================================================================================
#  Ponto de entrada: lê --modo e abre a janela no papel escolhido.
# ==================================================================================

def main():
    parser = argparse.ArgumentParser(description="GUI do simulador de TR1 (TX ou RX).")
    parser.add_argument("--modo", "-m", required=True, choices=["tx", "rx"],
                        help="digite (--modo tx - para transmissor) ou (--modo rx - para receptor)")
    args = parser.parse_args()

    janela = JanelaSimulador(args.modo)
    janela.connect("destroy", Gtk.main_quit)    # fechar a janela encerra o programa
    janela.show_all()
    Gtk.main()                                   # laço de eventos do GTK


if __name__ == "__main__":
    main()
