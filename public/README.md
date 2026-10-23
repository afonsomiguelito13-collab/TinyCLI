# 🦁 Tiny Cloud CLI

**O Agente Autónomo de Programação para o Terminal.**
*Benchmarks are honest.*

[![Versão](https://img.shields.io/badge/version-14.5.0-blue.svg)]()
[![Linguagem](https://img.shields.io/badge/python-3.10%2B-blue.svg)]()
[![Licença](https://img.shields.io/badge/license-Proprietary-red.svg)]()

O **Tiny Cloud CLI** é uma ferramenta de linha de comandos (CLI) leve e inteligente, desenhada para transformar o teu terminal (Termux, Linux, Raspberry Pi) num ambiente de desenvolvimento assistido por IA. Não é apenas um chat: ele tem **poderes de agente** para criar ficheiros, executar comandos e testar código Python em tempo real.

---

## 🚀 Funcionalidades Principais

- **Agent Loop (Autocorreção):** O agente cria o código, executa, lê os logs de erro e **corrige-se a si mesmo** até obter uma execução estável.
- **Model Pool & Failover:** Integração com múltiplos provedores (DeepSeek, Agnes, GPT-6 Luna, Gemini). Se um modelo falhar, o sistema troca automaticamente para um de reserva.
- **Sistema de Fila (Fila do iPhone):** Para garantir a estabilidade do servidor, os pedidos são processados numa fila real. Se o servidor estiver cheio, tu esperas a tua vez como no lançamento de um iPhone.
- **Sistema de Segurança (Trust Workspace):** O agente pede permissão antes de aceder a novos diretórios ou executar comandos destrutivos.
- **Sistema de Ban:** Comandos perigosos (como `rm -rf`) são bloqueados instantaneamente com um aviso severo de violação dos Termos de Serviço.
- **UI Profissional:** Interface limpa com painéis coloridos, spinners de carregamento e syntax highlighting para blocos de código.

---

## 🧠 Arquitetura (Cliente-Servidor)

O Tiny CLI usa uma arquitetura híbrida para ser leve no teu dispositivo e seguro na nuvem:

1.  **O Cliente (`tinycli.py`):** Corre no teu terminal. Ele é responsável pela UI, pela execução local de comandos (após a tua aprovação) e pela gestão do histórico de sessões.
2.  **O Servidor (`server.js` no Render):** O guarda-costas da API. Ele esconde as chaves da BeatAPI/VyceAI, gere o Rate Limit, a Fila de espera e faz o failover entre os modelos.

**Privacidade:** As tuas conversas não são guardadas no servidor. Todo o histórico fica no teu dispositivo (`~/.local/share/.tinycli_sessions`).

---

## 🛠️ Instalação (Termux / Linux)

A instalação é feita num único comando. O instalador trata de baixar o cliente, instalar as dependências visuais (Rich, Questionary, Pyfiglet) e configurar o atalho global.

```bash
curl -sL https://raw.githubusercontent.com/afonsomiguelito13-collab/TinyCLI/main/public/install.sh | bash