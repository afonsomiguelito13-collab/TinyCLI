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

MODELOS_DISPONIVEIS = [
    "deepseek-v4.1-flash", 
    "deepseek-v4-flash",
    "glm-5.3",
    "glm-5.3-flash",
    "gemini-3.8-flash",
    "jev-1.13"
]

# --- SISTEMA DE USAGE ---
def carregar_usage():
    os.makedirs(os.path.dirname(USAGE_FILE), exist_ok=True)
    if os.path.exists(USAGE_FILE):
        try:
            with open(USAGE_FILE, "r") as f:
                return json.load(f)
        except:
            pass
    return {"requests": 0, "prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0, "modelo_atual": MODELOS_DISPONIVEIS[0]}

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
    api_url = f"{SERVER_URL}/api/chat"
    
    # Envia o modelo atual (mesmo que o servidor force, é boa prática)
    data = {"messages": mensagens, "model": USAGE_DATA["modelo_atual"]}
    
    try:
        req = urllib.request.Request(api_url, data=json.dumps(data).encode("utf-8"), headers={"Content-Type": "application/json"}, method="POST")
        with urllib.request.urlopen(req) as response:
            resultado = json.loads(response.read().decode("utf-8"))
            
            # Atualiza os contadores de usage
            usage_api = resultado.get("usage", {})
            USAGE_DATA["requests"] += 1
            USAGE_DATA["prompt_tokens"] += usage_api.get("prompt_tokens", 0)
            USAGE_DATA["completion_tokens"] += usage_api.get("completion_tokens", 0)
            USAGE_DATA["total_tokens"] += usage_api.get("total_tokens", 0)
            salvar_usage(USAGE_DATA)
            
            return resultado["content"]
    except urllib.error.HTTPError as e:
        return f"ERRO NO SERVIDOR ({e.code}): {e.reason}"
    except Exception as e:
        return f"ERRO DE CONEXÃO: O servidor tá offline?"

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
    table.add_row("/models", "Troca o modelo de IA (UI interativa)")
    table.add_row("/usage", "Mostra os teus tokens, pedidos e o modelo atual")
    table.add_row("/clear", "Limpa o terminal")
    table.add_row("sair", "Fecha o Tiny CLI")
    
    console.print(table)
    console.print("\n[dim]* As permissões de diretório são guardadas em ~/.tinycli_trust[/dim]")
    console.print("[dim]* O usage é guardado em ~/.local/share/.tinycli_usage.json[/dim]\n")

def mostrar_usage():
    console.print(Panel(
        f"[bold green]Modelo Atual:[/bold green] {USAGE_DATA['modelo_atual']}\n"
        f"[bold yellow]Requests Feitos:[/bold yellow] {USAGE_DATA['requests']}\n"
        f"[bold cyan]Tokens de Prompt:[/bold cyan] {USAGE_DATA['prompt_tokens']}\n"
        f"[bold cyan]Tokens de Resposta:[/bold cyan] {USAGE_DATA['completion_tokens']}\n"
        f"[bold magenta]Total de Tokens:[/bold magenta] {USAGE_DATA['total_tokens']}\n\n"
        f"[dim]Servidor: {SERVER_URL}[/dim]",
        title="📊 Estatísticas do Tiny Cloud", border_style="blue"
    ))

def trocar_modelo():
    escolha = questionary.select(
        "Escolha o modelo (Use as setas ↑/↓ e Enter):",
        choices=MODELOS_DISPONIVEIS,
        style=custom_style,
        default=USAGE_DATA["modelo_atual"]
    ).ask()
    if escolha:
        USAGE_DATA["modelo_atual"] = escolha
        salvar_usage(USAGE_DATA)
        console.print(f"[green]✅ Modelo alterado para: {escolha}[/green]\n")

# --- LOOP PRINCIPAL ---
def main():
    console.print(Panel("[bold green]🦁 Tiny Cloud CLI v3.1[/bold green]\nDigita [bold cyan]/help[/bold cyan] para ver os comandos.", border_style="green"))
    
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
                trocar_modelo()
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