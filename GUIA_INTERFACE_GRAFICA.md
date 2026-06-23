# Guia de Implementação — `InterfaceGrafica.py` (GTK + Matplotlib)

> Complemento do `GUIA_IMPLEMENTACAO.md` (§9). Roteiro para construir a GUI exigida pela
> Seção 2 do enunciado: **configuração** dos parâmetros + **exibição gráfica** dos sinais,
> ligada ao backend já implementado (`Transmissor.py` / `Receptor.py` / `CamadaFisica.py`).
> **Proibido** terminal: a interface tem de ser gráfica (recomendação do enunciado: **GTK**).

---

## 1. Bibliotecas solicitadas

| Biblioteca | Papel | Import |
|---|---|---|
| **PyGObject (GTK 3)** | Janela, widgets de configuração, layout | `gi` → `gi.repository.Gtk` |
| **Matplotlib** | Gráficos dos sinais (TX/RX) | `matplotlib.figure.Figure` |
| **Backend GTK3Agg** | Embute a figura Matplotlib dentro do GTK | `backend_gtk3agg.FigureCanvasGTK3Agg` |
| **Cairo (PyCairo)** | Renderização (dependência do GTK3Agg) | implícito |
| NumPy | Já usado pela camada física (arrays de sinal) | `numpy` |

Instalação (Debian/Ubuntu — igual ao `GUIA_IMPLEMENTACAO.md` §3):

```bash
sudo apt install python3-gi python3-gi-cairo gir1.2-gtk-3.0
pip install pycairo PyGObject numpy matplotlib
python InterfaceGrafica.py   # abre a janela
```

> Verificado neste projeto: `PyGObject/GTK3 OK` e `matplotlib GTK3Agg OK`.

---

## 2. Contrato de integração (NÃO IMPROVISAR — use exatamente estas chaves/strings)

A GUI só monta um **dicionário de configuração** e chama 3 funções. As strings têm de ser
**idênticas** às esperadas pelos despachantes do backend, senão eles levantam `ValueError`.

### 2.1 Dicionário `config` (lido por `Transmissor` e `Receptor`)

| Chave | Tipo | Valores válidos |
|---|---|---|
| `tamanho_maximo_quadro` | `int` | ex.: 8…512 (bits de payload por quadro) |
| `tipo_edc` | `str` | `'nenhum'`, `'Paridade'`, `'Checksum'`, `'CRC-32'`, `'Hamming'` |
| `tamanho_checksum` | `int` | `k` em bits (ex.: 8) — só usado se `tipo_edc='Checksum'` |
| `tipo_enquadramento` | `str` | `'nenhum'`, `'Contagem de caracteres'`, `'Inserção de bytes'`, `'Inserção de bits'` |
| `tipo_modulacao_digital` | `str` | `'NRZ-Polar'`, `'Manchester'`, `'Bipolar'`, `'nenhum'` |
| `tipo_modulacao_analogica` | `str` | `'ASK'`, `'FSK'`, `'PSK'`, `'QPSK'`, `'16-QAM'`, `'nenhum'` |

> **Regra da física (modelo de seleção):** é **OU portadora OU banda-base**. Se
> `tipo_modulacao_analogica != 'nenhum'`, a portadora é usada e a digital é ignorada; caso
> contrário, usa-se a digital. Na GUI, deixe o usuário escolher uma das duas (a outra fica
> em `'nenhum'`).

Os valores de **ruído** (`x` = média, `σ` = desvio) **não** vão no `config`: são passados
direto para `aplicar_ruido` na hora de simular.

### 2.2 As 3 chamadas (orquestração da simulação)

```python
import Transmissor, Receptor, CamadaFisica

sinal_tx = Transmissor.iniciar_transmissao(texto, config)      # texto -> sinal limpo (np.ndarray)
sinal_rx = CamadaFisica.aplicar_ruido(sinal_tx, x, sigma)      # meio: + ruído gaussiano n(x,σ)
resultado = Receptor.iniciar_recepcao(sinal_rx, config)        # sinal -> dict
```

### 2.3 Retorno de `Receptor.iniciar_recepcao` (para preencher as saídas)

