#!/usr/bin/env python3
import os, sys, json, subprocess, time, uuid, re
import questionary
from questionary import Style
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich.table import Table
from rich.live import Live
from rich.syntax import Syntax
import pyfiglet
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

console = Console()
custom_style = Style([
    ('qmark', 'fg:#00ff00 bold'), ('question', 'fg:#00bfff bold'),
    ('answer', 'fg:#00ff00 bold'), ('pointer', 'fg:#ffaa00 bold'),
    ('highlighted', 'fg:#00ff00 bold'), ('selected', 'fg:#00ff00')
])

VERSAO_LOCAL = "12.0.0"
INSTALL_URL = "https://raw.githubusercontent.com/afonsomiguelito13-collab/TinyCLI/main/public/install.sh"

SERVER_URL = os.environ.get("TINY_SERVER_URL", "https://tinycli.onrender.com")
TRUST_FILE = os.path.expanduser("~/.tinycli_trust")
USAGE_FILE = os.path.expanduser("~/.local/share/.tinycli_usage.json")
SESSIONS_DIR = os.path.expanduser("~/.local/share/.tinycli_sessions")
TERMOS_FILE = os.path.expanduser("~/.local/share/.tinycli_terms.json")
CONFIG_FILE = os.path.expanduser("~/.local/share/.tinycli_config.json")

MODELOS_DISPONIVEIS = [
    "deepseek-v4.1", 
    "deepseek-v4-flash", 
    "gemini-3.8-flash", 
    "agnes-3.0-flash",
    "jev-1.13",
    "gpt-6-luna",
    "space-bunny",
    "longcat-2.5"
]
MODELO_ATUAL = MODELOS_DISPONIVEIS[0]
LIMITE_SEMANAL = 5000000 # 5 Milhões

CUSTO_MODELO = {
    "deepseek-v4.1": 3,
    "deepseek-v4-flash": 3,
    "gemini-3.8-flash": 4,
    "agnes-3.0-flash": 3,
    "jev-1.13": 1,
    "gpt-6-luna": 8,
    "space-bunny": 1,
    "longcat-2.5": 1
}

http_session = requests.Session()
retry_strategy = Retry(total=3, backoff_factor=1, status_forcelist=[429, 500, 502, 503, 504], allowed_methods=["POST", "GET"])
adapter = HTTPAdapter(max_retries=retry_strategy, pool_connections=10, pool_maxsize=10)
http_session.mount("https://", adapter)
http_session.mount("http://", adapter)

def limpar_tela():
    os.system('clear' if os.name == 'posix' else 'cls')

def verificar_atualizacao():
    try:
        res = http_session.get(f"{SERVER_URL}/api/version", timeout=(3, 10))
        if res.status_code == 200:
            versao_servidor = res.json().get("version", VERSAO_LOCAL)
            if versao_servidor != VERSAO_LOCAL:
                console.print(Panel(
                    f"[bold yellow]🚀 Nova Atualização Disponível![/bold yellow]\n"
                    f"Versão Local: {VERSAO_LOCAL} | Nova Versão: {versao_servidor}\n\n"
                    f"Queres atualizar agora?",
                    border_style="yellow"
                ))
                if questionary.confirm("Atualizar?").ask():
                    console.print("[cyan]A baixar a atualização...[/cyan]")
                    subprocess.run(f"curl -sL {INSTALL_URL} | bash", shell=True)
                    console.print("[green]✅ Atualização concluída! Reinicia o Tiny CLI.[/green]")
                    sys.exit(0)
    except Exception:
        pass

def carregar_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f: return json.load(f)
        except: pass
    return {"last_dir": os.getcwd()}

def salvar_config(diretorio):
    os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
    with open(CONFIG_FILE, "w") as f: json.dump({"last_dir": diretorio}, f)

