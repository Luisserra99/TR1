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

## 5. Encerrando

Feche as janelas (ou `Ctrl+C` em cada terminal). Se usou ambiente virtual, `deactivate`.