| Chave | Conteúdo | Onde exibir |
|---|---|---|
| `resultado['mensagem']` | texto recuperado (`str`) | **Texto RX** |
| `resultado['bits_fisicos']` | bits logo após a camada física | Bits RX (pós-física) |
| `resultado['bits_enlace']` | bits após desenquadramento | Bits RX (quadros) |
| `resultado['bits_enlace_erro_corrigidos']` | bits de dados finais | **Bits RX** |
| `resultado['edc_ok']` | `bool` — `False` = erro detectado | **Status** (LED/label) |

Para o lado **TX**: o texto é o próprio `Entry`; os **bits TX** saem de
`utils.texto_para_bits(texto)`; o **sinal TX** é o `sinal_tx` retornado.

---

## 3. Layout da janela

```
┌───────────────────────────── InterfaceGrafica (Gtk.Window) ─────────────────────────────┐
│ ┌─────────────── CONFIGURAÇÃO (Gtk.Grid) ───────────────┐ ┌──── SAÍDAS (Gtk.Notebook) ───┐ │
│ │ Mensagem:            [ Gtk.Entry              ]        │ │ Aba "Texto & Bits":          │ │
│ │ Tam. máx. quadro:    [ SpinButton ]                   │ │   Texto TX / Texto RX        │ │
│ │ Enquadramento:       [ ComboBoxText ▼ ]               │ │   Bits  TX / Bits  RX        │ │
│ │ Detecção/Correção:   [ ComboBoxText ▼ ]  k:[Spin]     │ │   Status EDC: ● ok / ✗ erro  │ │
│ │ Modulação digital:   [ ComboBoxText ▼ ]               │ ├──────────────────────────────┤ │
│ │ Modulação portadora: [ ComboBoxText ▼ ]               │ │ Aba "Gráficos":              │ │
│ │ Ruído  x:[Spin]  σ:[Spin]                             │ │   [ canvas Matplotlib TX ]   │ │
│ │            [   ▶  SIMULAR   ]                          │ │   [ canvas Matplotlib RX ]   │ │
│ └───────────────────────────────────────────────────────┘ └──────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────────────────────────────┘
```

Container raiz: `Gtk.Box(HORIZONTAL)` com painel de config à esquerda e `Gtk.Notebook`
(abas) à direita. Dentro da config, um `Gtk.Grid` (rótulo na coluna 0, widget na coluna 1).

---

## 4. Widgets de configuração (mapeamento parâmetro → widget)

| Parâmetro | Widget GTK | Como popular / ler |
|---|---|---|
| Mensagem | `Gtk.Entry` | `entry.get_text()` |
| Tam. máx. quadro | `Gtk.SpinButton` (8…512, passo 8) | `int(spin.get_value())` |
| Tam. checksum `k` | `Gtk.SpinButton` (4…32, passo 4) | `int(spin.get_value())` |
| Enquadramento | `Gtk.ComboBoxText` | `combo.get_active_text()` |
| Detecção/Correção | `Gtk.ComboBoxText` | idem |
| Modulação digital | `Gtk.ComboBoxText` | idem |
| Modulação portadora | `Gtk.ComboBoxText` | idem |
| Ruído x, σ | 2× `Gtk.SpinButton` (float) | `spin.get_value()` |

> **Popule os combos com as strings EXATAS da tabela §2.1** (`append_text("CRC-32")`
> etc.). O `get_active_text()` devolve a string verbatim, que vai direto no `config`.

---

## 5. Gráficos com Matplotlib embarcado

```python
from matplotlib.figure import Figure
from matplotlib.backends.backend_gtk3agg import FigureCanvasGTK3Agg as FigureCanvas

self.figura = Figure(figsize=(6, 4), tight_layout=True)
self.ax_tx = self.figura.add_subplot(211)   # sinal transmitido
self.ax_rx = self.figura.add_subplot(212)   # sinal recebido (com ruído)
self.canvas = FigureCanvas(self.figura)      # é um Gtk.Widget -> entra no Notebook
```

Helper de plotagem (limite a janela de amostras — o sinal inteiro é enorme):

```python
def _plotar(self, ax, sinal, titulo):
    ax.clear()
    n = min(len(sinal), 40 * CamadaFisica.AMOSTRAS_POR_BIT)  # ~40 bits p/ leitura
    ax.plot(sinal[:n], linewidth=0.8)
    ax.set_title(titulo); ax.set_xlabel("amostras"); ax.set_ylabel("V/W"); ax.grid(True)
```

