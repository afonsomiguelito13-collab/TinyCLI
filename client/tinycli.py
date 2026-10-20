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

# Importações do Prompt Toolkit para a UI de baixo
from prompt_toolkit import PromptSession
from prompt_toolkit.styles import Style as PtStyle
from prompt_toolkit.formatted_text import HTML

console = Console()
custom_style = Style([
    ('qmark', 'fg:#00ff00 bold'), ('question', 'fg:#00bfff bold'),
    ('answer', 'fg:#00ff00 bold'), ('pointer', 'fg:#ffaa00 bold'),
    ('highlighted', 'fg:#00ff00 bold'), ('selected', 'fg:#00ff00')
])

# Estilo do Prompt Toolkit (Cinza e Branco)
pt_style = PtStyle.from_dict({
    'prompt': 'bg:#333333 #ffffff bold',
    'bottom-toolbar': 'bg:#000000 #ffffff',
})

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
TEMA_ATUAL = "dark"

COMANDOS_PROIBIDOS = [
    "rm -rf", "rm -r /", "reboot", "shutdown", "mkfs", "dd if=",
    "flash", "fastboot", "wipe", "format", "chmod -R 777", "chown -R"
]

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

def executar_ferramenta(resposta):
    try:
        if "```json" in resposta: resposta = resposta.split("```json")[1].split("```")[0]
        elif "```" in resposta: resposta = resposta.split("```")[1].split("```")[0]

        acao = json.loads(resposta.strip())
        ferramenta = acao.get("tool")
        
        if ferramenta in ["run_command", "create_file", "run_code", "list_directory", "read_file", "web_search"]:
            alvo = os.getcwd()
            if ferramenta in ["create_file", "read_file"]:
                alvo = os.path.dirname(os.path.abspath(acao.get("path", ""))) or os.getcwd()
            
            if not pedir_permissao(alvo): return "Cancelado.", False
            limpar_tela()
            
            if ferramenta == "run_command":
                cmd = acao.get("command")
                if verificar_comando_perigoso(cmd):
                    mostrar_ban_aviso()
                    return "ACÇÃO BLOQUEADA: VIOLAÇÃO DOS TERMOS DE SERVIÇO.", False
                console.print(Panel(f"[bold yellow]⚙️ Executando:[/bold yellow] {cmd}", border_style="yellow"))
                res = subprocess.run(cmd, shell=True, capture_output=True, text=True)
                saida = (res.stdout + res.stderr).strip()
                if res.returncode != 0:
                    return f"Erro no comando:\n{saida}", True
                return (saida or "Comando executado."), False
                
            elif ferramenta == "create_file":
                path, content = acao.get("path"), acao.get("content")
                console.print(Panel(f"[bold cyan]📝 Criando arquivo:[/bold cyan] {path}", border_style="cyan"))
                with open(path, "w", encoding="utf-8") as f: f.write(content)
                return f"Arquivo {path} criado.", False

            elif ferramenta == "run_code":
                code = acao.get("code")
                console.print(Panel("[bold yellow]🐍 Executando Python[/bold yellow]", border_style="yellow"))
                res = subprocess.run(["python3", "-c", code], capture_output=True, text=True)
                saida = (res.stdout + res.stderr).strip()
                if res.returncode != 0:
                    return f"Erro no código Python:\n{saida}", True
                return (saida or "Código executado."), False
                
            elif ferramenta == "list_directory":
                path = acao.get("path", ".")
                console.print(Panel(f"[bold cyan]📁 Listando:[/bold cyan] {path}", border_style="cyan"))
                try:
                    itens = os.listdir(path)
                    return f"Arquivos em {path}:\n" + "\n".join(itens), False
                except Exception as e:
                    return f"Erro ao listar: {e}", True
                    
            elif ferramenta == "read_file":
                path = acao.get("path")
                console.print(Panel(f"[bold cyan]📖 Lendo:[/bold cyan] {path}", border_style="cyan"))
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        conteudo = f.read()
                    return f"Conteúdo de {path}:\n{conteudo}", False
                except Exception as e:
                    return f"Erro ao ler: {e}", True
                    
            elif ferramenta == "web_search":
                query = acao.get("query")
                console.print(Panel(f"[bold cyan]🌐 Pesquisando:[/bold cyan] {query}", border_style="cyan"))
                try:
                    import urllib.parse
                    import re
                    url = f"https://html.duckduckgo.com/html/?q={urllib.parse.quote(query)}"
                    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
                    with urllib.request.urlopen(req, timeout=10) as r:
                        html = r.read().decode('utf-8')
                        resultados = re.findall(r'<a rel="nofollow" class="result__a" href="(.*?)">(.*?)</a>', html)[:3]
                        if resultados:
                            return "Resultados:\n" + "\n".join([f"{titulo} - {link}" for link, titulo in resultados]), False
                        return "Nenhum resultado encontrado.", False
                except Exception as e:
                    return f"Erro na pesquisa: {e}", True

        return None, False
    except json.JSONDecodeError:
        return None, False

