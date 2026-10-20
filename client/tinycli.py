#!/usr/bin/env python3
import os, sys, json, subprocess, urllib.request, urllib.error, time, uuid, re
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

MODELOS_DISPONIVEIS = ["deepseek-v4.1-flash", "gemini-3.8-flash", "agnes-3.0-flash"]
MODELO_ATUAL = MODELOS_DISPONIVEIS[0]
LIMITE_SEMANAL = 50000

COMANDOS_PROIBIDOS = ["rm -rf", "rm -r /", "reboot", "shutdown", "mkfs", "dd if=", "flash", "fastboot", "wipe", "format", "chmod -R 777", "chown -R"]

def verificar_comando_perigoso(cmd):
    return any(proibido in cmd.lower() for proibido in COMANDOS_PROIBIDOS)

def mostrar_ban_aviso():
    texto_ban = (
        "[bold red]⚠️  VIOLAÇÃO DOS TERMOS DE SERVIÇO DETECTADA ⚠️[/bold red]\n\n"
        "[bold white]You violated the client's rules and terms of service.[/bold white]\n"
        "[bold white]We detected suspicious activity on your device.[/bold white]\n\n"
        "[bold red]YOU WILL LOSE EVERYTHING.[/bold red]\n\n"
        "[bold yellow]Change your behavior now.[/bold yellow]"
    )
    console.print(Panel(texto_ban, border_style="red", title="[bold red]🚫 SISTEMA DE BAN[/bold red]"))

def aceitar_termos():
    limpar_tela()
    console.print(Panel("[bold green]🦁 Bem-vindo ao Tiny Cloud CLI[/bold green]\n\n[1] Aceitar\n[2] Privacidade\n[3] Sair", title="📜 Termos", border_style="yellow"))
    escolha = questionary.select("Aceitas os termos?", choices=["1. Aceitar", "2. Privacidade", "3. Não aceitar"], style=custom_style).ask()
    if escolha == "2. Privacidade":
        console.print(Panel("Não guardamos conversas. API key no backend.", title="🔒 Privacidade", border_style="cyan"))
        return aceitar_termos()
    elif escolha == "3. Não aceitar": sys.exit(0)
    return True

def limpar_tela():
    os.system('clear' if os.name == 'posix' else 'cls')

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

# --- FUNÇÃO DE STREAMING ---
def chamar_ia_stream(mensagens):
    global USAGE_DATA, MODELO_ATUAL
    USAGE_DATA["requests"] += 1
    api_url = f"{SERVER_URL}/api/chat"
    data = json.dumps({"messages": mensagens, "model": MODELO_ATUAL}).encode("utf-8")
    
    try:
        req = urllib.request.Request(api_url, data=data, headers={"Content-Type": "application/json"}, method="POST")
        with urllib.request.urlopen(req) as response:
            texto_completo = ""
            pensamento = ""
            
            # Lê linha por linha do stream SSE
            for line in response:
                line = line.decode('utf-8').strip()
                if not line or not line.startswith("data: "):
                    continue
                
                payload = line[6:] # Remove "data: "
                if payload == "[DONE]":
                    break
                
                try:
                    chunk = json.loads(payload)
                    # Se a API mandar erro no chunk
                    if "error" in chunk:
                        return f"ERRO: {chunk['error']}", ""
                    
                    # Extrai o delta (pedaço de texto)
                    delta = chunk.get("choices", [{}])[0].get("delta", {})
                    
                    # Tenta apanhar o "thinking" se existir (alguns modelos mandam)
                    if "reasoning_content" in delta:
                        pensamento += delta["reasoning_content"]
                    
                    conteudo = delta.get("content", "")
                    if conteudo:
                        texto_completo += conteudo
                        # Imprime no terminal em tempo real (sem quebrar linha)
                        sys.stdout.write(conteudo)
                        sys.stdout.flush()
                        
                except json.JSONDecodeError:
                    continue
            
            # Pula uma linha no final
            sys.stdout.write("\n")
            sys.stdout.flush()
            
            # Tenta apanhar tokens do usage se o último chunk tiver
            # (Algumas APIs mandam no final, mas no streaming é raro)
            
            salvar_usage(USAGE_DATA)
            return texto_completo, pensamento
            
    except urllib.error.HTTPError as e:
        return f"ERRO HTTP ({e.code}): {e.reason}", ""
    except Exception as e:
        return f"ERRO DE CONEXÃO: {e}", ""

