#!/usr/bin/env python3
import os, sys, json, subprocess, urllib.request, urllib.error
import questionary
from questionary import Style
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown

console = Console()

custom_style = Style([
    ('qmark', 'fg:#00ff00 bold'),
    ('question', 'fg:#00bfff bold'),
    ('answer', 'fg:#00ff00 bold'),
    ('pointer', 'fg:#ffaa00 bold'),
    ('highlighted', 'fg:#00ff00 bold'),
    ('selected', 'fg:#00ff00'),
])

# O cliente NÃO tem chave. Ele bate no teu servidor Render.
SERVER_URL = os.environ.get("TINY_SERVER_URL", "http://127.0.0.1:3000")
TRUST_FILE = ".tiny_trust"

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
    api_url = f"{SERVER_URL}/api/chat"
    # O cliente não envia o modelo, o servidor decide.
    data = {"messages": mensagens}
    
    try:
        req = urllib.request.Request(api_url, data=json.dumps(data).encode("utf-8"), headers={"Content-Type": "application/json"}, method="POST")
        with urllib.request.urlopen(req) as response:
            return json.loads(response.read().decode("utf-8"))["choices"][0]["message"]["content"]
    except urllib.error.HTTPError as e:
        return f"ERRO NO SERVIDOR ({e.code}): {e.reason}"
    except Exception as e:
        return f"ERRO DE CONEXÃO: O servidor do Tiny CLI tá offline?"

# --- EXECUÇÃO DE FERRAMENTAS ---
def executar_ferramenta(resposta):
    try:
        if "```json" in resposta:
            resposta = resposta.split("```json")[1].split("```")[0]
        elif "```" in resposta:
             resposta = resposta.split("```")[1].split("```")[0]

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
                    if os.path.dirname(path):
                        os.makedirs(os.path.dirname(path), exist_ok=True)
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

# --- LOOP PRINCIPAL ---
def main():
    console.print(Panel("[bold green]🦁 Tiny Cloud CLI[/bold green]\nConectado ao servidor privado.", border_style="green"))
    
    if os.getcwd() not in DIRETORIOS_CONFIAVEIS:
        pedir_permissao(os.getcwd())

    # Carrega as skills locais
    try:
        with open(os.path.expanduser("~/.tinycli_skill.md"), "r", encoding="utf-8") as f:
            skill_content = f.read()
    except FileNotFoundError:
        skill_content = "Você é o Tiny CLI, um agente de programação."

    mensagens = [{"role": "system", "content": skill_content}]
    
    while True:
        try:
            prompt = console.input("[bold blue]👤 Tu:[/bold blue] ")
            if prompt.lower().strip() in ["sair", "exit"]: break
            if not prompt.strip(): continue
            
            mensagens.append({"role": "user", "content": prompt})
            console.print("[dim]⏳ Enviando para a nuvem...[/dim]")
            
            # Loop de Agente
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