Depois de plotar TX e RX: `self.canvas.draw()`.

---

## 6. Callback do botão "Simular" (coração da GUI)

```python
def _on_simular(self, _botao):
    try:
        cfg = self._ler_configuracoes()              # monta o dict da §2.1
        texto = self.entry_msg.get_text()
        x = self.spin_x.get_value(); sigma = self.spin_sigma.get_value()

        # --- pipeline: TX -> meio (ruído) -> RX  (§2.2) ---
        sinal_tx = Transmissor.iniciar_transmissao(texto, cfg)
        sinal_rx = CamadaFisica.aplicar_ruido(sinal_tx, x, sigma)
        resultado = Receptor.iniciar_recepcao(sinal_rx, cfg)

        # --- saídas de texto/bits ---
        self.lbl_texto_tx.set_text(texto)
        self.lbl_texto_rx.set_text(resultado['mensagem'])
        self.lbl_bits_tx.set_text(self._fmt_bits(utils.texto_para_bits(texto)))
        self.lbl_bits_rx.set_text(self._fmt_bits(resultado['bits_enlace_erro_corrigidos']))
        self.lbl_status.set_markup(
            "<b>EDC: ✓ sem erro</b>" if resultado['edc_ok'] else "<b>EDC: ✗ erro detectado</b>")

        # --- gráficos ---
        self._plotar(self.ax_tx, sinal_tx, "Sinal Transmitido (limpo)")
        self._plotar(self.ax_rx, sinal_rx, f"Sinal Recebido (ruído x={x}, σ={sigma})")
        self.canvas.draw()
    except Exception as ex:
        self._dialogo_erro(f"{type(ex).__name__}: {ex}")   # ex.: combinação inválida
```

> `_fmt_bits` = `''.join(map(str, bits))` (corte em ~256 chars para não travar a label).
> `_dialogo_erro` = `Gtk.MessageDialog(...)`. Útil porque strings de config erradas geram
> `ValueError` legível.

---

## 7. Esqueleto completo (`InterfaceGrafica.py`)

