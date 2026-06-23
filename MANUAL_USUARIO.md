# Manual do Usuário — Simulador TR1 (Camadas Física e de Enlace)

Simulador que transmite uma mensagem de texto de um **Transmissor** para um **Receptor**,
passando por codificação de enlace (enquadramento + detecção/correção de erros), modulação
do sinal e um **meio com ruído**. As duas pontas são **janelas gráficas separadas** que
conversam pela rede (socket TCP), como na Figura 1 do enunciado.

---

## 1. Requisitos

- **Linux** (testado em Ubuntu/Debian) com ambiente gráfico (desktop).
- **Python 3.10+**.
- Bibliotecas: **GTK 3 / PyGObject** (interface) e **NumPy / Matplotlib** (sinais e gráficos).

---

## 2. Instalação

Escolha **uma** das opções abaixo.

### Opção A — `apt` + ambiente virtual (recomendada no Ubuntu/Debian)

```bash
# 1) Pacotes de sistema do GTK (não vêm pelo pip):
sudo apt install python3-gi python3-gi-cairo gir1.2-gtk-3.0 python3-full

# 2) Ambiente virtual que enxerga o GTK do sistema:
python3 -m venv --system-site-packages .venv
source .venv/bin/activate

# 3) Bibliotecas Python puro:
pip install -r requirements.txt        # numpy, matplotlib
```

> Em Ubuntu 24.04 / Debian 12+ o `pip` no Python do sistema é bloqueado
> (`externally-managed-environment`). **Não** use `--break-system-packages`; use o
> ambiente virtual acima.

### Opção B — Conda (não depende do `apt`)

```bash
conda env create -f environment.yml
conda activate tr1
```

### Confirme que está tudo certo

```bash
python -c "import gi; gi.require_version('Gtk','3.0'); from gi.repository import Gtk; import cairo, numpy, matplotlib; print('ambiente OK')"
```

Deve imprimir `ambiente OK`.

---

## 3. Como executar

O programa roda em **dois papéis**, na **mesma máquina**. Abra **dois terminais** (com o
ambiente ativado em ambos) e **inicie sempre o Receptor primeiro** — ele fica aguardando.

```bash
# Terminal 1 — Receptor (abra primeiro)
python InterfaceGrafica.py --modo rx

# Terminal 2 — Transmissor
python InterfaceGrafica.py --modo tx
```

| Opção | Para que serve |
|---|---|
| `--modo rx` / `--modo tx` | papel da instância (receptor / transmissor) — **obrigatório** |

> A comunicação é **local e fixa** (`127.0.0.1:5001`); não há host nem porta para configurar.

---

## 4. Usando a interface

### Janela do **Transmissor**
1. Digite a **Mensagem**.
2. Configure os parâmetros (veja §5):
   - **Tam. máx. quadro**, **Enquadramento**, **Detecção/Correção** (e **k** se for Checksum).
   - **Modulação**: escolha **OU** uma *digital* **OU** uma *por portadora* — deixe a outra em
     `nenhum` (o sinal usa só uma das duas).
   - **Ruído**: `x` (média) e `σ` (desvio) do canal.
3. Clique **▶ TRANSMITIR**.
   - À esquerda aparece o texto e os bits transmitidos; na aba **Gráficos**, o sinal limpo e o
     sinal com ruído que foi enviado.
   - O status mostra **"Enviado ✓"**.

### Janela do **Receptor**
- Começa em **"Aguardando conexão…"**. Ao receber, preenche automaticamente:
  - **Texto enviado (TX)** e **Texto recuperado (RX)** — devem coincidir quando não há erro.
  - **Bits recebidos (RX)**.
  - **Status EDC**: <span>✓ verde</span> (sem erro) ou ✗ vermelho (erro detectado).
  - Aba **Gráficos**: o **sinal recebido** (com ruído).
- Os campos de configuração do Receptor refletem o que o Transmissor usou (são informativos).
- O Receptor continua aguardando: você pode transmitir várias vezes seguidas.

> O Receptor decodifica usando a configuração que **chega junto** do sinal — você não precisa
> reconfigurar o Receptor manualmente para casar com o Transmissor.

---

## 5. O que cada parâmetro significa

| Campo | Opções | Efeito |
|---|---|---|
| **Tam. máx. quadro** | nº de bits | divide a mensagem em quadros desse tamanho |
| **Enquadramento** | Contagem de caracteres · Inserção de bytes · Inserção de bits · nenhum | como o início/fim de cada quadro é marcado |
| **Detecção/Correção** | Paridade · Checksum · CRC-32 · Hamming · nenhum | Paridade/Checksum/CRC **detectam** erro; **Hamming corrige** 1 bit por quadro |
| **Tam. checksum (k)** | nº de bits | tamanho do bloco do Checksum (só usado se escolher Checksum) |
| **Modulação digital** | NRZ-Polar · Manchester · Bipolar · nenhum | sinal em banda-base |
| **Modulação portadora** | ASK · FSK · PSK · QPSK · 16-QAM · nenhum | sinal modulado em uma senoide |
| **Ruído x / σ** | números | intensidade do ruído gaussiano do meio (σ maior = mais erros) |

---

## 6. Cenários de demonstração

Configure no **Transmissor** e clique TRANSMITIR; observe o **Receptor**.

| Mensagem | Enquadr. | Detecção/Correção | Modulação | σ | Resultado esperado no RX |
|---|---|---|---|---|---|
| `Olá, TR1!` | Inserção de bits | CRC-32 | digital NRZ-Polar | 0.05 | texto igual, **EDC ✓** |
| `teste` | Contagem de caracteres | Hamming | portadora QPSK | 0.05 | texto igual, **EDC ✓** |
| `abc` | Inserção de bytes | **Hamming** | digital Manchester | 0.60 | Hamming **corrige** → texto igual |
| `abc` | Inserção de bytes | **CRC-32** | digital Manchester | 0.60 | erro passa → **EDC ✗** (detecta, não corrige) |

As duas últimas linhas, lado a lado, mostram a diferença entre **detecção** (CRC acusa o
erro) e **correção** (Hamming conserta).

---

## 7. Solução de problemas

| Sintoma | Causa provável | Solução |
|---|---|---|
| `Não foi possível conectar. O Receptor está rodando?` | TX aberto antes do RX | inicie o **RX primeiro**, depois o TX |
| `No module named 'gi'` / `Namespace Gtk not available` | GTK não instalado | rode o passo 2 da §2 (Opção A) |
| `error: externally-managed-environment` no `pip` | pip bloqueado no Python do sistema | use o **ambiente virtual** (§2 Opção A) |
| `cannot open display` / abre sem janela | sessão sem ambiente gráfico (ex.: SSH puro) | rode num desktop, ou use `ssh -X`/VNC |
| `Address already in use` ao abrir o RX | já há um Receptor rodando na porta 5001 | feche a outra instância do Receptor |
| Texto RX sai trocado e **EDC ✗** | ruído alto demais para o esquema escolhido | reduza `σ`, ou use **Hamming**, ou uma modulação mais robusta |

> Mensagens como `--- INICIANDO TRANSMISSÃO ---` no terminal são apenas logs normais do
> programa, não são erros.

---

## 8. Encerrando

Feche as janelas (ou `Ctrl+C` em cada terminal). Se usou ambiente virtual, `deactivate`.