def escolher_pasta_inicial():
    config = carregar_config()
    pasta_padrao = config.get("last_dir", os.getcwd())
    
    limpar_tela()
    console.print(Panel("[bold cyan]📁 Onde queres trabalhar hoje?[/bold cyan]", border_style="cyan"))
    
    opcoes = [f"Usar a pasta atual: {pasta_padrao}", "Escolher outra pasta (navegar)", "Usar a Home (~)"]
    escolha = questionary.select("Seleciona uma opção:", choices=opcoes, style=custom_style).ask()
    
    if escolha == "Usar a Home (~)": pasta_final = os.path.expanduser("~")
    elif escolha == "Escolher outra pasta (navegar)":
        pasta_final = questionary.path("Caminho da pasta:", default=pasta_padrao, style=custom_style).ask()
        if not pasta_final or not os.path.isdir(pasta_final):
            pasta_final = os.getcwd()
    else: pasta_final = pasta_padrao

    os.chdir(pasta_final)
    salvar_config(pasta_final)
    time.sleep(1)

def pedir_aprovacao_comando(cmd):
    console.print(Panel(f"[bold yellow]O Agente quer executar:[/bold yellow]\n\n[bold white]{cmd}[/bold white]", border_style="yellow", title="⚠️ APROVAÇÃO NECESSÁRIA"))
    return questionary.select("Aprovas?", choices=["Sim, executar", "Não, bloquear"], style=custom_style).ask() == "Sim, executar"

def verificar_comando_perigoso(cmd):
    return any(p in cmd.lower() for p in ["rm -rf", "reboot", "mkfs", "dd if=", "flash"])

def mostrar_ban_aviso():
    console.print(Panel("[bold red]⚠️ VIOLAÇÃO DOS TERMOS DE SERVIÇO DETECTADA ⚠️[/bold red]\n\n[bold white]You will lose everything.[/bold white]", border_style="red", title="🚫 BAN"))

def aceitar_termos():
    limpar_tela()
    texto_termos = (
        "[bold white]TERMOS DE SERVIÇO E POLÍTICA DE PRIVACIDADE - TINY CLOUD CLI[/bold white]\n\n"
        "[bold yellow]1. Aceitação dos Termos[/bold yellow]\n"
        "Ao aceder ou utilizar o Tiny Cloud CLI (\"Serviço\"), concordas em ficar vinculado a estes Termos.\n\n"
        "[bold yellow]2. Descrição do Serviço[/bold yellow]\n"
        "O Tiny Cloud CLI é uma ferramenta que permite a interação com Modelos de Linguagem (LLMs) de terceiros. O Serviço é fornecido \"como está\".\n\n"
        "[bold yellow]3. Privacidade e Dados[/bold yellow]\n"
        "O Tiny Cloud CLI não armazena os teus prompts nos servidores do backend. Todo o histórico é guardado localmente no teu dispositivo. As chaves de API são mantidas em segurança.\n\n"
        "[bold yellow]4. Responsabilidade e Uso Aceitável[/bold yellow]\n"
        "És o único responsável pelo código gerado. O abuso do sistema (Rate Limit) resultará em banimento.\n"
    )
    
    console.print(Panel(texto_termos, title="📜 Termos e Privacidade", border_style="yellow"))
    
    escolha = questionary.select("Aceitas os Termos de Serviço?", choices=["Sim, eu aceito", "Não, sair"], style=custom_style).ask()
    
    if escolha == "Não, sair":
        console.print("[red]❌ Termos não aceites. A encerrar...[/red]")
        sys.exit(0)
    return True

def listar_sessoes():
    if not os.path.exists(SESSIONS_DIR): return []
    return [f.replace(".json", "") for f in os.listdir(SESSIONS_DIR) if f.endswith(".json")]

def carregar_sessao(session_id):
    path = os.path.join(SESSIONS_DIR, f"{session_id}.json")
    if os.path.exists(path):
        with open(path, "r") as f: return json.load(f)
    return None

def salvar_sessao(session_id, mensagens):
    os.makedirs(SESSIONS_DIR, exist_ok=True)
    with open(os.path.join(SESSIONS_DIR, f"{session_id}.json"), "w") as f:
        json.dump(mensagens, f)

