# Guia de Implementação — Trabalho Final de TR1 (CIC0235)

> Simulador das camadas **Física** e de **Enlace** de uma rede de computadores, em **Python**.
> Este documento é um **roteiro de implementação do zero**, detalhado por módulo e função, com
> rastreabilidade direta para cada item do enunciado (`Trabalho_de_TR1-5.pdf`).
---

## 1. Visão geral do trabalho

O trabalho consiste em **simular a transmissão de uma mensagem de texto** desde a digitação no
transmissor (TX) até a recuperação no receptor (RX), passando por:

```
Texto → bits → [Camada de Enlace] → [Camada Física] → sinal elétrico (V/W)
      → [Meio com ruído gaussiano] → sinal recebido
      → [Camada Física RX] → [Camada de Enlace RX] → bits → Texto
```

### Regras de ouro (não negociáveis)

| Regra | Detalhe |
|-------|---------|
| **Linguagem** | Python 3 (o enunciado também aceita C++). |
| **Sem bibliotecas externas para os algoritmos** | É **proibido** usar libs prontas para CRC, Hamming, modulações, etc. Ex.: **não** usar `zlib` para CRC. NumPy/Matplotlib são aceitos apenas para arrays/plotagem, **não** para os algoritmos centrais. |
| **Interface gráfica obrigatória** | **Não** pode ser tela de terminal. Recomendação do enunciado: **GTK** (PyGObject). |
| **Sinal em valores de eletricidade** | O sinal trafega como valores V/W (tensão/potência), não como bits abstratos. |
| **Ruído gaussiano** | O meio adiciona ruído `n(x, σ)` a partir de um valor base de V/W. |
| **TX ≠ RX** | O código deve diferenciar claramente transmissor e receptor (idealmente em threads/processos separados, conforme a Figura 1 do PDF). |
| **Modularização** | Usar as declarações/implementações dos arquivos `.py` no simulador. Código duplicado/redundante perde pontos. |
| **Independência** | Cada grupo desenvolve sozinho. O projeto passa por verificador automático de plágio (nota zero se detectado). |

### Rastreabilidade: requisito do PDF → módulo/função

| Item do PDF | Requisito | Arquivo | Funções sugeridas |
|-------------|-----------|---------|-------------------|
| 1.1.1 | NRZ-Polar, Manchester, Bipolar | `CamadaFisica.py` | `nrz_polar`, `manchester`, `bipolar` (+ decoders) |
| 1.1.2 | ASK, FSK, PSK/QPSK, 16-QAM | `CamadaFisica.py` | `ask_*`, `fsk_*`, `psk_*`, `qpsk_*`, `qam16_*` |
| 1.3 | Contagem de caracteres, Flags+bytes, Flags+bits | `CamadaEnlace.py` | `framing_char_count`, `framing_byte_flags`, `framing_bit_flags` (+ deframing) |
| 1.4 | Paridade par, Checksum, CRC-32 | `CamadaEnlace.py` | `parity_*`, `checksum_*`, `crc32_*` |
| 1.5 | Hamming | `CamadaEnlace.py` | `hamming_insert`, `hamming_correct`, `hamming_remove` |
| Fig. 1 | Ruído gaussiano no meio | `CamadaFisica.py` / `Simulador.py` | `aplicar_ruido` |
| Fig. 1 | Aplicação texto↔bits | `Transmissor.py` / `Receptor.py` | `texto_para_bits`, `bits_para_texto` |
| Seção 2 | GUI GTK | `InterfaceGrafica.py` | janela de configuração + plots |
| Seção 2 | Rotina principal | `Simulador.py` | `main`, `simular` |

---

## 2. Arquitetura e organização dos arquivos

O enunciado (Seção 2) exige entregar estes arquivos. Sugestão de responsabilidades:

| Arquivo | Responsabilidade |
|---------|------------------|
| `CamadaFisica.py` | Modulação digital (banda-base), modulação por portadora, amostragem e ruído. |
| `CamadaEnlace.py` | Enquadramento, detecção (paridade/checksum/CRC) e correção (Hamming) de erros. |
| `Transmissor.py` | Fluxo TX: texto → bits → enlace → física → sinal. |
| `Receptor.py` | Fluxo RX: sinal → física → enlace → bits → texto. |
| `InterfaceGrafica.py` | GUI GTK: entrada de dados, configuração e exibição gráfica dos resultados. |
| `Simulador.py` | Rotina principal que orquestra TX → meio (ruído) → RX. |
| `utils.py` | Conversões auxiliares (int↔bits, texto↔bits, padding, etc.). |

### Diagrama de fluxo (baseado na Figura 1 do PDF)

```
                 ┌──────────────── Interface Gráfica (config) ────────────────┐
                 │ tam. quadro | tam. EDC | enquadramento | detecção/correção  │
                 │ modulação digital | modulação portadora | ruído (x, σ)      │
                 └────────────────────────────────────────────────────────────┘

  THREAD TX                          MEIO                          THREAD RX
  ┌───────────────┐          ┌──────────────────┐          ┌───────────────┐
  │ Aplicação     │          │                  │          │ Camada Física │
  │  texto→bits   │          │   sinal V/W      │          │  demodulador  │
  ├───────────────┤          │       +          │          │  decod. banda │
  │ Camada Enlace │          │  ruído gaussiano │          ├───────────────┤
  │  enquadra+EDC │          │   n(x, σ)        │          │ Camada Enlace │
  ├───────────────┤   sinal  │                  │  sinal   │  detecção/corr│
  │ Camada Física │ ───────► │                  │ ───────► │  desenquadra  │
  │  cod. banda   │          │                  │          ├───────────────┤
  │  modulador    │          │                  │          │ Aplicação     │
  └───────────────┘          └──────────────────┘          │  bits→texto   │
                                                            └───────────────┘
```

### Convenção de dados entre camadas

- **Texto:** `str` (mensagem do usuário).
- **Bits:** lista de inteiros `0/1` (ou `list[bool]`). Mantenha **um único formato** em todo o
  projeto para evitar conversões redundantes.
- **Quadros:** lista de bits já com cabeçalho/flags e EDC.
- **Sinal:** lista/`np.ndarray` de valores reais (V/W), com `N` amostras por bit/símbolo.

---

## 3. Ambiente e dependências

### 3.1 Pacotes de sistema (GTK3 + PyGObject) — via `apt`

O `PyGObject`/`pycairo` são **bindings de sistema**: precisam vir do `apt` (instalá-los via `pip`
falha sem as libs `-dev` do GObject). Instale-os primeiro:

```bash
# Debian/Ubuntu
sudo apt install python3-gi python3-gi-cairo gir1.2-gtk-3.0 python3-full
```

### 3.2 Ambiente Python — `venv`

Distribuições recentes (Debian 12+/Ubuntu 24.04+) bloqueiam `pip install` no Python do sistema
(erro `externally-managed-environment`, PEP 668). A solução **não** é `--break-system-packages`,
e sim um **virtualenv**. Use `--system-site-packages` para que o venv enxergue o GTK instalado
pelo `apt`:

```bash
# cria o venv herdando o python3-gi/GTK do sistema
python3 -m venv --system-site-packages .venv
source .venv/bin/activate

# instala apenas as libs Python puro (nao precisam do apt)
pip install -r requirements.txt   # numpy, matplotlib
```

> O `requirements.txt` lista só `numpy` e `matplotlib` de propósito — `PyGObject`/`pycairo`
> vêm do `apt` (passo 3.1).
>
> **Alternativa (conda):** `conda env create -f environment.yml && conda activate tr1` instala
> toda a stack GTK via `conda-forge`, sem depender do `apt`.

### 3.3 Execução

```bash
source .venv/bin/activate     # se ainda nao estiver ativo
python InterfaceGrafica.py    # abre a GUI
# ou
python Simulador.py           # execução direta (modo simulação/testes)
```

Para confirmar que o ambiente está OK:

```bash
python -c "import gi; gi.require_version('Gtk','3.0'); from gi.repository import Gtk; import cairo, numpy, matplotlib; print('ambiente OK')"
```

