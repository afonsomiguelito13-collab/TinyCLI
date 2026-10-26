#!/usr/bin/env python3
import os, sys, json, subprocess, time, uuid, re, locale
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

VERSAO_LOCAL = "21.0.0"
GITHUB_CLIENT_ID = "Ov23lia18KwHbwNmBmBv"

INSTALL_URL = "https://raw.githubusercontent.com/afonsomiguelito13-collab/TinyCLI/main/public/install.sh"
SERVER_URL = os.environ.get("TINY_SERVER_URL", "https://tinycli.onrender.com")
TRUST_FILE = os.path.expanduser("~/.tinycli_trust")
USAGE_FILE = os.path.expanduser("~/.local/share/.tinycli_usage.json")
SESSIONS_DIR = os.path.expanduser("~/.local/share/.tinycli_sessions")
TERMOS_FILE = os.path.expanduser("~/.local/share/.tinycli_terms.json")
CONFIG_FILE = os.path.expanduser("~/.local/share/.tinycli_config.json")
GITHUB_TOKEN_FILE = os.path.expanduser("~/.tinycli_github_token")
GITHUB_USER_FILE = os.path.expanduser("~/.tinycli_github_user")
PLANO_FILE = os.path.expanduser("~/.tinycli_plano")

MODELOS_DISPONIVEIS = [
    "deepseek-v4.1", 
    "agnes-3.0-flash", 
    "gpt-6-luna",
    "gemini-3.8-flash",
    "claude-opus-4.8"
]
MODELO_ATUAL = MODELOS_DISPONIVEIS[0]
LIMITE_SEMANAL = 5000000

CUSTO_MODELO = {
    "deepseek-v4.1": 3, 
    "agnes-3.0-flash": 3, 
    "gpt-6-luna": 8,
    "gemini-3.8-flash": 4,
    "claude-opus-4.8": 20
}

# --- SISTEMA DE IDIOMAS (i18n) ---
IDIOMAS_DISPONIVEIS = {
    "pt_PT": "🇵🇹 Português (Portugal)",
    "pt_BR": "🇧🇷 Português (Brasil)",
    "en": "🇬🇧 English",
    "zh": "🇨🇳 中文 (Chinês)",
    "ja": "🇯🇵 日本語 (Japonês)",
    "ru": "🇷🇺 Русский (Russo)"
}

TRADUCOES = {
    "pt_PT": {
        "bem_vindo": "Bem-vindo ao Tiny Cloud CLI",
        "termos": "📜 Termos de Serviço e Privacidade",
        "ler_mais": "Ler o texto completo",
        "aceitar": "Aceitar e continuar",
        "sair": "Sair",
        "pasta": "📁 Onde queres trabalhar hoje?",
        "pasta_atual": "Usar a pasta atual",
        "home": "Usar a Home (~)",
        "prompt": "👤 Tu:",
        "pensando": "⏳ Pensando...",
        "aprovacao": "⚠️ APROVAÇÃO NECESSÁRIA",
        "aprovas": "Aprovas?",
        "sim": "Sim, executar",
        "nao": "Não, bloquear",
        "usage": "📊 Usage (5M)",
        "fila": "⚠️ Servidor cheio! Há {n} pessoas na fila.",
        "modelo": "Modelo",
        "tokens": "Tokens Usados",
        "restantes": "Restantes",
        "texto_termos": "1. Aceitação: Ao usar o CLI, concordas com estes termos.\n2. Privacidade: O histórico é local. As chaves ficam no servidor.\n3. Uso: És responsável pelo código gerado. Comandos perigosos serão bloqueados.\n4. Fila: O servidor tem limites. Abusos resultam em banimento."
    },
    # ... (Podes manter as outras traduções do teu ficheiro antigo) ...
}

def obter_idioma_sistema():
    try:
        lang, _ = locale.getdefaultlocale()
        if lang:
            if lang.startswith("pt_BR"): return "pt_BR"
            if lang.startswith("pt"): return "pt_PT"
            if lang.startswith("zh"): return "zh"
            if lang.startswith("ja"): return "ja"
            if lang.startswith("ru"): return "ru"
            if lang.startswith("en"): return "en"
    except: pass
    return "pt_PT"