def carregar_usage():
    os.makedirs(os.path.dirname(USAGE_FILE), exist_ok=True)
    if os.path.exists(USAGE_FILE):
        try:
            with open(USAGE_FILE, "r") as f:
                data = json.load(f)
                data.setdefault("requests", 0)
                data.setdefault("tokens_usados", 0)
                return data
        except: pass
    return {"requests": 0, "tokens_usados": 0}

def salvar_usage(data):
    os.makedirs(os.path.dirname(USAGE_FILE), exist_ok=True)
    with open(USAGE_FILE, "w") as f: json.dump(data, f)

USAGE_DATA = carregar_usage()
DIRETORIOS_CONFIAVEIS = set(open(TRUST_FILE).read().splitlines()) if os.path.exists(TRUST_FILE) else set()

def pedir_permissao(caminho):
    abs_path = os.path.abspath(caminho)
    if abs_path in DIRETORIOS_CONFIAVEIS: return True
    escolha = questionary.select(f"⚠️  Confiar em {abs_path}?", choices=["Sim", "Não"], style=custom_style).ask()
    if escolha == "Sim":
        DIRETORIOS_CONFIAVEIS.add(abs_path)
        with open(TRUST_FILE, "a") as f: f.write(f"{abs_path}\n")
        return True
    return False

def chamar_ia(mensagens):
    global USAGE_DATA, MODELO_ATUAL
    USAGE_DATA["requests"] += 1
    api_url = f"{SERVER_URL}/api/chat"
    health_url = f"{SERVER_URL}/api/version"
    
    # Acordar o Render
    max_tentativas = 5
    acordou = False
    for tentativa in range(max_tentativas):
        try:
            res = http_session.get(health_url, timeout=(5, 10))
            if res.status_code == 200:
                acordou = True
                break
        except Exception:
            pass
        with console.status(f"[bold yellow]⏳ A ligar ao servidor... (Tentativa {tentativa+1}/{max_tentativas})[/bold yellow]", spinner="bouncingBall"):
            time.sleep(2)

    if not acordou:
        return "ERRO: O servidor demorou muito a acordar. Tenta de novo daqui a pouco."

    # --- FALLBACK NO CLIENTE ---
    modelos_fallback = ["deepseek-v4.1", "deepseek-v4-flash"]
    
    for modelo_tentativa in [MODELO_ATUAL] + modelos_fallback:
        try:
            if modelo_tentativa != MODELO_ATUAL:
                console.print(f"[yellow]⚠️ {MODELO_ATUAL} falhou (instável). A tentar fallback para {modelo_tentativa}...[/yellow]")
            
            data_pedido = {"messages": mensagens, "model": modelo_tentativa}
            response = http_session.post(api_url, json=data_pedido, timeout=(10, 90))
            
            if response.status_code == 429:
                return "ERRO 429: CALMA LÁ! Abusaste do rate limit. Fica 15 minutos de castigo."
                
            # Se o modelo experimental falhar, tenta o próximo
            if response.status_code == 503 and modelo_tentativa == MODELO_ATUAL:
                continue
                
            response.raise_for_status()
            dados = response.json()
            
            tokens_reais = dados.get("usage", {}).get("total_tokens", 0)
            multiplicador = CUSTO_MODELO.get(modelo_tentativa, 1)
            USAGE_DATA["tokens_usados"] += (tokens_reais * multiplicador)
            salvar_usage(USAGE_DATA)
            
            if modelo_tentativa != MODELO_ATUAL:
                MODELO_ATUAL = modelo_tentativa
                
            return dados["choices"][0]["message"]["content"]
            
        except requests.exceptions.Timeout:
            if modelo_tentativa == MODELO_ATUAL: continue
            return "ERRO DE TIMEOUT: O servidor demorou muito a responder."
        except requests.exceptions.ConnectionError:
            if modelo_tentativa == MODELO_ATUAL: continue
            return "ERRO DE CONEXÃO: Verifica a internet."
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 503 and modelo_tentativa == MODELO_ATUAL: continue
            if e.response.status_code == 404:
                return "ERRO 404: Rota não encontrada. O servidor no Render pode estar com o código antigo."
            return f"ERRO HTTP ({e.response.status_code}): {e.response.reason}"
        except Exception as e:
            if modelo_tentativa == MODELO_ATUAL: continue
            return f"ERRO INESPERADO: {e}"
    
    return "ERRO: Todos os modelos falharam. Tenta outro modelo no /models."

