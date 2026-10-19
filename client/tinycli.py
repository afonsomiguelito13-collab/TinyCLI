#!/usr/bin/env python3
import os, sys, json, subprocess, urllib.request, urllib.error
import questionary
from questionary import Style
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich.table import Table

console = Console()
custom_style = Style([('qmark', 'fg:#00ff00 bold'), ('question', 'fg:#00bfff bold'), ('answer', 'fg:#00ff00 bold'), ('pointer', 'fg:#ffaa00 bold'), ('highlighted', 'fg:#00ff00 bold'), ('selected', 'fg:#00ff00')])

SERVER_URL = os.environ.get("TINY_SERVER_URL", "https://tinycli.onrender.com")
TRUST_FILE = os.path.expanduser("~/.tinycli_trust")
USAGE_FILE = os.path.expanduser("~/.local/share/.tinycli_usage.json")

# --- SISTEMA DE USAGE (MÁGICA DO WEEKLY) ---
LIMITE_SEMANAL = 1000 # Limite de tokens (podes mudar ou receber do servidor)

def carregar_usage():
    os.makedirs(os.path.dirname(USAGE_FILE), exist_ok=True)
    if os.path.exists(USAGE_FILE):
        try:
            with open(USAGE_FILE, "r") as f:
                return json.load(f)
        except:
            pass
    return {"requests": 0, "tokens_usados": 0, "tokens_restantes": LIMITE_SEMANAL}

def salvar_usage(data):
    os.makedirs(os.path.dirname(USAGE_FILE), exist_ok=True)
    with open(USAGE_FILE, "w") as f:
        json.dump(data, f)

USAGE_DATA = carregar_usage()

# --- SISTEMA DE CONFIANÇA (TRUST UI) ---
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
        
    console.print(f"\n[yellow]⚠️  O agente quer acessar um novo diretório:[/yellow] [bold white]{abs_path}[/bold white]")
    escolha = questionary.select(
        "Confiar nesse diretório e salvar nas preferências?",
        choices=["Sim, confiar e salvar", "Não, bloquear ação"],
        style=custom_style
    ).ask()
    
    if escolha == "Sim, confiar e salvar":
        DIRETORIOS_CONFIAVEIS.add(abs_path)
        salvar_confiavel(abs_path)
        console.print(f"[green]✅ Diretório confiado.[/green]\n")
        return True
    else:
        console.print("[red]❌ Ação bloqueada.[/red]\n")
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
            
            # O servidor devolve os tokens usados
            tokens_usados = dados.get("usage", {}).get("total_tokens", 0)
            USAGE_DATA["tokens_usados"] += tokens_usados
            USAGE_DATA["tokens_restantes"] = max(0, LIMITE_SEMANAL - USAGE_DATA["tokens_usados"])
            salvar_usage(USAGE_DATA)
            
            return dados["choices"][0]["message"]["content"]
    except urllib.error.HTTPError as e:
        return f"ERRO NO SERVIDOR ({e.code}): {e.reason}"
    except Exception as e:
        return f"ERRO DE CONEXÃO: O servidor está offline?"

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
                with console.status(f"[yellow]📝 Escrevendo: {path}[/yellow]", spinner="dots"):
                    if os.path.dirname(path): os.makedirs(os.path.dirname(path), exist_ok=True)
                    with open(path, "w", encoding="utf-8") as f:
                        f.write(content)
                return f"Arquivo {path} criado."

            elif ferramenta == "run_code":
                code = acao.get("code")
                with console.status("[yellow]🐍 Executando Python[/yellow]", spinner="dots"):
                    res = subprocess.run(["python3", "-c", code], capture_output=True, text=True)
                return (res.stdout + res.stderr) or "Código executado."

        return None
    except json.JSONDecodeError:
        return None

# --- MENUS DE COMANDOS ---
def mostrar_help():
    table = Table(title="🦁 Tiny CLI - Comandos", show_header=True, header_style="bold green")
    table.add_column("Comando", style="cyan", width=12)
    table.add_column("Descrição", style="white")
    
    table.add_row("/help", "Mostra este menu de ajuda")
    table.add_row("/models", "Mostra os modelos disponíveis e qual está ativo")
    table.add_row("/usage", "Mostra a tua cota, tokens restantes e barra de progresso")
    table.add_row("/clear", "Limpa o terminal")
    table.add_row("sair", "Fecha o Tiny CLI")
    
    console.print(table)

