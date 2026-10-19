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
from rich.prompt import Confirm

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

LIMITE_SEMANAL = 1000

# --- GESTÃO DE SESSÕES ---
def listar_sessoes():
    if not os.path.exists(SESSIONS_DIR):
        return []
    sessoes = []
    for f in os.listdir(SESSIONS_DIR):
        if f.endswith(".json"):
            sessoes.append(f.replace(".json", ""))
    return sessoes

def carregar_sessao(session_id):
    path = os.path.join(SESSIONS_DIR, f"{session_id}.json")
    if os.path.exists(path):
        with open(path, "r") as f:
            return json.load(f)
    return None

def salvar_sessao(session_id, mensagens):
    os.makedirs(SESSIONS_DIR, exist_ok=True)
    path = os.path.join(SESSIONS_DIR, f"{session_id}.json")
    with open(path, "w") as f:
        json.dump(mensagens, f)

def nova_sessao():
    session_id = str(uuid.uuid4())[:8]
    return session_id, []

# --- SISTEMA DE USAGE ---
def carregar_usage():
    os.makedirs(os.path.dirname(USAGE_FILE), exist_ok=True)
    if os.path.exists(USAGE_FILE):
        try:
            with open(USAGE_FILE, "r") as f:
                return json.load(f)
        except:
            pass
    return {"requests": 0, "tokens_usados": 0}

def salvar_usage(data):
    os.makedirs(os.path.dirname(USAGE_FILE), exist_ok=True)
    with open(USAGE_FILE, "w") as f:
        json.dump(data, f)

USAGE_DATA = carregar_usage()

# --- SISTEMA DE CONFIANÇA ---
def carregar_confiaveis():
    if os.path.exists(TRUST_FILE):
        with open(TRUST_FILE, "r") as f:
            return set(f.read().splitlines())
    return set()

def salvar_confiavel(path):
    with open(TRUST_FILE, "a") as f:
        f.write(f"{os.path.abspath(path)}\n")

DIRETORIOS_CONFIAVEIS = carregar_confiaveis()

def pedir_permissao(caminho):
    abs_path = os.path.abspath(caminho)
    if abs_path in DIRETORIOS_CONFIAVEIS:
        return True
    console.print(f"\n[yellow]⚠️  O agente quer acessar:[/yellow] [bold white]{abs_path}[/bold white]")
    escolha = questionary.select(
        "Confiar nesse diretório?", choices=["Sim", "Não"], style=custom_style
    ).ask()
    if escolha == "Sim":
        DIRETORIOS_CONFIAVEIS.add(abs_path)
        salvar_confiavel(abs_path)
        return True
    return False

# --- COMUNICAÇÃO COM A NUVEM ---
def chamar_ia(mensagens):
    global USAGE_DATA
    USAGE_DATA["requests"] += 1
    api_url = f"{SERVER_URL}/api/chat"
    data = {"messages": mensagens}
    try:
        req = urllib.request.Request(api_url, data=json.dumps(data).encode("utf-8"), headers={"Content-Type": "application/json"}, method="POST")
        with urllib.request.urlopen(req) as response:
            dados = json.loads(response.read().decode("utf-8"))
            tokens = dados.get("usage", {}).get("total_tokens", 0)
            USAGE_DATA["tokens_usados"] += tokens
            salvar_usage(USAGE_DATA)
            return dados["choices"][0]["message"]["content"]
    except urllib.error.HTTPError as e:
        return f"ERRO NO SERVIDOR ({e.code}): {e.reason}"
    except Exception as e:
        return f"ERRO DE CONEXÃO: {e}"

# --- COMPACT (RESUMIR HISTÓRICO) ---
def compactar_historico(mensagens):
    if len(mensagens) < 3:
        console.print("[yellow]Histórico muito curto para compactar.[/yellow]")
        return mensagens
    
    console.print("[dim]⏳ Gerando resumo do histórico...[/dim]")
    prompt_resumo = [
        {"role": "system", "content": "Você é um assistente que resume conversas. Resuma a conversa abaixo de forma concisa, mantendo as decisões importantes, ficheiros criados/editados e o objetivo atual. Responda APENAS com o resumo, sem introduções."},
        {"role": "user", "content": json.dumps(mensagens)}
    ]
    resumo = chamar_ia(prompt_resumo)
    
    if resumo.startswith("ERRO"):
        console.print(f"[red]Falha ao compactar: {resumo}[/red]")
        return mensagens
    
    # Substitui o histórico por um resumo + a última mensagem do utilizador
    novo_historico = [
        {"role": "system", "content": f"Resumo da conversa anterior: {resumo}"},
        mensagens[-1] if mensagens[-1]["role"] == "user" else {"role": "user", "content": "Continuar."}
    ]
    console.print("[green]✅ Histórico compactado![/green]")
    return novo_historico

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
            
            if not pedir_permissao(alvo):
                return "Ação cancelada pelo utilizador."

            if ferramenta == "run_command":
                cmd = acao.get("command")
                with console.status(f"[yellow]⚙️ Executando: {cmd}[/yellow]", spinner="dots"):
                    res = subprocess.run(cmd, shell=True, capture_output=True, text=True)
                return (res.stdout + res.stderr) or "Comando executado."
                
            elif ferramenta == "create_file":
                path = acao.get("path")
                content = acao.get("content")
                console.print(f"\n[bold cyan]📝 Criando arquivo:[/bold cyan] [bold white]{path}[/bold white]")
                syntax = Syntax(content, "python", theme="monokai", line_numbers=False)
                with Live(syntax, refresh_per_second=10, console=console):
                    if os.path.dirname(path): os.makedirs(os.path.dirname(path), exist_ok=True)
                    with open(path, "w", encoding="utf-8") as f:
                        f.write(content)
                    time.sleep(0.5)
                return f"Arquivo {path} criado."

            elif ferramenta == "run_code":
                code = acao.get("code")
                with console.status("[yellow]🐍 Executando Python[/yellow]", spinner="dots"):
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
    table.add_row("/models", "Mostra os modelos disponíveis")
    table.add_row("/usage", "Mostra a cota e tokens restantes")
    table.add_row("/session", "Lista, carrega ou cria sessões")
    table.add_row("/compact", "Resume o histórico para economizar tokens")
    table.add_row("/clear", "Limpa o terminal")
    table.add_row("sair", "Fecha o Tiny CLI")
    console.print(table)