def executar_ferramenta(resposta):
    try:
        pensamento = ""
        match_think = re.search(r'<thinking>(.*?)</thinking>', resposta, re.DOTALL)
        if match_think: 
            pensamento = match_think.group(1).strip()
            resposta = resposta.replace(match_think.group(0), "")

        if "```json" in resposta: resposta = resposta.split("```json")[1].split("```")[0]
        elif "```" in resposta: resposta = resposta.split("```")[1].split("```")[0]
        
        if "<tool_call>" in resposta:
            cmd_match = re.search(r'<arg_value>(.*?)</arg_value>', resposta, re.DOTALL)
            if cmd_match: acao = {"tool": "run_command", "command": cmd_match.group(1).strip()}
            else: return None, False, pensamento
        else:
            acao = json.loads(resposta.strip())
            
        ferramenta = acao.get("tool")
        
        if ferramenta in ["run_command", "create_file", "run_code"]:
            alvo = os.getcwd()
            if ferramenta == "create_file":
                alvo = os.path.dirname(os.path.abspath(acao.get("path", ""))) or os.getcwd()
            
            if not pedir_permissao(alvo): return "Cancelado.", False, pensamento
            limpar_tela()
            
            if pensamento:
                console.print(Panel(f"[italic dim]{pensamento}[/italic dim]", title="🧠 Pensamento", border_style="magenta"))

            if ferramenta == "run_command":
                cmd = acao.get("command")
                if verificar_comando_perigoso(cmd):
                    mostrar_ban_aviso()
                    return "ACÇÃO BLOQUEADA PELO SISTEMA DE BAN.", False, pensamento
                if not pedir_aprovacao_comando(cmd):
                    return "O utilizador NEGOU a execução do comando.", False, pensamento

                with console.status(f"[bold yellow]⚙️ Executando:[/bold yellow] {cmd}", spinner="dots"):
                    res = subprocess.run(cmd, shell=True, capture_output=True, text=True)
                saida = (res.stdout + res.stderr).strip()
                if res.returncode != 0: return f"Erro:\n{saida}", True, pensamento
                return (saida or "Comando executado."), False, pensamento
                
            elif ferramenta == "create_file":
                path, content = acao.get("path"), acao.get("content")
                console.print(Panel(f"[bold cyan]📝 Criando arquivo:[/bold cyan] {path}", border_style="cyan"))
                syntax = Syntax(content, "python", theme="monokai", line_numbers=False)
                with Live(syntax, refresh_per_second=10, console=console):
                    if os.path.dirname(path): os.makedirs(os.path.dirname(path), exist_ok=True)
                    with open(path, "w", encoding="utf-8") as f: f.write(content)
                    time.sleep(0.5)
                return f"Arquivo {path} criado.", False, pensamento

            elif ferramenta == "run_code":
                code = acao.get("code")
                console.print(Panel(f"[bold yellow]🐍 O Agente quer executar Python:[/bold yellow]\n{code}", border_style="yellow"))
                if not questionary.confirm("Aprovas?").ask():
                    return "O utilizador NEGOU a execução do código.", False, pensamento
                with console.status("[bold yellow]🐍 Executando...[/bold yellow]", spinner="dots"):
                    res = subprocess.run(["python3", "-c", code], capture_output=True, text=True)
                saida = (res.stdout + res.stderr).strip()
                if res.returncode != 0: return f"Erro no código:\n{saida}", True, pensamento
                return (saida or "Código executado."), False, pensamento
        return None, False, pensamento
    except json.JSONDecodeError:
        return None, False, ""