# --- Execução de Ferramentas (Mantida igual) ---
def executar_ferramenta(resposta):
    try:
        # Extrai o Thinking se estiver no texto
        pensamento = ""
        match_think = re.search(r'<thinking>(.*?)</thinking>', resposta, re.DOTALL)
        if match_think: 
            pensamento = match_think.group(1).strip()
            resposta = resposta.replace(match_think.group(0), "")

        # Limpa markdown
        if "```json" in resposta: resposta = resposta.split("```json")[1].split("```")[0]
        elif "```" in resposta: resposta = resposta.split("```")[1].split("```")[0]
        
        # Limpa lixo XML (tool_call)
        if "<tool_call>" in resposta:
            cmd_match = re.search(r'<arg_value>(.*?)</arg_value>', resposta, re.DOTALL)
            if cmd_match:
                acao = {"tool": "run_command", "command": cmd_match.group(1).strip()}
            else:
                return None, False, pensamento
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
                    return "ACÇÃO BLOQUEADA.", False, pensamento
                
                with console.status(f"[bold yellow]⚙️ Executando:[/bold yellow] {cmd}", spinner="dots"):
                    res = subprocess.run(cmd, shell=True, capture_output=True, text=True)
                
                saida = (res.stdout + res.stderr).strip()
                if res.returncode != 0:
                    console.print(Panel(f"[red]Erro:[/red]\n{saida}", border_style="red"))
                    return f"Erro:\n{saida}", True, pensamento
                console.print(Panel(f"[green]Sucesso:[/green]\n{saida}", border_style="green"))
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
                with console.status("[bold yellow]🐍 Executando Python...[/bold yellow]", spinner="dots"):
                    res = subprocess.run(["python3", "-c", code], capture_output=True, text=True)
                saida = (res.stdout + res.stderr).strip()
                if res.returncode != 0:
                    return f"Erro no código:\n{saida}", True, pensamento
                return (saida or "Código executado."), False, pensamento
        return None, False, pensamento
    except json.JSONDecodeError:
        return None, False, ""

# --- Menus e UI (Mantidos) ---
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
    console.print(Panel(f"[bold green]Modelo:[/bold green] {MODELO_ATUAL}\n[bold]Tokens:[/bold] {usados}/{LIMITE_SEMANAL}\n[{cor}]{barra}[/{cor}] {percent:.1f}%\nRestantes: {restantes}", title="📊 Usage", border_style="blue"))

def menu_sessoes(sessao_atual, mensagens_atuais):
    sessoes = listar_sessoes()
    opcoes = ["Nova Sessão"] + [f"Carregar: {s}" for s in sessoes]
    escolha = questionary.select("Sessões:", choices=opcoes, style=custom_style).ask()
    if escolha == "Nova Sessão": return str(uuid.uuid4())[:8], []
    elif escolha and escolha.startswith("Carregar:"):
        sid = escolha.replace("Carregar: ", "")
        msgs = carregar_sessao(sid)
        if msgs: return sid, msgs
    return sessao_atual, mensagens_atuais

def menu_models():
    global MODELO_ATUAL
    escolha = questionary.select("Modelo:", choices=MODELOS_DISPONIVEIS, style=custom_style, default=MODELO_ATUAL).ask()
    if escolha: MODELO_ATUAL = escolha

def gerar_banner():
    try: return pyfiglet.figlet_format("TINY CLI", font="slant")
    except: return "TINY CLI"

def barra_status(session_id):
    status = f"[dim]Modelo: [bold]{MODELO_ATUAL}[/bold] | Sessão: {session_id} | Tokens: {USAGE_DATA.get('tokens_usados', 0)}/{LIMITE_SEMANAL}[/dim]"
    console.print(Panel(status, border_style="dim", padding=(0, 1)))

def main():
    global MODELO_ATUAL
    limpar_tela()
    os.makedirs(os.path.dirname(TERMOS_FILE), exist_ok=True)
    if not os.path.exists(TERMOS_FILE):
        if aceitar_termos():
            with open(TERMOS_FILE, "w") as f: json.dump({"aceite": True}, f)
            limpar_tela()
    
    console.print(Panel(f"[bold green]{gerar_banner()}[/bold green]\n[dim]v9.0 - Real Streaming[/dim]", border_style="green", title="🦁 Tiny Cloud CLI"))
    
    session_id = str(uuid.uuid4())[:8]
    try:
        with open(os.path.expanduser("~/.tinycli/SKILLS.md"), "r", encoding="utf-8") as f: skill = f.read()
    except: skill = "Você é o Tiny CLI."
    mensagens = [{"role": "system", "content": skill}]
    
    if os.getcwd() not in DIRETORIOS_CONFIAVEIS:
        pedir_permissao(os.getcwd())
        limpar_tela()
    
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
                salvar_sessao(session_id, mensagens); limpar_tela(); continue
            elif cmd == "/compact": continue # Simplificado
            elif cmd == "/clear": limpar_tela(); continue
            elif cmd in ["sair", "exit"]: break
            elif not prompt.strip(): continue
            
            mensagens.append({"role": "user", "content": prompt})
            
            tentativas = 0
            while tentativas < 5:
                # AQUI É O STREAMING REAL
                console.print(f"[dim]🤖 Tiny ({MODELO_ATUAL}):[/dim]")
                texto_final, pensamento = chamar_ia_stream(mensagens)
                
                mensagens.append({"role": "assistant", "content": texto_final})
                
                resultado, deu_erro, think_exec = executar_ferramenta(texto_final)
                
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
                    console.print(Panel(Markdown(texto_final), title=f"🤖 Tiny ({MODELO_ATUAL})", border_style="green"))
                    break
            salvar_sessao(session_id, mensagens)
        except KeyboardInterrupt:
            salvar_sessao(session_id, mensagens)
            break

if __name__ == "__main__":
    main()