> **Atenção:** NumPy/Matplotlib são permitidos apenas para manipular arrays e **plotar** sinais.
> Os algoritmos (CRC, Hamming, modulações) devem ser implementados **manualmente**.

---

## 4. Etapa — Camada Física (`CamadaFisica.py`) — item 1.1 do PDF

O sinal deve ser representado em **valores de eletricidade (V/W)**. Defina constantes globais, por
exemplo `V = 1.0` (nível alto) e `-V` (nível baixo), e `AMOSTRAS_POR_BIT = 100` (resolução do plot).

### 4.1 Codificação banda-base — modulação digital (item 1.1.1)

Cada função recebe a lista de bits e retorna o sinal (lista de níveis V/W). O decodificador faz o
inverso (amostra o sinal e recupera os bits).

#### NRZ-Polar (Non-Return to Zero Polar)
- **Regra:** bit `1` → `+V`; bit `0` → `−V`. Nível constante durante todo o tempo do bit.

```python
def nrz_polar(bits: list[int]) -> list[float]:
    """Codifica bits em NRZ-Polar: 1 -> +V, 0 -> -V."""

def nrz_polar_decoder(sinal: list[float]) -> list[int]:
    """Amostra o sinal no meio de cada bit: nível > 0 -> 1, senão 0."""
```

#### Manchester
- **Regra:** XOR do bit com o clock. Convenção (IEEE 802.3): bit `1` = transição alto→baixo;
  bit `0` = transição baixo→alto. Cada bit tem **duas metades** (meio-período).

```python
def manchester(bits: list[int]) -> list[float]:
    """Cada bit vira duas metades com transição no meio do período."""

def manchester_decoder(sinal: list[float]) -> list[int]:
    """Identifica a transição no meio do bit para recuperar o valor."""
```

#### Bipolar (AMI — Alternate Mark Inversion)
- **Regra:** bit `0` → `0`; bit `1` → alterna entre `+V` e `−V` a cada ocorrência.

```python
def bipolar(bits: list[int]) -> list[float]:
    """0 -> 0V; 1 -> alterna +V / -V."""

def bipolar_decoder(sinal: list[float]) -> list[int]:
    """Nível != 0 -> 1; nível == 0 -> 0 (usar limiar para o ruído)."""
```

### 4.2 Modulação por portadora (item 1.1.2)

Use uma portadora senoidal `A·sin(2πft)` amostrada com `AMOSTRAS_POR_BIT` pontos por bit/símbolo.
Parâmetros comuns: frequência `f`, amplitude `A`, amostras por símbolo `N`.

#### ASK — Amplitude Shift Keying
- **Regra:** bit `1` → portadora com amplitude `A`; bit `0` → amplitude `0` (ou menor).

```python
def ask_modulation(bits, f=..., A=..., N=...) -> np.ndarray: ...
def ask_demodulation(sinal, f=..., A=..., N=...) -> list[int]: ...
```

#### FSK — Frequency Shift Keying
- **Regra:** bit `1` → frequência `f1`; bit `0` → frequência `f0`.

```python
def fsk_modulation(bits, f0=..., f1=..., A=..., N=...) -> np.ndarray: ...
def fsk_demodulation(sinal, f0=..., f1=..., A=..., N=...) -> list[int]: ...
```

#### PSK / QPSK — Phase Shift Keying
- **BPSK:** bit `1` → fase `0`; bit `0` → fase `π`.
- **QPSK:** processa **2 bits por símbolo**, cada par mapeado a uma das 4 fases
  (`45°, 135°, 225°, 315°`).

```python
def psk_modulation(bits, f=..., A=..., N=...) -> np.ndarray: ...
def psk_demodulation(sinal, ...) -> list[int]: ...
def qpsk_modulation(bits, ...) -> np.ndarray: ...   # 2 bits/símbolo
def qpsk_demodulation(sinal, ...) -> list[int]: ...
```

