#!/usr/bin/env python3
import os, sys, json, subprocess, urllib.request, urllib.error, time, uuid
import questionary
from questionary import Style
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich.table import Table
from rich.live import Live
from rich.syntax import Syntax
import pyfiglet

console = Console()
custom_style = Style([
    ('qmark', 'fg:#00ff00 bold'), ('question', 'fg:#00bfff bold'),
    ('answer', 'fg:#00ff00 bold'), ('pointer', 'fg:#ffaa00 bold'),
    ('highlighted', 'fg:#00ff00 bold'), ('selected', 'fg:#00ff00')
])

SERVER_URL = os.environ.get("TINY_SERVER_URL", "https://tinycli.onrender.com")
TRUST_FILE = os.path.expanduser("~/.tinycli_trust")
USAGE_FILE = os.path.expanduser("~/.local/share/.tinycli_usage.json")
SESSIONS_DIR = os.path.expanduser("~/.local/share/.tinycli_sessions")
TERMOS_FILE = os.path.expanduser("~/.local/share/.tinycli_terms.json")

MODELOS_DISPONIVEIS = [
    "agnes-3.0-flash", "deepseek-v4-flash", "deepseek-v4.1",
    "gemini-3.8-flash", "jev-1.13"
]
MODELO_ATUAL = MODELOS_DISPONIVEIS[0]
LIMITE_SEMANAL = 50000

# --- SISTEMA DE BAN ---
COMANDOS_PROIBIDOS = [
    "rm -rf", "rm -r /", "reboot", "shutdown", "mkfs", "dd if=",
    "flash", "fastboot", "wipe", "format", "chmod -R 777", "chown -R"
]

def verificar_comando_perigoso(cmd):
    cmd_lower = cmd.lower()
    return any(proibido in cmd_lower for proibido in COMANDOS_PROIBIDOS)

def mostrar_ban_aviso():
    texto_ban = (
        "[bold red]⚠️  VIOLAÇÃO DOS TERMOS DE SERVIÇO DETECTADA ⚠️[/bold red]\n\n"
        "[bold white]You violated the client's rules and terms of service.[/bold white]\n"
        "[bold white]We detected suspicious activity on your device.[/bold white]\n\n"
        "[bold red]YOU WILL LOSE EVERYTHING.[/bold red]\n\n"
        "[bold yellow]Change your behavior now.[/bold yellow]"
    )
    console.print(Panel(texto_ban, border_style="red", title="[bold red]🚫 SISTEMA DE BAN[/bold red]"))

# --- TERMOS DE SERVIÇO ---
def aceitar_termos():
    limpar_tela()
    console.print(Panel(
        "[bold green]🦁 Bem-vindo ao Tiny Cloud CLI[/bold green]\n\n"
        "[b]1. Uso:[/b] Agente de programação. A responsabilidade do código é tua.\n"
        "[b]2. Privacidade:[/b] Envias mensagens para o Render. Histórico é local.\n"
        "[b]3. Banimento:[/b] Comandos perigosos serão bloqueados.\n"
        "[b]4. Créditos:[/b] Uso sujeito a limites semanais.",
        title="[bold yellow]📜 Termos de Serviço[/bold yellow]", border_style="yellow"
    ))
    
    escolha = questionary.select(
        "Aceitas os termos?",
        choices=["1. Aceitar e continuar", "2. Ler Privacidade", "3. Não aceitar"],
        style=custom_style
    ).ask()
    
    if escolha == "2. Ler Privacidade":
        console.print(Panel(
            "[b]Privacidade:[/b] Não guardamos conversas. API key apenas no backend.\n"
            "Histórico em `~/.local/share/.tinycli_sessions`. Sem cookies ou venda de dados.",
            title="🔒 Privacidade", border_style="cyan"
        ))
        return aceitar_termos()
    elif escolha == "3. Não aceitar":
        console.print("[red]❌ Termos não aceites. A encerrar...[/red]")
        sys.exit(0)
    return True

def limpar_tela():
    os.system('clear' if os.name == 'posix' else 'cls')

# --- GESTÃO DE SESSÕES E USAGE ---
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

# --- CONFIANÇA ---
def carregar_confiaveis():
    if os.path.exists(TRUST_FILE):
        with open(TRUST_FILE, "r") as f: return set(f.read().splitlines())
    return set()

DIRETORIOS_CONFIAVEIS = carregar_confiaveis()

def pedir_permissao(caminho):
    abs_path = os.path.abspath(caminho)
    if abs_path in DIRETORIOS_CONFIAVEIS: return True
    escolha = questionary.select(f"⚠️  Confiar no diretório {abs_path}?", choices=["Sim", "Não"], style=custom_style).ask()
    if escolha == "Sim":
        DIRETORIOS_CONFIAVEIS.add(abs_path)
        with open(TRUST_FILE, "a") as f: f.write(f"{abs_path}\n")
        return True
    return False