IDIOMA_ATUAL = obter_idioma_sistema()

def t(chave, **kwargs):
    texto = TRADUCOES.get(IDIOMA_ATUAL, TRADUCOES["pt_PT"]).get(chave, chave)
    return texto.format(**kwargs) if kwargs else texto

# --- CLIENTE HTTP ---
http_session = requests.Session()
retry_strategy = Retry(total=3, backoff_factor=1, status_forcelist=[429, 500, 502, 503, 504], allowed_methods=["POST", "GET"])
adapter = HTTPAdapter(max_retries=retry_strategy, pool_connections=10, pool_maxsize=10)
http_session.mount("https://", adapter)
http_session.mount("http://", adapter)

def limpar_tela():
    os.system('clear' if os.name == 'posix' else 'cls')

# --- LOGIN GITHUB E PLANO ---
def verificar_login():
    return os.path.exists(GITHUB_TOKEN_FILE)

def obter_plano(username):
    try:
        res = http_session.post(f"{SERVER_URL}/api/check-plan", json={"username": username}, timeout=10)
        if res.status_code == 200:
            plano = res.json().get("plan", "Free")
            with open(PLANO_FILE, "w") as f: f.write(plano)
            return plano
    except: pass
    return "Free"

def fazer_login_github():
    console.print(Panel("[bold cyan]🔐 Login com GitHub[/bold cyan]\nA ligar ao GitHub para autenticação...", border_style="cyan"))
    try:
        res = http_session.post(
            "https://github.com/login/device/code",
            data={"client_id": GITHUB_CLIENT_ID, "scope": "read:user"},
            headers={"Accept": "application/json"}, timeout=10
        )
        res.raise_for_status()
        dados = res.json()
        
        user_code = dados["user_code"]
        device_code = dados["device_code"]
        verification_uri = dados["verification_uri"]
        interval = dados.get("interval", 5)
        
        console.print(Panel(
            f"[bold white]Código:[/bold white] [bold green]{user_code}[/bold green]\n\n"
            f"[bold white]Link:[/bold white] {verification_uri}\n\n"
            f"[dim]A abrir o navegador...[/dim]",
            title="📱 Ação Necessária", border_style="yellow"
        ))
        
        subprocess.run(f"termux-open-url {verification_uri}", shell=True, capture_output=True)
        
        with console.status("[bold cyan]⏳ À espera que autorizes no GitHub...[/bold cyan]", spinner="dots"):
            while True:
                time.sleep(interval)
                token_res = http_session.post(
                    "https://github.com/login/oauth/access_token",
                    data={"client_id": GITHUB_CLIENT_ID, "device_code": device_code, "grant_type": "urn:ietf:params:oauth:grant-type:device_code"},
                    headers={"Accept": "application/json"}, timeout=10
                )
                token_dados = token_res.json()
                
                if "access_token" in token_dados:
                    token = token_dados["access_token"]
                    with open(GITHUB_TOKEN_FILE, "w") as f: f.write(token)
                    
                    # Obtém o username e o plano
                    try:
                        user_res = http_session.post(f"{SERVER_URL}/api/github-user", json={"token": token}, timeout=10)
                        if user_res.status_code == 200:
                            username = user_res.json().get("username", "Developer")
                            with open(GITHUB_USER_FILE, "w") as f: f.write(username)
                            
                            plano = obter_plano(username)
                            if plano == "Go":
                                console.print(f"[bold green]👑 Bem-vindo, {username}! O teu plano é GO (Opus 4.8 desbloqueado).[/bold green]")
                            else:
                                console.print(f"[bold green]✅ Login efetuado! Bem-vindo, {username} (Plano Free).[/bold green]")
                    except:
                        console.print("[bold green]✅ Login efetuado![/bold green]")
                    return True
                elif token_dados.get("error") == "authorization_pending": continue
                elif token_dados.get("error") == "slow_down": interval += 5; continue
                elif token_dados.get("error") == "expired_token": return False
                else: return False
    except Exception as e:
        console.print(f"[red]❌ Erro no login: {e}[/red]")
        return False