#### 16-QAM — Quadrature Amplitude Modulation
- **Regra:** processa **4 bits por símbolo** (constelação 4×4). Combina amplitude e fase
  (componentes I e Q). Garanta **padding** para múltiplos de 4 bits.

```python
def qam16_modulation(bits, f=..., A=..., N=...) -> np.ndarray: ...
def qam16_demodulation(sinal, ...) -> list[int]: ...
```

### 4.3 Seletor (amostrador) e funções de despacho

Para a GUI escolher a técnica em runtime, crie despachantes:

```python
def coder(bits: list[int], tipo: str) -> list[float]:
    """Despacha para nrz_polar / manchester / bipolar conforme 'tipo'."""

def decoder(sinal: list[float], tipo: str) -> list[int]:
    """Despacha para o decodificador banda-base correspondente."""

def modulator(bits, tipo: str, **params) -> np.ndarray:
    """Despacha para ask/fsk/psk/qpsk/qam16."""

def demodulator(sinal, tipo: str, **params) -> list[int]: ...
```

---

## 5. Etapa — Meio de comunicação / Ruído (Figura 1)

O meio recebe o sinal em V/W e **adiciona ruído gaussiano** `n(x, σ)`:

```python
def aplicar_ruido(sinal: list[float], x: float, sigma: float) -> list[float]:
    """Soma a cada amostra um ruído gaussiano de média x e desvio sigma.
    Implementar a normal manualmente (ex.: Box-Muller) ou usar random.gauss."""
```

- `x` (média) e `σ` (desvio-padrão) devem ser **configuráveis pela GUI**.
- O ruído permite demonstrar a **detecção e correção de erros** da camada de enlace.
- Os decodificadores/demoduladores devem usar **limiar** (threshold) para tolerar o ruído.

---

## 6. Etapa — Camada de Enlace (`CamadaEnlace.py`) — itens 1.3 a 1.5

A camada de enlace opera sobre **bits**. O pipeline TX típico é:
`bits da aplicação → adiciona EDC/ECC → enquadra`. No RX, o inverso:
`desenquadra → verifica/corrige erros → bits da aplicação`.

### 6.1 Enquadramento — item 1.3 (1/3)

> Acrescentar ao código do Trabalho Prático I os protocolos de enquadramento.

#### Contagem de caracteres
- **Regra:** cada quadro inicia com um cabeçalho (ex.: 8 bits) indicando o tamanho do quadro.

```python
def framing_char_count(quadro_bits: list[int]) -> list[int]:
    """Prefixa um contador (em bits) com o tamanho do quadro."""
def deframing_char_count(bitstream: list[int]) -> list[list[int]]:
    """Lê o contador e fatia os quadros."""
```

#### Flags com inserção de bytes/caracteres (byte stuffing)
- **Regra:** delimita o quadro com a flag `0x7E` (`01111110`). Se a flag ou o caractere de escape
  `0x7D` aparecer no payload, insere um **byte de escape** antes.

```python
def framing_byte_flags(quadro_bits: list[int]) -> list[int]: ...
def deframing_byte_flags(bitstream: list[int]) -> list[list[int]]: ...
```

#### Flags com inserção de bits (bit stuffing)
- **Regra:** flag `01111110`. No payload, após **cinco `1` consecutivos**, insere um `0`
  (destuffing no RX remove esse `0`).

```python
def framing_bit_flags(quadro_bits: list[int]) -> list[int]: ...
def deframing_bit_flags(bitstream: list[int]) -> list[list[int]]: ...
```

### 6.2 Detecção de erros — item 1.4 (2/3)

> Acrescentar à subetapa anterior os protocolos de detecção de erros.

Padrão de funções para cada técnica: `insert` (TX, anexa o EDC), `check` (RX, valida) e
`remove` (RX, retira o EDC do payload).

#### Bit de paridade par
- **Regra:** anexa 1 bit para que a quantidade total de `1`s seja **par**.

```python
def parity_insert(bits: list[int]) -> list[int]: ...
def parity_check(bits: list[int]) -> bool: ...
def parity_remove(bits: list[int]) -> list[int]: ...
```

