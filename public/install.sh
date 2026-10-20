#!/bin/bash

GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}🦁 Bem-vindo ao instalador do Tiny Cloud CLI!${NC}"

# 1. Instalar dependências base
echo -e "${BLUE}📦 A instalar dependências (Rich, Questionary, Pyfiglet, Prompt_Toolkit)...${NC}"
pkg install python -y > /dev/null 2>&1 || sudo apt install python3 -y > /dev/null 2>&1
pip install rich questionary pyfiglet prompt_toolkit > /dev/null 2>&1

# 2. Configurar caminhos
REPO_URL="https://raw.githubusercontent.com/afonsomiguelito13-collab/TinyCLI/main/client"
CLIENT_DIR="$HOME/.tinycli"
mkdir -p "$CLIENT_DIR"

# 3. Baixar o CLI
echo -e "${BLUE}⬇️ A baixar o Agente Cez (CLI)...${NC}"
curl -sL "$REPO_URL/tinycli.py" -o "$CLIENT_DIR/tinycli.py"
curl -sL "$REPO_URL/SKILLS.md" -o "$CLIENT_DIR/SKILLS.md"

# Criar o atalho do CLI
if [ -d "$PREFIX/bin" ]; then BIN_DIR="$PREFIX/bin"; else BIN_DIR="/usr/local/bin"; fi
cat << EOF > "$BIN_DIR/tinycli"
#!/bin/bash
export TINY_SERVER_URL="https://tinycli.onrender.com"
python3 "$CLIENT_DIR/tinycli.py"
EOF
chmod +x "$BIN_DIR/tinycli"

# 4. PERGUNTAR SE QUER A WEB (O Rei a decidir!)
echo -e "\n${YELLOW}🌐 Queres instalar a Interface Web do TinyCLI (tinycli-web)? (Y/n)${NC}"
read -p "> " web_choice

if [[ "$web_choice" == "y" || "$web_choice" == "Y" || -z "$web_choice" ]]; then
    echo -e "${BLUE}⬇️ A instalar a Interface Web...${NC}"
    
    # Criar pasta web
    WEB_DIR="$HOME/.tinycli/web"
    mkdir -p "$WEB_DIR"
    
    # Baixar ficheiros da web
    curl -sL "$REPO_URL/tiny_web_server.py" -o "$WEB_DIR/tiny_web_server.py"
    curl -sL "$REPO_URL/index.html" -o "$WEB_DIR/index.html"
    
    # Criar o atalho tinycli-web
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
    
    echo -e "${GREEN}✅ Instalação Web concluída! Corre 'tinycli-web' para começar.${NC}"
else
    echo -e "${YELLOW}⏭️  A saltar a instalação Web. Fica só com o CLI.${NC}"
fi

echo -e "\n${GREEN}✅ Tudo pronto! Bom código, chefe! 🦁${NC}"