def mostrar_help():
    table = Table(title="🦁 Tiny CLI - Comandos", show_header=True, header_style="bold green")
    table.add_column("Comando", style="cyan", width=15)
    table.add_column("Descrição", style="white")
    table.add_row("/help", "Mostra este menu")
    table.add_row("/models", "Troca o modelo de IA")
    table.add_row("/usage", "Mostra a cota")
    table.add_row("/session", "Gerencia sessões")
    table.add_row("/compact", "Resume a conversa")
    table.add_row("/theme", "Muda o tema")
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

def menu_theme():
    global TEMA_ATUAL
    escolha = questionary.select("Escolha o tema:", choices=["dark", "light"], style=custom_style, default=TEMA_ATUAL).ask()
    if escolha:
        TEMA_ATUAL = escolha
        console.print(f"[green]✅ Tema: {TEMA_ATUAL}[/green]")

def gerar_banner():
    try:
        return pyfiglet.figlet_format("TINY CLI", font="slant")
    except:
        return "TINY CLI"

def get_bottom_toolbar():
    usados = USAGE_DATA.get("tokens_usados", 0)
    return HTML(f'<style bg="black" fg="white">  Modelo: {MODELO_ATUAL}  |  Tokens: {usados}/{LIMITE_SEMANAL}  </style>')

def main():
    global MODELO_ATUAL, TEMA_ATUAL
    limpar_tela()
    
    os.makedirs(os.path.dirname(TERMOS_FILE), exist_ok=True)
    if not os.path.exists(TERMOS_FILE):
        if aceitar_termos():
            with open(TERMOS_FILE, "w") as f: json.dump({"aceite": True}, f)
            limpar_tela()
    
    banner_art = gerar_banner()
    console.print(Panel(f"[bold green]{banner_art}[/bold green]\n[dim]v7.5 - Full Agent Skills[/dim]\n\nDigita [bold cyan]/help[/bold cyan] para começar.", border_style="green", title="🦁 Tiny Cloud CLI", subtitle="Benchmarks are honest"))
    
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
        console.print(Panel(f"[bold green]{banner_art}[/bold green]\n[dim]v7.5 - Full Agent Skills[/dim]\n\nDigita [bold cyan]/help[/bold cyan] para começar.", border_style="green", title="🦁 Tiny Cloud CLI", subtitle="Benchmarks are honest"))
    
    session = PromptSession(
        style=pt_style,
        bottom_toolbar=get_bottom_toolbar
    )
    
    while True:
        try:
            prompt_texto = session.prompt(
                HTML('<style bg="#333333" fg="#ffffff">  Escreve aqui!  </style> '),
            )
            
            if prompt_texto is None: continue
                
            cmd = prompt_texto.lower().strip()
            
            if cmd in ["/help", "help"]: mostrar_help(); continue
            elif cmd == "/usage": mostrar_usage(); continue
            elif cmd == "/models": menu_models(); continue
            elif cmd == "/theme": menu_theme(); continue
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
            elif not prompt_texto.strip(): continue
            
            mensagens.append({"role": "user", "content": prompt_texto})
            
            tentativas = 0
            max_tentativas = 5
            
            while tentativas < max_tentativas:
                with console.status(f"[dim]Pensando... (Tentativa {tentativas+1})[/dim]", spinner="dots"): pass
                
                resposta = chamar_ia(mensagens)
                mensagens.append({"role": "assistant", "content": resposta})
                
                resultado, deu_erro = executar_ferramenta(resposta)
                
                if resultado:
                    if deu_erro:
                        mensagens.append({"role": "user", "content": f"A execução falhou com o seguinte erro:\n{resultado}\n\nPor favor, analisa o erro, corrige o código/comando e tenta novamente para obter uma execução estável."})
                        tentativas += 1
                        console.print("[yellow]⚠️ Erro detetado. O agente está a tentar corrigir...[/yellow]")
                        time.sleep(1)
                        limpar_tela()
                        continue
                    else:
                        mensagens.append({"role": "user", "content": f"Resultado da ferramenta:\n{resultado}"})
                        continue
                else:
                    limpar_tela()
                    console.print(Panel(Markdown(resposta), title=f"🤖 Tiny ({MODELO_ATUAL})", border_style="green"))
                    break
            
            if tentativas >= max_tentativas:
                console.print(Panel("[red]O agente atingiu o limite máximo de 5 tentativas.[/red]", border_style="red"))

            salvar_sessao(session_id, mensagens)
                
        except KeyboardInterrupt:
            salvar_sessao(session_id, mensagens)
            break

if __name__ == "__main__":
    main()