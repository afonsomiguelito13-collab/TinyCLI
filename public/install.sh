#!/bin/bash

GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}🦁 A instalar o Tiny Cloud CLI (Terminal + Web)...${NC}"

# 1. Instalar dependências do Python
if ! command -v python3 &> /dev/null; then
    echo -e "${YELLOW}⚠️ Python3 não encontrado. A instalar...${NC}"
    pkg install python -y || sudo apt install python3 -y
fi

echo -e "${BLUE}📦 A instalar dependências (Rich, Questionary, Pyfiglet, Prompt_Toolkit)...${NC}"
pip install rich questionary pyfiglet prompt_toolkit > /dev/null 2>&1

# 2. Configurar os caminhos
REPO_URL="https://raw.githubusercontent.com/afonsomiguelito13-collab/TinyCLI/main/client"
CLIENT_DIR="$HOME/.tinycli"
WEB_DIR="$HOME/.tinycli/web"

# Criar as pastas
mkdir -p "$CLIENT_DIR"
mkdir -p "$WEB_DIR"

# 3. Baixar o CLI e as Skills
echo -e "${BLUE}⬇️ A baixar o cérebro do Agente Cez (CLI)...${NC}"
curl -sL "$REPO_URL/tinycli.py" -o "$CLIENT_DIR/tinycli.py"
curl -sL "$REPO_URL/SKILLS.md" -o "$CLIENT_DIR/SKILLS.md"

# 4. Baixar a UI Web e o Servidor Local
echo -e "${BLUE}⬇️ A baixar a Interface Web...${NC}"
curl -sL "$REPO_URL/tiny_web_server.py" -o "$WEB_DIR/tiny_web_server.py"
curl -sL "$REPO_URL/index.html" -o "$WEB_DIR/index.html"

# 5. Criar o atalho GLOBAL do CLI no Terminal
echo -e "${BLUE}🔗 A criar o atalho 'tinycli'...${NC}"
if [ -d "$PREFIX/bin" ]; then BIN_DIR="$PREFIX/bin"; else BIN_DIR="/usr/local/bin"; fi

cat << EOF > "$BIN_DIR/tinycli"
#!/bin/bash
export TINY_SERVER_URL="https://tinycli.onrender.com"
python3 "$CLIENT_DIR/tinycli.py"
EOF
chmod +x "$BIN_DIR/tinycli"

# 6. Criar o atalho GLOBAL da Web
echo -e "${BLUE}🔗 A criar o atalho 'tinycli-web'...${NC}"
cat << EOF > "$BIN_DIR/tinycli-web"
#!/bin/bash
cd "$WEB_DIR"
echo "A arrancar o servidor Web..."
python3 "$WEB_DIR/tiny_web_server.py" &
sleep 2
# Tenta abrir o navegador no Termux
termux-open-url "http://localhost:8080" 2>/dev/null || echo "Abre o teu navegador em http://localhost:8080"
wait
EOF
chmod +x "$BIN_DIR/tinycli-web"

echo -e "${GREEN}✅ Instalação concluída com sucesso!${NC}"
echo -e "🚀 Para o terminal: ${GREEN}tinycli${NC}"
echo -e "🌐 Para a Interface Web: ${GREEN}tinycli-web${NC}"