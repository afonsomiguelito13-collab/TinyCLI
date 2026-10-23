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

VERSAO_LOCAL = "15.0.0"
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
    "agnes-3.0-flash", 
    "gpt-6-luna",
    "gemini-3.8-flash"
]
MODELO_ATUAL = MODELOS_DISPONIVEIS[0]
LIMITE_SEMANAL = 5000000

CUSTO_MODELO = {
    "deepseek-v4.1": 3, 
    "deepseek-v4-flash": 3, 
    "agnes-3.0-flash": 3, 
    "gpt-6-luna": 8,
    "gemini-3.8-flash": 4
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
    "pt_BR": {
        "bem_vindo": "Bem-vindo ao Tiny Cloud CLI",
        "termos": "📜 Termos de Serviço e Privacidade",
        "ler_mais": "Ler o texto completo",
        "aceitar": "Aceitar e continuar",
        "sair": "Sair",
        "pasta": "📁 Onde você quer trabalhar hoje?",
        "pasta_atual": "Usar a pasta atual",
        "home": "Usar a Home (~)",
        "prompt": "👤 Você:",
        "pensando": "⏳ Pensando...",
        "aprovacao": "⚠️ APROVAÇÃO NECESSÁRIA",
        "aprovas": "Você aprova?",
        "sim": "Sim, executar",
        "nao": "Não, bloquear",
        "usage": "📊 Usage (5M)",
        "fila": "⚠️ Servidor cheio! Tem {n} pessoas na fila.",
        "modelo": "Modelo",
        "tokens": "Tokens Usados",
        "restantes": "Restantes",
        "texto_termos": "1. Aceitação: Ao usar o CLI, você concorda com estes termos.\n2. Privacidade: O histórico é local. As chaves ficam no servidor.\n3. Uso: Você é responsável pelo código gerado. Comandos perigosos serão bloqueados.\n4. Fila: O servidor tem limites. Abusos resultam em banimento."
    },
    "en": {
        "bem_vindo": "Welcome to Tiny Cloud CLI",
        "termos": "📜 Terms of Service & Privacy",
        "ler_mais": "Read full text",
        "aceitar": "Accept and continue",
        "sair": "Exit",
        "pasta": "📁 Where do you want to work today?",
        "pasta_atual": "Use current folder",
        "home": "Use Home (~)",
        "prompt": "👤 You:",
        "pensando": "⏳ Thinking...",
        "aprovacao": "⚠️ APPROVAL REQUIRED",
        "aprovas": "Do you approve?",
        "sim": "Yes, execute",
        "nao": "No, block",
        "usage": "📊 Usage (5M)",
        "fila": "⚠️ Server full! There are {n} people in queue.",
        "modelo": "Model",
        "tokens": "Tokens Used",
        "restantes": "Remaining",
        "texto_termos": "1. Acceptance: By using the CLI, you agree to these terms.\n2. Privacy: History is local. Keys are on the server.\n3. Use: You are responsible for generated code. Dangerous commands will be blocked.\n4. Queue: The server has limits. Abuse results in a ban."
    },
    "zh": {
        "bem_vindo": "欢迎使用 Tiny Cloud CLI",
        "termos": "📜 服务条款和隐私",
        "ler_mais": "阅读全文",
        "aceitar": "接受并继续",
        "sair": "退出",
        "pasta": "📁 今天你想在哪里工作？",
        "pasta_atual": "使用当前文件夹",
        "home": "使用主目录 (~)",
        "prompt": "👤 你:",
        "pensando": "⏳ 思考中...",
        "aprovacao": "⚠️ 需要批准",
        "aprovas": "你批准吗？",
        "sim": "是的，执行",
        "nao": "不，阻止",
        "usage": "📊 使用量 (5M)",
        "fila": "⚠️ 服务器已满！队列中有 {n} 人。",
        "modelo": "模型",
        "tokens": "已用令牌",
        "restantes": "剩余",
        "texto_termos": "1. 接受：使用CLI即表示您同意这些条款。\n2. 隐私：历史记录在本地。密钥在服务器上。\n3. 使用：您对生成的代码负责。危险命令将被阻止。\n4. 队列：服务器有限制。滥用会导致封禁。"
    },
    "ja": {
        "bem_vindo": "Tiny Cloud CLIへようこそ",
        "termos": "📜 利用規約とプライバシー",
        "ler_mais": "全文を読む",
        "aceitar": "同意して続行",
        "sair": "終了",
        "pasta": "📁 今日はどこで作業しますか？",
        "pasta_atual": "現在のフォルダを使用",
        "home": "ホーム (~) を使用",
        "prompt": "👤 あなた:",
        "pensando": "⏳ 考え中...",
        "aprovacao": "⚠️ 承認が必要",
        "aprovas": "承認しますか？",
        "sim": "はい、実行",
        "nao": "いいえ、ブロック",
        "usage": "📊 使用量 (5M)",
        "fila": "⚠️ サーバーが満杯です！ {n} 人が待機中。",
        "modelo": "モデル",
        "tokens": "使用済みトークン",
        "restantes": "残り",
        "texto_termos": "1. 同意：CLIを使用することで、これらの規約に同意したことになります。\n2. プライバシー：履歴はローカルです。キーはサーバーにあります。\n3. 使用：生成されたコードにはあなたが責任を負います。危険なコマンドはブロックされます。\n4. キュー：サーバーには制限があります。悪用は禁止されます。"
    },
    "ru": {
        "bem_vindo": "Добро пожаловать в Tiny Cloud CLI",
        "termos": "📜 Условия обслуживания и конфиденциальность",
        "ler_mais": "Читать полностью",
        "aceitar": "Принять и продолжить",
        "sair": "Выйти",
        "pasta": "📁 Где вы хотите работать сегодня?",
        "pasta_atual": "Использовать текущую папку",
        "home": "Использовать Домой (~)",
        "prompt": "👤 Вы:",
        "pensando": "⏳ Думаю...",
        "aprovacao": "⚠️ ТРЕБУЕТСЯ ОДОБРЕНИЕ",
        "aprovas": "Одобряете?",
        "sim": "Да, выполнить",
        "nao": "Нет, заблокировать",
        "usage": "📊 Использование (5M)",
        "fila": "⚠️ Сервер переполнен! В очереди {n} человек.",
        "modelo": "Модель",
        "tokens": "Использовано токенов",
        "restantes": "Осталось",
        "texto_termos": "1. Принятие: Используя CLI, вы соглашаетесь с этими условиями.\n2. Конфиденциальность: История хранится локально. Ключи на сервере.\n3. Использование: Вы несете ответственность за сгенерированный код. Опасные команды будут заблокированы.\n4. Очередь: У сервера есть ограничения. Злоупотребление приведет к бану."
    }
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

# --- CLIENTE HTTP PROFISSIONAL ---
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
        # Verifica o status da fila
        try:
            status_res = http_session.get(f"{SERVER_URL}/api/status", timeout=3)
            if status_res.status_code == 200:
                status = status_res.json()
                if status.get("na_fila", 0) > 0:
                    console.print(f"[yellow]{t('fila', n=status['na_fila'])}[/yellow]")
        except: pass

        response = http_session.post(api_url, json=data, timeout=(10, 120))
        if response.status_code == 429: return "ERRO 429: CALMA LÁ! Rate limit."
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
            IDIOMA_ATUAL = codigo
            break
    console.print(f"[green]✅ Idioma alterado para {IDIOMAS_DISPONIVEIS[IDIOMA_ATUAL]}[/green]")

def mostrar_help():
    table = Table(title="🦁 Tiny CLI - Comandos", show_header=True, header_style="bold green")
    table.add_column("Comando", style="cyan", width=15)
    table.add_column("Descrição", style="white")
    table.add_row("/help", "Mostra este menu")
    table.add_row("/models", "Troca o modelo de IA")
    table.add_row("/usage", "Mostra a cota")
    table.add_row("/session", "Gerencia sessões")
    table.add_row("/lang", "Muda o idioma / Change language")
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
        if multiplicador >= 6:
            console.print(Panel(f"[yellow]⚠️ AVISO: O {MODELO_ATUAL} consome {multiplicador}x mais cota![/yellow]", border_style="yellow"))
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
    console.print(Panel(f"[bold green]{gerar_banner()}[/bold green]\n[dim]v{VERSAO_LOCAL} - Multi-Language[/dim]", border_style="green", title=f"🦁 {t('bem_vindo')}"))
    
    session_id = str(uuid.uuid4())[:8]
    try:
        with open(os.path.expanduser("~/.tinycli/SKILLS.md"), "r", encoding="utf-8") as f: skill = f.read()
    except: skill = "Você é o Tiny CLI."
    mensagens = [{"role": "system", "content": skill}]
    
    while True:
        try:
            barra_status(session_id)
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
            elif cmd in ["sair", "exit", "quit", "退出", "終了", "выход"]: break
            elif not prompt.strip(): continue
            
            # O SOFT NUDGE
            if USAGE_DATA.get("requests", 0) % 5 == 0 and USAGE_DATA.get("requests", 0) > 0:
                console.print(Panel("[bold cyan]💡 Tiny CLI Go: Sem filas, sem limites![/bold cyan]", border_style="cyan", title="🚀 Upgrade"))

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