#### Checksum (modelo apresentado em sala)
- **Regra:** soma dos blocos em complemento; o RX soma tudo e verifica o resultado.

```python
def checksum_insert(bits: list[int], k: int) -> list[int]: ...
def checksum_check(bits: list[int], k: int) -> bool: ...
def checksum_remove(bits: list[int], k: int) -> list[int]: ...
```

#### CRC-32 (polinômio IEEE 802 — **implementação manual**)
- **Regra:** divisão polinomial binária pelo gerador CRC-32 (`0x04C11DB7`). **Proibido usar `zlib`.**

```python
def crc32_insert(bits: list[int]) -> list[int]:
    """Anexa os 32 bits de CRC calculados por divisão polinomial."""
def crc32_check(bits: list[int]) -> bool:
    """Recalcula o CRC; resto zero => sem erro detectado."""
def crc32_remove(bits: list[int]) -> list[int]: ...
```

### 6.3 Correção de erros — item 1.5 (3/3)

> Acrescentar o protocolo de correção de erros: Hamming.

#### Código de Hamming
- **Regra:** insere bits de paridade nas posições potências de 2. No RX, recomputa a síndrome para
  **localizar e corrigir** 1 bit invertido.

```python
def hamming_insert(bits: list[int]) -> list[int]:
    """Insere bits de paridade nas posições 1,2,4,8,..."""
def hamming_correct(bits: list[int]) -> list[int]:
    """Calcula a síndrome, localiza e corrige o bit errado."""
def hamming_remove(bits: list[int]) -> list[int]:
    """Remove os bits de paridade, retornando os dados originais."""
```

> **Decisão de projeto a documentar no relatório:** EDC (detecção) e ECC (correção) podem ser
> mutuamente exclusivos por quadro, conforme escolha na GUI. Defina e descreva sua convenção.

---

## 7. Etapa — Aplicação (texto ↔ bits)

No TX, converter o texto digitado em bits; no RX, reconstruir o texto.

```python
def texto_para_bits(texto: str) -> list[int]:
    """Codifica cada caractere (ex.: UTF-8/ASCII) em 8 bits."""
def bits_para_texto(bits: list[int]) -> str:
    """Agrupa de 8 em 8 bits e reconstrói os caracteres."""
```

Coloque também em `utils.py` os auxiliares reutilizados (`int_para_bits`, `bits_para_int`,
`fatiar_em_payloads`, `adicionar_padding`, etc.) para evitar duplicação.

---

## 8. Etapa — Transmissor e Receptor (TX/RX)

### Transmissor (`Transmissor.py`)
```
texto
  → texto_para_bits                      (aplicação)
  → fatiar em payloads (tam. máx. quadro)
  → EDC/ECC (paridade | checksum | crc32 | hamming)   (enlace)
  → enquadramento (char_count | byte_flags | bit_flags)
  → coder / modulator                    (física: bits → sinal V/W)
  → [envia ao meio]
```

### Receptor (`Receptor.py`)
```
sinal recebido (com ruído)
  → decoder / demodulator                (física: sinal → bits)
  → desenquadramento                     (enlace)
  → check/correct de erros
  → remove EDC/ECC
  → bits_para_texto                      (aplicação)
  → texto recuperado
```

### Concorrência
Conforme a Figura 1, TX e RX devem rodar como **threads/processos separados**. Use o módulo
`threading` (ou `multiprocessing`) e uma fila (`queue.Queue`) ou variável compartilhada para
representar o **meio de comunicação** (onde o ruído é aplicado).

---

## 9. Etapa — Interface Gráfica (`InterfaceGrafica.py`) — GTK

A GUI **não pode** ser terminal. Deve permitir **configuração** e **exibição gráfica**.

### Configuração geral (entradas)
- Tamanho máximo do quadro.
- Tamanho do EDC.
- Tipo de **enquadramento** (contagem de caracteres / flags+bytes / flags+bits).
- Tipo de **detecção ou correção** (paridade / checksum / CRC-32 / Hamming).
- Tipo de **modulação digital** (NRZ-Polar / Manchester / Bipolar).
- Tipo de **modulação por portadora** (ASK / FSK / PSK-QPSK / 16-QAM).
- Ruído: valores **x** (média) e **σ** (desvio).
- Campo de **entrada de texto**.