def mostrar_help():
    table = Table(title="🦁 Tiny CLI - Comandos", show_header=True, header_style="bold green")
    table.add_column("Comando", style="cyan", width=15)
    table.add_column("Descrição", style="white")
    table.add_row("/help", "Mostra este menu")
    table.add_row("/models", "Troca o modelo de IA")
    table.add_row("/usage", "Mostra a cota")
    table.add_row("/session", "Gerencia sessões")
    table.add_row("/clear", "Limpa o terminal")
    console.print(table)

def mostrar_usage():
    usados = USAGE_DATA.get("tokens_usados", 0)
    restantes = max(0, LIMITE_SEMANAL - usados)
    percent = (usados / LIMITE_SEMANAL) * 100
    visual = min(100, percent)
    blocos = int((visual / 100) * 20)
    barra = "█" * blocos + "░" * (20 - blocos)
    cor = "green" if percent < 50 else "yellow" if percent < 80 else "red"
    
    console.print(Panel(
        f"[bold green]Modelo:[/bold green] {MODELO_ATUAL}\n"
        f"[bold]Tokens Usados:[/bold] {usados} / {LIMITE_SEMANAL}\n"
        f"[{cor}]{barra}[/{cor}] {percent:.2f}%\n"
        f"[bold yellow]Restantes:[/bold yellow] {restantes}", 
        title="📊 Usage (5M)", 
        border_style="blue"
    ))

def menu_sessoes(sessao_atual, mensagens_atuais):
    sessoes = listar_sessoes()
    opcoes = ["Nova Sessão"] + [f"Carregar: {s}" for s in sessoes]
    escolha = questionary.select("Sessões:", choices=opcoes, style=custom_style).ask()
    
    if escolha == "Nova Sessão": 
        try:
            with open(os.path.expanduser("~/.tinycli/SKILLS.md"), "r", encoding="utf-8") as f: skill = f.read()
        except: skill = "Você é o Tiny CLI."
        return str(uuid.uuid4())[:8], [{"role": "system", "content": skill}]
        
    elif escolha and escolha.startswith("Carregar:"):
        sid = escolha.replace("Carregar: ", "")
        msgs = carregar_sessao(sid)
        if msgs: 
            return sid, msgs
    return sessao_atual, mensagens_atuais

def menu_models():
    global MODELO_ATUAL
    escolha = questionary.select("Modelo:", choices=MODELOS_DISPONIVEIS, style=custom_style, default=MODELO_ATUAL).ask()
    if escolha:
        MODELO_ATUAL = escolha
        multiplicador = CUSTO_MODELO.get(MODELO_ATUAL, 1)
        
        if MODELO_ATUAL == "longcat-2.5":
            console.print(Panel(
                "[bold yellow]⚠️ Modelo Experimental[/bold yellow]\n"
                "O LongCat 2.5 é um preview gratuito. Se ele falhar, o sistema troca automaticamente para o DeepSeek.",
                border_style="yellow", title="🐱 Meituan"
            ))
        elif multiplicador >= 6:
            console.print(Panel(
                f"[bold yellow]🚀 Upgrade Sugerido![/bold yellow]\n\n"
                f"O modelo [bold]{MODELO_ATUAL}[/bold] consome [bold]{multiplicador}x[/bold] mais a tua cota.\n"
                f"Para uso intensivo sem limites, considera o [bold cyan]Tiny CLI Go[/bold cyan].\n"
                f"Por agora, o modelo [green]DeepSeek V4.1[/green] é a tua melhor opção gratuita.",
                border_style="yellow", title="💡 Dica"
            ))
        else:
            console.print(f"[green]✅ Modelo: {MODELO_ATUAL} (Custo: {multiplicador}x)[/green]")

def gerar_banner():
    try: return pyfiglet.figlet_format("TINY CLI", font="slant")
    except: return "TINY CLI"

def barra_status(session_id):
    status = f"[dim]Modelo: [bold]{MODELO_ATUAL}[/bold] | Sessão: {session_id} | Tokens: {USAGE_DATA.get('tokens_usados', 0)}/{LIMITE_SEMANAL} | Local: {os.getcwd()}[/dim]"
    console.print(Panel(status, border_style="dim", padding=(0, 1)))