def obter_username_local():
    if os.path.exists(GITHUB_USER_FILE):
        with open(GITHUB_USER_FILE, "r") as f: return f.read().strip()
    return "Developer"

def obter_plano_local():
    if os.path.exists(PLANO_FILE):
        with open(PLANO_FILE, "r") as f: return f.read().strip()
    return "Free"

# --- RESTO DO CÓDIGO (FUNCIONAL) ---
def verificar_atualizacao():
    try:
        res = http_session.get(f"{SERVER_URL}/api/version", timeout=(3, 10))
        if res.status_code == 200:
            versao_servidor = res.json().get("version", VERSAO_LOCAL)
            if versao_servidor != VERSAO_LOCAL:
                if questionary.confirm(f"Nova versão {versao_servidor} disponível. Atualizar?").ask():
                    subprocess.run(f"curl -sL {INSTALL_URL} | bash", shell=True)
                    sys.exit(0)
    except: pass

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
    console.print(Panel(f"[bold cyan]{t('pasta')}[/bold cyan]", border_style="cyan"))
    opcoes = [f"{t('pasta_atual')}: {pasta_padrao}", t('home')]
    escolha = questionary.select("Seleciona:", choices=opcoes, style=custom_style).ask()
    if escolha == t('home'): pasta_final = os.path.expanduser("~")
    else: pasta_final = pasta_padrao
    os.chdir(pasta_final)
    salvar_config(pasta_final)
    time.sleep(1)

def pedir_aprovacao_comando(cmd):
    console.print(Panel(f"[bold yellow]{t('aprovacao')}:[/bold yellow]\n\n[bold white]{cmd}[/bold white]", border_style="yellow", title="⚠️"))
    return questionary.select(t('aprovas'), choices=[t('sim'), t('nao')], style=custom_style).ask() == t('sim')

def verificar_comando_perigoso(cmd):
    return any(p in cmd.lower() for p in ["rm -rf", "reboot", "mkfs", "dd if=", "flash"])

def mostrar_ban_aviso():
    console.print(Panel("[bold red]⚠️ VIOLAÇÃO DOS TERMOS DE SERVIÇO DETECTADA ⚠️[/bold red]\n\n[bold white]You will lose everything.[/bold white]", border_style="red", title="🚫 BAN"))

def aceitar_termos():
    limpar_tela()
    texto_curto = t("texto_termos")[:500] + "\n\n[dim]...[/dim]"
    console.print(Panel(texto_curto, title=t("termos"), border_style="yellow"))
    escolha = questionary.select("Opções:", choices=[t("ler_mais"), t("aceitar"), t("sair")], style=custom_style).ask()
    if escolha == t("ler_mais"):
        limpar_tela()
        console.print(Panel(t("texto_termos"), title=t("termos"), border_style="yellow"))
        return aceitar_termos()
    elif escolha == t("sair"): sys.exit(0)
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
    with open(os.path.join(SESSIONS_DIR, f"{session_id}.json"), "w") as f: json.dump(mensagens, f)