### Exibição (saídas)
- Saída de **texto** (TX e RX).
- Saída de **bits** (TX e RX).
- **Gráficos do sinal** (TX e RX) — usar Matplotlib embarcado no GTK
  (`FigureCanvasGTK3Agg`).

> Dica: ligue o botão "Simular" da GUI à rotina `simular()` do `Simulador.py`, passando todas as
> configurações escolhidas.

---

## 10. Etapa — Relatório (Seção 2 do PDF)

Relatório com **mínimo de 3 páginas** (aceita-se Jupyter). Estrutura obrigatória:

| Seção | Conteúdo |
|-------|----------|
| **Capa** | Nome do simulador e nome dos membros do grupo. |
| **Introdução** | Descrição do problema e visão geral do funcionamento do simulador. |
| **Implementação** | Descrição detalhada do desenvolvimento, **diagramas ilustrativos**, funcionamento dos protocolos, procedimentos e decisões tomadas em casos omissos no enunciado. |
| **Membros** | Atividades desenvolvidas por **cada** membro do grupo. |
| **Conclusão** | Comentários gerais e principais dificuldades. |

Entrega: relatório + código fonte compactados em **`.zip`** no Moodle.

---

## 11. Checklist final e critérios de avaliação

### Checklist de implementação

- [ ] **Física — digital:** NRZ-Polar, Manchester, Bipolar (cod. + decod.)
- [ ] **Física — portadora:** ASK, FSK, PSK/QPSK, 16-QAM (mod. + demod.)
- [ ] **Meio:** ruído gaussiano `n(x, σ)` configurável
- [ ] **Enlace — enquadramento:** contagem de caracteres, flags+bytes, flags+bits
- [ ] **Enlace — detecção:** paridade par, checksum, CRC-32 (manual)
- [ ] **Enlace — correção:** Hamming
- [ ] **Aplicação:** texto↔bits
- [ ] **TX/RX** separados (threads) com diferenciação clara
- [ ] **GUI GTK** com todas as configurações e gráficos
- [ ] **Simulador.py** orquestrando tudo
- [ ] **Relatório** (≥3 páginas) com todas as seções
- [ ] Código **modular**, comentado e indentado; sem libs externas para algoritmos
- [ ] Executa sem erros no **Linux**
- [ ] `.zip` (código + relatório) submetido no Moodle

### Critérios de avaliação (Tabela 1 do PDF)

| Item | Quesito | Pontos |
|------|---------|--------|
| Relatório | PDF com todas as informações | **+2** |
| Código e execução | Projeto compila e executa corretamente | **+2** |
| Resultado | Saídas corretas conforme os protocolos | **+3** |
| Conceitos de TR1 | Código-fonte implementado adequadamente | **+3** |
| Legibilidade e modularização | Comentários, indentação, funções bem usadas, uso correto dos arquivos `.py` | **−10** (penalidade) |
| Atraso | −1 por dia (máx. −5) | **−1/dia** |
| Plágio | Cópia de qualquer forma | **−10** |

> **Lembrete:** o projeto passa por **verificador automático de plágio**. Trabalhos detectados
> recebem nota zero, independentemente do grupo. Mantenha o desenvolvimento independente.

---

### Ordem recomendada de desenvolvimento

1. `utils.py` (conversões base) → 2. Aplicação (texto↔bits) → 3. Camada Física digital →
4. Camada Física portadora → 5. Ruído → 6. Enlace (enquadramento) → 7. Enlace (detecção) →
8. Enlace (correção) → 9. `Transmissor.py`/`Receptor.py`/`Simulador.py` (integração) →
10. `InterfaceGrafica.py` (GUI) → 11. Relatório.

Teste cada módulo isoladamente (codifica→decodifica sem ruído deve devolver os bits originais)
antes de integrar.