```python
import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GLib

from matplotlib.figure import Figure
from matplotlib.backends.backend_gtk3agg import FigureCanvasGTK3Agg as FigureCanvas

import utils, CamadaFisica, Transmissor, Receptor

DIGITAIS   = ["NRZ-Polar", "Manchester", "Bipolar", "nenhum"]
PORTADORAS = ["nenhum", "ASK", "FSK", "PSK", "QPSK", "16-QAM"]
ENQUADRAM  = ["Contagem de caracteres", "Inserção de bytes", "Inserção de bits", "nenhum"]
EDCS       = ["nenhum", "Paridade", "Checksum", "CRC-32", "Hamming"]


class InterfaceGrafica(Gtk.Window):
    def __init__(self):
        super().__init__(title="Simulador TR1 — Camadas Física e de Enlace")
        self.set_default_size(1100, 650); self.set_border_width(8)

        raiz = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        self.add(raiz)
        raiz.pack_start(self._painel_config(), False, False, 0)
        raiz.pack_start(self._painel_saidas(), True, True, 0)

    # ---------- painel de configuração ----------
    def _painel_config(self):
        grade = Gtk.Grid(row_spacing=6, column_spacing=8)
        lin = 0
        def add(rotulo, widget):
            nonlocal lin
            grade.attach(Gtk.Label(label=rotulo, xalign=0), 0, lin, 1, 1)
            grade.attach(widget, 1, lin, 1, 1); lin += 1

        self.entry_msg = Gtk.Entry(text="Olá, TR1!")
        self.spin_quadro = Gtk.SpinButton.new_with_range(8, 512, 8); self.spin_quadro.set_value(64)
        self.spin_k = Gtk.SpinButton.new_with_range(4, 32, 4); self.spin_k.set_value(8)
        self.cmb_enq = self._combo(ENQUADRAM)
        self.cmb_edc = self._combo(EDCS)
        self.cmb_dig = self._combo(DIGITAIS)
        self.cmb_por = self._combo(PORTADORAS)
        self.spin_x = Gtk.SpinButton.new_with_range(-2, 2, 0.05); self.spin_x.set_value(0.0)
        self.spin_sigma = Gtk.SpinButton.new_with_range(0, 3, 0.05); self.spin_sigma.set_value(0.10)
        self.spin_x.set_digits(2); self.spin_sigma.set_digits(2)

        add("Mensagem:", self.entry_msg)
        add("Tam. máx. quadro:", self.spin_quadro)
        add("Enquadramento:", self.cmb_enq)
        add("Detecção/Correção:", self.cmb_edc)
        add("Tam. checksum (k):", self.spin_k)
        add("Modulação digital:", self.cmb_dig)
        add("Modulação portadora:", self.cmb_por)
        add("Ruído — média (x):", self.spin_x)
        add("Ruído — desvio (σ):", self.spin_sigma)

        botao = Gtk.Button(label="▶  SIMULAR"); botao.connect("clicked", self._on_simular)
        grade.attach(botao, 0, lin, 2, 1)
        return grade

    def _combo(self, itens):
        c = Gtk.ComboBoxText()
        for it in itens: c.append_text(it)
        c.set_active(0); return c

    # ---------- painel de saídas ----------
    def _painel_saidas(self):
        nb = Gtk.Notebook()

        # aba 1: texto & bits
        cx = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self.lbl_texto_tx = Gtk.Label(xalign=0); self.lbl_texto_rx = Gtk.Label(xalign=0)
        self.lbl_bits_tx = Gtk.Label(xalign=0); self.lbl_bits_rx = Gtk.Label(xalign=0)
        self.lbl_status  = Gtk.Label(xalign=0)
        for r, w in [("Texto TX:", self.lbl_texto_tx), ("Texto RX:", self.lbl_texto_rx),
                     ("Bits TX:", self.lbl_bits_tx), ("Bits RX:", self.lbl_bits_rx),
                     ("Status:", self.lbl_status)]:
            linha = Gtk.Box(spacing=6)
            linha.pack_start(Gtk.Label(label=r), False, False, 0)
            linha.pack_start(w, True, True, 0); cx.pack_start(linha, False, False, 0)
        nb.append_page(cx, Gtk.Label(label="Texto & Bits"))

        # aba 2: gráficos
        self.figura = Figure(figsize=(6, 4), tight_layout=True)
        self.ax_tx = self.figura.add_subplot(211); self.ax_rx = self.figura.add_subplot(212)
        self.canvas = FigureCanvas(self.figura)
        nb.append_page(self.canvas, Gtk.Label(label="Gráficos"))
        return nb

    # ---------- helpers / callback ----------
    def _ler_configuracoes(self):
        return {
            "tamanho_maximo_quadro": int(self.spin_quadro.get_value()),
            "tamanho_checksum": int(self.spin_k.get_value()),
            "tipo_enquadramento": self.cmb_enq.get_active_text(),
            "tipo_edc": self.cmb_edc.get_active_text(),
            "tipo_modulacao_digital": self.cmb_dig.get_active_text(),
            "tipo_modulacao_analogica": self.cmb_por.get_active_text(),
        }

    def _fmt_bits(self, bits):
        s = "".join(map(str, bits))
        return s if len(s) <= 256 else s[:256] + f"… ({len(s)} bits)"

    def _plotar(self, ax, sinal, titulo):
        ax.clear()
        n = min(len(sinal), 40 * CamadaFisica.AMOSTRAS_POR_BIT)
        ax.plot(sinal[:n], linewidth=0.8)
        ax.set_title(titulo); ax.set_ylabel("V/W"); ax.grid(True)

    def _dialogo_erro(self, msg):
        d = Gtk.MessageDialog(transient_for=self, modal=True,
                              message_type=Gtk.MessageType.ERROR,
                              buttons=Gtk.ButtonsType.OK, text="Erro na simulação")
        d.format_secondary_text(msg); d.run(); d.destroy()

    def _on_simular(self, _botao):
        ...  # exatamente o corpo da §6

def main():
    win = InterfaceGrafica()
    win.connect("destroy", Gtk.main_quit)
    win.show_all()
    Gtk.main()

if __name__ == "__main__":
    main()
```

---

## 8. Concorrência (TX/RX em threads — Figura 1 do enunciado)

O enunciado pede TX e RX como **threads/processos separados**. Para não congelar a GUI
durante a simulação (e atender ao requisito), rode o pipeline numa worker thread e volte
para a interface com `GLib.idle_add`:

```python
import threading
from gi.repository import GLib

def _on_simular(self, _botao):
    cfg = self._ler_configuracoes(); texto = self.entry_msg.get_text()
    x, sigma = self.spin_x.get_value(), self.spin_sigma.get_value()
    threading.Thread(target=self._worker, args=(texto, cfg, x, sigma), daemon=True).start()

def _worker(self, texto, cfg, x, sigma):
    try:
        sinal_tx = Transmissor.iniciar_transmissao(texto, cfg)         # thread TX
        sinal_rx = CamadaFisica.aplicar_ruido(sinal_tx, x, sigma)      # meio
        resultado = Receptor.iniciar_recepcao(sinal_rx, cfg)           # thread RX
        GLib.idle_add(self._atualizar_gui, texto, sinal_tx, sinal_rx, resultado, x, sigma)
    except Exception as ex:
        GLib.idle_add(self._dialogo_erro, f"{type(ex).__name__}: {ex}")
```

> **Regra de ouro do GTK:** widgets só podem ser tocados na thread principal — por isso a
> atualização (`_atualizar_gui`, que faz `set_text`/`_plotar`/`canvas.draw`) é agendada via
> `GLib.idle_add`. Uma `queue.Queue` pode representar o "meio" entre as threads, como sugere
> o `GUIA_IMPLEMENTACAO.md` §8. Para a entrega, a versão síncrona da §6/§7 já é suficiente;
> as threads são o diferencial que casa com a Figura 1.

---

## 9. Ordem de implementação sugerida

1. Janela vazia + `main()` abrindo (`Gtk.main`).
2. Painel de configuração (`_painel_config`) com todos os widgets e os combos populados.
3. `_ler_configuracoes()` → imprima o dict e confira contra a §2.1.
4. Botão Simular chamando o pipeline (§6) **sem** gráficos: valide Texto/Bits RX.
5. Embarque do Matplotlib (§5) + `_plotar` nas abas.
6. Tratamento de erro (`_dialogo_erro`) e Status do `edc_ok`.
7. (Opcional/diferencial) threads + `GLib.idle_add` (§8).
8. Ligue, futuramente, ao `Simulador.py` se ele centralizar a orquestração.

---

## 10. Checklist de conformidade (Seção 2 do enunciado / `GUIA_IMPLEMENTACAO.md` §9)

- [ ] **Não** é terminal — janela GTK com widgets.
- [ ] Entradas: tam. quadro, tam. EDC (`k`), enquadramento, detecção/correção, modulação digital, modulação portadora, ruído (x, σ), texto.
- [ ] Saídas: **texto** TX e RX; **bits** TX e RX; **gráficos** do sinal TX e RX (Matplotlib embarcado em GTK).
- [ ] Botão "Simular" liga a GUI ao backend (`Transmissor`/`aplicar_ruido`/`Receptor`).
- [ ] Strings de config idênticas às da §2.1 (senão `ValueError`).
- [ ] Status do `edc_ok` visível (erro detectado vs sem erro).
- [ ] (Diferencial) TX/RX em threads conforme a Figura 1.
- [ ] Executa sem erros no Linux (`python InterfaceGrafica.py`).

---

### Apêndice — combinações de teste rápidas pela GUI

| Mensagem | Quadro | Enquadr. | EDC | Digital | Portadora | σ | Esperado |
|---|---|---|---|---|---|---|---|
| `Olá, TR1!` | 64 | Inserção de bits | CRC-32 | NRZ-Polar | nenhum | 0.05 | RX = TX, EDC ✓ |
| `teste` | 32 | Contagem de caracteres | Hamming | nenhum | QPSK | 0.05 | RX = TX, EDC ✓ |
| `abc` | 64 | Inserção de bytes | Hamming | Manchester | nenhum | 0.6 | Hamming corrige 1 bit/quadro |
| `abc` | 64 | Inserção de bytes | CRC-32 | Manchester | nenhum | 0.6 | EDC ✗ (detecta, não corrige) |

> Com σ alto, Hamming tende a recuperar (corrige 1 bit por quadro) e CRC tende a acusar
> `edc_ok=False` — exatamente o que demonstra detecção vs correção na apresentação.