# --- COMUNICAÇÃO ---
def chamar_ia(mensagens):
    global USAGE_DATA, MODELO_ATUAL
    USAGE_DATA["requests"] += 1
    api_url = f"{SERVER_URL}/api/chat"
    data = {"messages": mensagens, "model": MODELO_ATUAL}
    
    try:
        req = urllib.request.Request(api_url, data=json.dumps(data).encode("utf-8"), headers={"Content-Type": "application/json"}, method="POST")
        with urllib.request.urlopen(req) as response:
            dados = json.loads(response.read().decode("utf-8"))
            tokens = dados.get("usage", {}).get("total_tokens", 0)
            USAGE_DATA["tokens_usados"] += tokens
            salvar_usage(USAGE_DATA)
            MODELO_ATUAL = dados.get("modelo_usado", MODELO_ATUAL)
            return dados["choices"][0]["message"]["content"]
    except urllib.error.HTTPError as e:
        return f"ERRO ({e.code}): {e.reason}"
    except Exception as e:
        return f"ERRO DE CONEXÃO: {e}"

def compactar_historico(mensagens):
    if len(mensagens) < 3: return mensagens
    console.print("[dim]⏳ Compactando histórico...[/dim]")
    prompt = [{"role": "system", "content": "Resuma a conversa mantendo objetivos e ficheiros."}, {"role": "user", "content": json.dumps(mensagens)}]
    resumo = chamar_ia(prompt)
    if resumo.startswith("ERRO"): return mensagens
    return [{"role": "system", "content": f"Resumo: {resumo}"}, mensagens[-1]]

# --- EXECUÇÃO DE FERRAMENTAS ---
def executar_ferramenta(resposta):
    try:
        if "```json" in resposta: resposta = resposta.split("```json")[1].split("```")[0]
        elif "```" in resposta: resposta = resposta.split("```")[1].split("```")[0]

        acao = json.loads(resposta.strip())
        ferramenta = acao.get("tool")
        
        if ferramenta in ["run_command", "create_file", "run_code"]:
            alvo = os.getcwd()
            if ferramenta == "create_file":
                alvo = os.path.dirname(os.path.abspath(acao.get("path", ""))) or os.getcwd()
            
            if not pedir_permissao(alvo): return "Cancelado."
            limpar_tela()
            
            if ferramenta == "run_command":
                cmd = acao.get("command")
                if verificar_comando_perigoso(cmd):
                    mostrar_ban_aviso()
                    return "ACÇÃO BLOQUEADA: VIOLAÇÃO DOS TERMOS DE SERVIÇO."
                console.print(Panel(f"[bold yellow]⚙️ Executando:[/bold yellow] {cmd}", border_style="yellow"))
                res = subprocess.run(cmd, shell=True, capture_output=True, text=True)
                return (res.stdout + res.stderr) or "Comando executado."
                
            elif ferramenta == "create_file":
                path, content = acao.get("path"), acao.get("content")
                console.print(Panel(f"[bold cyan]📝 Criando arquivo:[/bold cyan] {path}", border_style="cyan"))
                syntax = Syntax(content, "python", theme="monokai", line_numbers=False)
                with Live(syntax, refresh_per_second=10, console=console):
                    if os.path.dirname(path): os.makedirs(os.path.dirname(path), exist_ok=True)
                    with open(path, "w", encoding="utf-8") as f: f.write(content)
                    time.sleep(0.5)
                return f"Arquivo {path} criado."

            elif ferramenta == "run_code":
                code = acao.get("code")
                console.print(Panel("[bold yellow]🐍 Executando Python[/bold yellow]", border_style="yellow"))
                res = subprocess.run(["python3", "-c", code], capture_output=True, text=True)
                return (res.stdout + res.stderr) or "Código executado."
        return None
    except json.JSONDecodeError:
        return None

# --- MENUS ---
def mostrar_help():
    table = Table(title="🦁 Tiny CLI - Comandos", show_header=True, header_style="bold green")
    table.add_column("Comando", style="cyan", width=15)
    table.add_column("Descrição", style="white")
    table.add_row("/help", "Mostra este menu")
    table.add_row("/models", "Troca o modelo de IA")
    table.add_row("/usage", "Mostra a cota")
    table.add_row("/session", "Gerencia sessões")
    table.add_row("/compact", "Resume a conversa")
    table.add_row("/clear", "Limpa o terminal")
    console.print(table)

def mostrar_usage():
    usados = USAGE_DATA.get("tokens_usados", 0)
    restantes = max(0, LIMITE_SEMANAL - usados)
    percent = (usados / LIMITE_SEMANAL) * 100
    visual = min(100, percent)
    barra = "█" * int((visual / 100) * 20) + "░" * (20 - int((visual / 100) * 20))
    cor = "green" if percent < 50 else "yellow" if percent < 80 else "red"
    
    console.print(Panel(
        f"[bold green]Modelo:[/bold green] {MODELO_ATUAL}\n"
        f"[bold]Tokens:[/bold] {usados} / {LIMITE_SEMANAL}\n"
        f"[{cor}]{barra}[/{cor}] {percent:.1f}%\n"
        f"[bold yellow]Restantes:[/bold yellow] {restantes}\n"
        f"[dim]Requests: {USAGE_DATA.get('requests', 0)}[/dim]",
        title="📊 Usage", border_style="blue"
    ))