def main():
    global MODELO_ATUAL
    limpar_tela()
    
    verificar_atualizacao()

    os.makedirs(os.path.dirname(TERMOS_FILE), exist_ok=True)
    if not os.path.exists(TERMOS_FILE):
        if aceitar_termos():
            with open(TERMOS_FILE, "w") as f: json.dump({"aceite": True}, f)
            limpar_tela()
    
    escolher_pasta_inicial()
    
    console.print(Panel(f"[bold green]{gerar_banner()}[/bold green]\n[dim]v{VERSAO_LOCAL} - Model Pool Edition[/dim]", border_style="green", title="🦁 Tiny Cloud CLI"))
    
    session_id = str(uuid.uuid4())[:8]
    try:
        with open(os.path.expanduser("~/.tinycli/SKILLS.md"), "r", encoding="utf-8") as f: skill = f.read()
    except: skill = "Você é o Tiny CLI."
    mensagens = [{"role": "system", "content": skill}]
    
    while True:
        try:
            barra_status(session_id)
            prompt = questionary.text("👤 Tu:", style=custom_style, qmark="").ask()
            if prompt is None: continue
            cmd = prompt.lower().strip()
            
            if cmd in ["/help", "help"]: mostrar_help(); continue
            elif cmd == "/usage": mostrar_usage(); continue
            elif cmd == "/models": menu_models(); continue
            elif cmd == "/session":
                session_id, mensagens = menu_sessoes(session_id, mensagens)
                salvar_sessao(session_id, mensagens)
                limpar_tela()
                
                # Mostra o histórico carregado
                if len(mensagens) > 1:
                    console.print(Panel("[bold cyan]Histórico Carregado:[/bold cyan]", border_style="cyan"))
                    for msg in mensagens:
                        if msg["role"] == "user":
                            console.print(f"[bold blue]👤 Tu:[/bold blue] {msg['content']}")
                        elif msg["role"] == "assistant":
                            console.print(f"[bold green]🤖 Tiny:[/bold green] {msg['content']}")
                    console.print()
                continue
            elif cmd == "/clear": limpar_tela(); continue
            elif cmd in ["sair", "exit"]: break
            elif not prompt.strip(): continue
            
            # O SOFT NUDGE OCULTO (A cada 5 pedidos)
            if USAGE_DATA.get("requests", 0) % 5 == 0 and USAGE_DATA.get("requests", 0) > 0:
                console.print(Panel(
                    "[bold cyan]💡 Sabias?[/bold cyan]\n"
                    "Os utilizadores do plano Free têm limites. Se precisares de mais potência, "
                    "o [bold]Tiny CLI Go[/bold] está a chegar para remover os limites e dar acesso prioritário ao GPT-6 Luna.\n"
                    "[dim]Continua a usar o Free por agora. Estás a ir muito bem![/dim]",
                    border_style="cyan", title="🚀 Upgrade"
                ))

            mensagens.append({"role": "user", "content": prompt})
            
            tentativas = 0
            while tentativas < 5:
                with console.status(f"[bold cyan]⏳ Pensando...[/bold cyan]", spinner="bouncingBar"):
                    resposta = chamar_ia(mensagens)
                mensagens.append({"role": "assistant", "content": resposta})
                
                resultado, deu_erro, pensamento = executar_ferramenta(resposta)
                
                if resultado:
                    if deu_erro:
                        mensagens.append({"role": "user", "content": f"Erro:\n{resultado}\nCorrige e tenta de novo."})
                        tentativas += 1
                        time.sleep(1)
                        limpar_tela()
                        continue
                    else:
                        mensagens.append({"role": "user", "content": f"Resultado:\n{resultado}"})
                        continue
                else:
                    limpar_tela()
                    console.print(Panel(Markdown(resposta), title=f"🤖 Tiny ({MODELO_ATUAL})", border_style="green"))
                    break
            salvar_sessao(session_id, mensagens)
        except KeyboardInterrupt:
            salvar_sessao(session_id, mensagens)
            break

if __name__ == "__main__":
    main()