def mostrar_usage():
    usados = USAGE_DATA.get("tokens_usados", 0)
    restantes = max(0, LIMITE_SEMANAL - usados)
    percentagem = (usados / LIMITE_SEMANAL) * 100
    blocos = int((usados / LIMITE_SEMANAL) * 20)
    barra = "█" * blocos + "░" * (20 - blocos)
    cor = "green" if percentagem < 50 else "yellow" if percentagem < 80 else "red"
    console.print(Panel(
        f"[bold]Tokens usados:[/bold] {usados} / {LIMITE_SEMANAL}\n"
        f"[{cor}]{barra}[/{cor}] {percentagem:.1f}%\n"
        f"[bold yellow]Restantes:[/bold yellow] {restantes}\n"
        f"[dim]Requests: {USAGE_DATA.get('requests', 0)}[/dim]",
        title="📊 Usage", border_style="blue"
    ))

def menu_sessoes(sessao_atual):
    sessoes = listar_sessoes()
    opcoes = ["Nova Sessão"] + [f"Carregar: {s}" for s in sessoes]
    escolha = questionary.select("Gerenciar Sessões:", choices=opcoes, style=custom_style).ask()
    
    if escolha == "Nova Sessão":
        return nova_sessao()
    elif escolha and escolha.startswith("Carregar:"):
        sid = escolha.replace("Carregar: ", "")
        msgs = carregar_sessao(sid)
        if msgs:
            console.print(f"[green]✅ Sessão {sid} carregada.[/green]")
            return sid, msgs
    return sessao_atual, carregar_sessao(sessao_atual) or []

# --- LOOP PRINCIPAL ---
def main():
    console.print(Panel("[bold green]🦁 Tiny Cloud CLI v3.8[/bold green]\nDigita [bold cyan]/help[/bold cyan]", border_style="green"))
    
    session_id, mensagens = nova_sessao()
    if not mensagens:
        try:
            with open(os.path.expanduser("~/.tinycli_skill.md"), "r", encoding="utf-8") as f:
                skill = f.read()
        except:
            skill = "Você é o Tiny CLI."
        mensagens = [{"role": "system", "content": skill}]
    
    if os.getcwd() not in DIRETORIOS_CONFIAVEIS:
        pedir_permissao(os.getcwd())
    
    while True:
        try:
            prompt = console.input(f"[bold blue]👤 Tu ({session_id}):[/bold blue] ")
            cmd = prompt.lower().strip()
            
            if cmd in ["/help", "help"]: mostrar_help(); continue
            elif cmd == "/usage": mostrar_usage(); continue
            elif cmd == "/models":
                console.print("[cyan]Modelo: deepseek-v4.1-flash (forçado pelo servidor)[/cyan]")
                continue
            elif cmd == "/session":
                session_id, mensagens = menu_sessoes(session_id)
                salvar_sessao(session_id, mensagens)
                continue
            elif cmd == "/compact":
                mensagens = compactar_historico(mensagens)
                salvar_sessao(session_id, mensagens)
                continue
            elif cmd == "/clear":
                os.system('clear' if os.name == 'posix' else 'cls'); continue
            elif cmd in ["sair", "exit"]:
                salvar_sessao(session_id, mensagens)
                break
            elif not prompt.strip(): continue
            
            mensagens.append({"role": "user", "content": prompt})
            console.print("[dim]⏳ Enviando...[/dim]")
            
            while True:
                resposta = chamar_ia(mensagens)
                mensagens.append({"role": "assistant", "content": resposta})
                
                resultado = executar_ferramenta(resposta)
                if resultado:
                    mensagens.append({"role": "user", "content": f"Resultado:\n{resultado}"})
                    console.print("[dim]⏳ Processando...[/dim]")
                    continue
                
                console.print(Panel(Markdown(resposta), title="🤖 Tiny", border_style="green"))
                break
            
            salvar_sessao(session_id, mensagens)
                
        except KeyboardInterrupt:
            salvar_sessao(session_id, mensagens)
            break

if __name__ == "__main__":
    main()