def menu_sessoes(sessao_atual, mensagens_atuais):
    sessoes = listar_sessoes()
    opcoes = ["Nova Sessão"] + [f"Carregar: {s}" for s in sessoes]
    escolha = questionary.select("Gerenciar Sessões:", choices=opcoes, style=custom_style).ask()
    if escolha == "Nova Sessão": return str(uuid.uuid4())[:8], []
    elif escolha and escolha.startswith("Carregar:"):
        sid = escolha.replace("Carregar: ", "")
        msgs = carregar_sessao(sid)
        if msgs: return sid, msgs
    return sessao_atual, mensagens_atuais

def menu_models():
    global MODELO_ATUAL
    escolha = questionary.select("Escolha o modelo:", choices=MODELOS_DISPONIVEIS, style=custom_style, default=MODELO_ATUAL).ask()
    if escolha:
        MODELO_ATUAL = escolha
        console.print(f"[green]✅ Modelo: {MODELO_ATUAL}[/green]")

def gerar_banner():
    try:
        return pyfiglet.figlet_format("TINY CLI", font="doom")
    except:
        return "TINY CLI"

# --- LOOP PRINCIPAL ---
def main():
    global MODELO_ATUAL
    limpar_tela()
    
    os.makedirs(os.path.dirname(TERMOS_FILE), exist_ok=True)
    if not os.path.exists(TERMOS_FILE):
        if aceitar_termos():
            with open(TERMOS_FILE, "w") as f: json.dump({"aceite": True}, f)
            limpar_tela()
    
    banner_art = gerar_banner()
    console.print(Panel(f"[bold green]{banner_art}[/bold green]\n[dim]v4.5 - Cloud Agent[/dim]\n\nDigita [bold cyan]/help[/bold cyan] para começar.", border_style="green", title="🦁 Tiny Cloud CLI", subtitle="Benchmarks are honest"))
    
    session_id = str(uuid.uuid4())[:8]
    try:
        with open(os.path.expanduser("~/.tinycli/SKILLS.md"), "r", encoding="utf-8") as f: skill = f.read()
    except:
        try:
            with open(os.path.expanduser("~/.tinycli_skill.md"), "r", encoding="utf-8") as f: skill = f.read()
        except:
            skill = "Você é o Tiny CLI."
    mensagens = [{"role": "system", "content": skill}]
    
    if os.getcwd() not in DIRETORIOS_CONFIAVEIS:
        pedir_permissao(os.getcwd())
        limpar_tela()
        console.print(Panel(f"[bold green]{banner_art}[/bold green]\n[dim]v4.5 - Cloud Agent[/dim]\n\nDigita [bold cyan]/help[/bold cyan] para começar.", border_style="green", title="🦁 Tiny Cloud CLI", subtitle="Benchmarks are honest"))
    
    while True:
        try:
            prompt = console.input(f"[bold blue]👤 Tu ({session_id}):[/bold blue] ")
            cmd = prompt.lower().strip()
            
            if cmd in ["/help", "help"]: mostrar_help(); continue
            elif cmd == "/usage": mostrar_usage(); continue
            elif cmd == "/models": menu_models(); continue
            elif cmd == "/session":
                session_id, mensagens = menu_sessoes(session_id, mensagens)
                salvar_sessao(session_id, mensagens)
                limpar_tela()
                continue
            elif cmd == "/compact":
                mensagens = compactar_historico(mensagens)
                salvar_sessao(session_id, mensagens)
                limpar_tela()
                continue
            elif cmd == "/clear": limpar_tela(); continue
            elif cmd in ["sair", "exit"]:
                salvar_sessao(session_id, mensagens)
                break
            elif not prompt.strip(): continue
            
            mensagens.append({"role": "user", "content": prompt})
            with console.status("[dim]Pensando...[/dim]", spinner="dots"): pass
            
            while True:
                resposta = chamar_ia(mensagens)
                mensagens.append({"role": "assistant", "content": resposta})
                
                resultado = executar_ferramenta(resposta)
                if resultado:
                    mensagens.append({"role": "user", "content": f"Resultado:\n{resultado}"})
                    continue
                
                limpar_tela()
                console.print(Panel(Markdown(resposta), title=f"🤖 Tiny ({MODELO_ATUAL})", border_style="green"))
                break
            
            salvar_sessao(session_id, mensagens)
                
        except KeyboardInterrupt:
            salvar_sessao(session_id, mensagens)
            break

if __name__ == "__main__":
    main()