def carregar_usage():
    os.makedirs(os.path.dirname(USAGE_FILE), exist_ok=True)
    if os.path.exists(USAGE_FILE):
        try:
            with open(USAGE_FILE, "r") as f:
                data = json.load(f)
                data.setdefault("requests", 0); data.setdefault("tokens_usados", 0)
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
    data = {"messages": mensagens, "model": MODELO_ATUAL}
    
    # Acordar o Render
    for tentativa in range(5):
        try:
            res = http_session.get(health_url, timeout=(5, 10))
            if res.status_code == 200: break
        except: pass
        with console.status(f"[yellow]{t('pensando')} (Tentativa {tentativa+1}/5)[/yellow]", spinner="bouncingBall"):
            time.sleep(2)
            
    try:
        try:
            status_res = http_session.get(f"{SERVER_URL}/api/status", timeout=3)
            if status_res.status_code == 200:
                status = status_res.json()
                if status.get("na_fila", 0) > 0:
                    console.print(f"[yellow]{t('fila', n=status['na_fila'])}[/yellow]")
        except: pass

        response = http_session.post(api_url, json=data, timeout=(10, 120))
        if response.status_code == 429: return "ERRO 429: LIMITE RÍGIDO ATINGIDO ou CASTIGO ATIVO. Faz upgrade para o Go."
        response.raise_for_status()
        dados = response.json()
        
        tokens_reais = dados.get("usage", {}).get("total_tokens", 0)
        multiplicador = CUSTO_MODELO.get(MODELO_ATUAL, 1)
        USAGE_DATA["tokens_usados"] += (tokens_reais * multiplicador)
        salvar_usage(USAGE_DATA)
        
        return dados["choices"][0]["message"]["content"]
        
    except requests.exceptions.Timeout:
        return "ERRO DE TIMEOUT."
    except Exception as e:
        return f"ERRO: {e}"

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
                console.print(Panel(f"[italic dim]{pensamento}[/italic dim]", title="🧠", border_style="magenta"))

            if ferramenta == "run_command":
                cmd = acao.get("command")
                if verificar_comando_perigoso(cmd):
                    mostrar_ban_aviso()
                    return "ACÇÃO BLOQUEADA.", False, pensamento
                if not pedir_aprovacao_comando(cmd):
                    return "O utilizador NEGOU.", False, pensamento
                with console.status(f"[bold yellow]⚙️ Executando:[/bold yellow] {cmd}", spinner="dots"):
                    res = subprocess.run(cmd, shell=True, capture_output=True, text=True)
                saida = (res.stdout + res.stderr).strip()
                return (saida or "Comando executado."), (res.returncode != 0), pensamento
                
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
                console.print(Panel(f"[bold yellow]🐍 Executando Python:[/bold yellow]\n{code}", border_style="yellow"))
                if not questionary.confirm("Aprovas?").ask():
                    return "O utilizador NEGOU.", False, pensamento
                with console.status("[bold yellow]🐍 Executando...[/bold yellow]", spinner="dots"):
                    res = subprocess.run(["python3", "-c", code], capture_output=True, text=True)
                saida = (res.stdout + res.stderr).strip()
                return (saida or "Código executado."), (res.returncode != 0), pensamento
        return None, False, pensamento
    except json.JSONDecodeError:
        return None, False, ""

def menu_lang():
    global IDIOMA_ATUAL
    escolha = questionary.select("Selecione o Idioma / Select Language:", choices=list(IDIOMAS_DISPONIVEIS.values()), style=custom_style).ask()
    for codigo, nome in IDIOMAS_DISPONIVEIS.items():
        if nome == escolha:
            IDIOMA_ATUAL = codigo; break
    console.print(f"[green]✅ Idioma alterado para {IDIOMAS_DISPONIVEIS[IDIOMA_ATUAL]}[/green]")

def mostrar_help():
    table = Table(title="🦁 Tiny CLI - Comandos", show_header=True, header_style="bold green")
    table.add_column("Comando", style="cyan", width=15)
    table.add_column("Descrição", style="white")
    table.add_row("/help", "Mostra este menu")
    table.add_row("/models", "Troca o modelo de IA")
    table.add_row("/usage", "Mostra a cota")
    table.add_row("/session", "Gerencia sessões")
    table.add_row("/lang", "Muda o idioma")
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
        f"[bold green]{t('modelo')}:[/bold green] {MODELO_ATUAL}\n"
        f"[bold]{t('tokens')}:[/bold] {usados} / {LIMITE_SEMANAL}\n"
        f"[{cor}]{barra}[/{cor}] {percent:.2f}%\n"
        f"[bold yellow]{t('restantes')}:[/bold yellow] {restantes}", 
        title=t("usage"), border_style="blue"
    ))

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
    if escolha:
        MODELO_ATUAL = escolha
        multiplicador = CUSTO_MODELO.get(MODELO_ATUAL, 1)
        if multiplicador >= 20:
            console.print(Panel(f"[yellow]⚠️ AVISO: O {MODELO_ATUAL} consome {multiplicador}x mais cota! É o modelo mais caro.[/yellow]", border_style="yellow"))
        elif multiplicador >= 6:
            console.print(Panel(f"[yellow]⚠️ AVISO: O {MODELO_ATUAL} consome {multiplicador}x mais cota![/yellow]", border_style="yellow"))
        else:
            console.print(f"[green]✅ Modelo: {MODELO_ATUAL} (Custo: {multiplicador}x)[/green]")

