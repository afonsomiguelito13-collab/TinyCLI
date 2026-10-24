#!/bin/bash

# Cores
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

# --- FUNÇÃO DA BARRA DE PROGRESSO ---
barra_progresso() {
    local duracao=$1
    local descricao=$2
    local passos=30
    local sleep_time=$(echo "scale=3; $duracao / $passos" | bc)

    printf "\n${CYAN}%s${NC}\n" "$descricao"
    
    # Inicia a barra vazia
    printf "${YELLOW}["
    for ((i=0; i<$passos; i++)); do printf " "; done
    printf "] 0%%\r"
    printf "${YELLOW}["

    for ((i=0; i<=$passos; i++)); do
        # Calcula a percentagem
        local percent=$(( i * 100 / passos ))
        
        # Desenha o bloco preenchido
        printf "${GREEN}█${YELLOW}"
        
        # Se for o último, fecha a barra
        if [ $i -eq $passos ]; then
            printf "] ${GREEN}100%%${NC}\n"
        else
            printf "] %d%%\r${YELLOW}[" $percent
        fi
        sleep $sleep_time
    done
}

echo -e "${GREEN}🦁 A instalar o Tiny Cloud CLI...${NC}"

# 1. Verifica o Python
if ! command -v python3 &> /dev/null; then
    echo -e "${YELLOW}⚠️ Python3 não encontrado. A instalar...${NC}"
    pkg install python -y || sudo apt install python3 -y
fi

# 2. Dependências com barra de progresso
barra_progresso 2.0 "📦 A instalar dependências (Rich, Questionary, Pyfiglet)..."
pip install rich questionary pyfiglet > /dev/null 2>&1

# 3. Baixar ficheiros com barra de progresso
barra_progresso 1.5 "⬇️ A baixar o Agente Cez (CLI)..."
REPO_URL="https://raw.githubusercontent.com/afonsomiguelito13-collab/TinyCLI/main/client"
CLIENT_DIR="$HOME/.tinycli"
WEB_DIR="$HOME/.tinycli/web"
mkdir -p "$CLIENT_DIR"
mkdir -p "$WEB_DIR"

curl -sL "$REPO_URL/tinycli.py" -o "$CLIENT_DIR/tinycli.py"
curl -sL "$REPO_URL/SKILLS.md" -o "$CLIENT_DIR/SKILLS.md"

barra_progresso 1.0 "⬇️ A baixar a Interface Web..."
curl -sL "$REPO_URL/tiny_web_server.py" -o "$WEB_DIR/tiny_web_server.py"
curl -sL "$REPO_URL/index.html" -o "$WEB_DIR/index.html"

# 4. Criar atalhos
barra_progresso 0.5 "🔗 A criar os atalhos globais..."
if [ -d "$PREFIX/bin" ]; then BIN_DIR="$PREFIX/bin"; else BIN_DIR="/usr/local/bin"; fi

cat << EOF > "$BIN_DIR/tinycli"
#!/bin/bash
export TINY_SERVER_URL="https://tinycli.onrender.com"
python3 "$CLIENT_DIR/tinycli.py"
EOF
chmod +x "$BIN_DIR/tinycli"

cat << EOF > "$BIN_DIR/tinycli-web"
#!/bin/bash
cd "$WEB_DIR"
echo "A arrancar o servidor Web..."
python3 "$WEB_DIR/tiny_web_server.py" &
sleep 2
termux-open-url "http://localhost:8080" 2>/dev/null || echo "Abre o teu navegador em http://localhost:8080"
wait
EOF
chmod +x "$BIN_DIR/tinycli-web"

echo -e "\n${GREEN}✅ Tudo pronto!${NC}"
echo -e "🚀 Para o terminal: ${GREEN}tinycli${NC}"
echo -e "🌐 Para a Interface Web: ${GREEN}tinycli-web${NC}"