def mostrar_usage():
    # Calcula a percentagem
    usados = USAGE_DATA.get("tokens_usados", 0)
    limite = LIMITE_SEMANAL
    restantes = max(0, limite - usados)
    percentagem = (usados / limite) * 100
    
    # Cria a barra de progresso visual
    blocos_cheios = int((usados / limite) * 20)
    barra = "█" * blocos_cheios + "░" * (20 - blocos_cheios)
    
    # Cor da barra baseada no uso
    cor = "green" if percentagem < 50 else "yellow" if percentagem < 80 else "red"
    
    console.print(Panel(
        f"[bold green]Modelo Atual:[/bold green] deepseek-v4.1-flash (Servidor)\n"
        f"[bold cyan]Servidor:[/bold cyan] {SERVER_URL}\n\n"
        f"[bold]Uso Semanal (Tokens):[/bold] {usados} / {limite}\n"
        f"[{cor}]{barra}[/{cor}] {percentagem:.1f}%\n\n"
        f"[bold yellow]Restantes:[/bold yellow] {restantes} tokens\n"
        f"[dim]Requests feitos: {USAGE_DATA.get('requests', 0)}[/dim]",
        title="📊 Usage Tracker (Weekly)",
        border_style="blue"
    ))

def mostrar_models():
    table = Table(title="🧠 Modelos Disponíveis (BeatAPI)", show_header=True, header_style="bold magenta")
    table.add_column("Modelo", style="cyan")
    table.add_column("Status", style="green")
    
    table.add_row("deepseek-v4.1-flash", "✅ Ativo (Forçado pelo Servidor)")
    table.add_row("deepseek-v4-flash", "🔒 Bloqueado pelo Servidor")
    table.add_row("glm-5.3", "🔒 Bloqueado pelo Servidor")
    table.add_row("gemini-3.8-flash", "🔒 Bloqueado pelo Servidor")
    
    console.print(table)
    console.print("[dim]* O servidor decide o modelo para garantir a cota grátis.[/dim]\n")

# --- LOOP PRINCIPAL ---
def main():
    console.print(Panel("[bold green]🦁 Tiny Cloud CLI v3.5[/bold green]\nDigita [bold cyan]/help[/bold cyan] para ver os comandos.", border_style="green"))
    
    if os.getcwd() not in DIRETORIOS_CONFIAVEIS:
        pedir_permissao(os.getcwd())

    try:
        with open(os.path.expanduser("~/.tinycli_skill.md"), "r", encoding="utf-8") as f:
            skill_content = f.read()
    except:
        skill_content = "Você é o Tiny CLI, um agente de programação."

    mensagens = [{"role": "system", "content": skill_content}]
    
    while True:
        try:
            prompt = console.input("[bold blue]👤 Tu:[/bold blue] ")
            
            cmd = prompt.lower().strip()
            if cmd in ["/help", "help"]:
                mostrar_help()
                continue
            elif cmd == "/models":
                mostrar_models()
                continue
            elif cmd == "/usage":
                mostrar_usage()
                continue
            elif cmd == "/clear":
                os.system('clear' if os.name == 'posix' else 'cls')
                continue
            elif cmd in ["sair", "exit"]:
                break
            elif not prompt.strip():
                continue
            
            mensagens.append({"role": "user", "content": prompt})
            console.print("[dim]⏳ Enviando para a nuvem...[/dim]")
            
            while True:
                resposta = chamar_ia(mensagens)
                mensagens.append({"role": "assistant", "content": resposta})
                
                resultado = executar_ferramenta(resposta)
                if resultado:
                    mensagens.append({"role": "user", "content": f"Resultado da ferramenta:\n{resultado}"})
                    console.print("[dim]⏳ Processando resultado...[/dim]")
                    continue
                
                console.print(Panel(Markdown(resposta), title="🤖 Tiny Cloud", border_style="green"))
                break
                
        except KeyboardInterrupt:
            break

if __name__ == "__main__":
    main()