def gerar_banner(username, plano):
    try:
        banner = pyfiglet.figlet_format("TINY CLI", font="slant")
    except:
        banner = "TINY CLI"
    
    plano_texto = "👑 PLANO GO" if plano == "Go" else "🆓 PLANO FREE"
    return Panel(
        f"[bold green]{banner}[/bold green]\n[dim]v{VERSAO_LOCAL} | {username} | {plano_texto}[/dim]", 
        border_style="green", title="🦁 Tiny Cloud CLI"
    )

def barra_status(session_id, username, plano):
    status = f"[dim]User: [bold]{username}[/bold] ({plano}) | Modelo: [bold]{MODELO_ATUAL}[/bold] | Sessão: {session_id} | Tokens: {USAGE_DATA.get('tokens_usados', 0)}/{LIMITE_SEMANAL}[/dim]"
    console.print(Panel(status, border_style="dim", padding=(0, 1)))

def main():
    global MODELO_ATUAL
    limpar_tela()
    
    # --- LOGIN ---
    if not verificar_login():
        if not fazer_login_github():
            console.print("[red]A encerrar...[/red]")
            sys.exit(1)
        limpar_tela()
    
    username = obter_username_local()
    plano = obter_plano_local()
    
    verificar_atualizacao()
    os.makedirs(os.path.dirname(TERMOS_FILE), exist_ok=True)
    if not os.path.exists(TERMOS_FILE):
        if aceitar_termos():
            with open(TERMOS_FILE, "w") as f: json.dump({"aceite": True}, f)
            limpar_tela()
    
    escolher_pasta_inicial()
    console.print(gerar_banner(username, plano))
    
    session_id = str(uuid.uuid4())[:8]
    try:
        with open(os.path.expanduser("~/.tinycli/SKILLS.md"), "r", encoding="utf-8") as f: skill = f.read()
    except: skill = "Você é o Tiny CLI."
    mensagens = [{"role": "system", "content": skill}]
    
    while True:
        try:
            barra_status(session_id, username, plano)
            prompt = questionary.text(t("prompt"), style=custom_style, qmark="").ask()
            if prompt is None: continue
            cmd = prompt.lower().strip()
            
            if cmd in ["/help", "help"]: mostrar_help(); continue
            elif cmd == "/usage": mostrar_usage(); continue
            elif cmd == "/models": menu_models(); continue
            elif cmd == "/lang": menu_lang(); continue
            elif cmd == "/session":
                session_id, mensagens = menu_sessoes(session_id, mensagens)
                salvar_sessao(session_id, mensagens); limpar_tela(); continue
            elif cmd == "/clear": limpar_tela(); continue
            elif cmd in ["sair", "exit", "quit", "退出", "終了", "выход", "blyat"]: break
            elif not prompt.strip(): continue
            
            if USAGE_DATA.get("requests", 0) % 5 == 0 and USAGE_DATA.get("requests", 0) > 0:
                console.print(Panel("[bold cyan]💡 Tiny CLI Go: Usa o Opus 4.8 sem multiplicador e sem filas![/bold cyan]", border_style="cyan", title="🚀 Upgrade"))

            mensagens.append({"role": "user", "content": prompt})
            
            tentativas = 0
            while tentativas < 5:
                with console.status(t("pensando"), spinner="bouncingBar"):
                    resposta = chamar_ia(mensagens)
                mensagens.append({"role": "assistant", "content": resposta})
                
                resultado, deu_erro, pensamento = executar_ferramenta(resposta)
                
                if resultado:
                    if deu_erro:
                        mensagens.append({"role": "user", "content": f"Erro:\n{resultado}\nCorrige."})
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