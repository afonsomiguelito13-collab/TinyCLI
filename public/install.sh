#!/bin/bash

# Cores para o terminal
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}🦁 A instalar o Tiny Cloud CLI...${NC}"

# 1. Verifica se o Python está instalado
if ! command -v python3 &> /dev/null; then
    echo -e "${YELLOW}⚠️ Python3 não encontrado. A instalar...${NC}"
    pkg install python -y || sudo apt install python3 -y
fi

# 2. Instala as dependências visuais
echo -e "${BLUE}📦 A instalar dependências (Rich e Questionary)...${NC}"
pip install rich questionary > /dev/null 2>&1

# 3. Define os links do teu GitHub
REPO_URL="https://raw.githubusercontent.com/afonsomiguelito13-collab/TinyCLI/main"
CLIENT_DIR="$HOME/.tinycli"

# Cria a pasta oculta do Tiny CLI
mkdir -p "$CLIENT_DIR"

echo -e "${BLUE}⬇️ A baixar os ficheiros do agente...${NC}"
curl -sL "$REPO_URL/client/tinycli.py" -o "$CLIENT_DIR/tinycli.py"
curl -sL "$REPO_URL/client/SKILLS.md" -o "$CLIENT_DIR/SKILLS.md"

# Verifica se o download funcionou
if [ ! -f "$CLIENT_DIR/tinycli.py" ]; then
    echo -e "${YELLOW}❌ Erro ao baixar o tinycli.py. Verifica se o repositório é público.${NC}"
    exit 1
fi

# 4. Cria o comando global (Termux e Linux)
echo -e "${BLUE}🔗 A criar o atalho global...${NC}"

# Descobre a pasta de binários correta
if [ -d "$PREFIX/bin" ]; then
    BIN_DIR="$PREFIX/bin" # Termux
else
    BIN_DIR="/usr/local/bin" # Linux normal
fi

cat << EOF > "$BIN_DIR/tinycli"
#!/bin/bash
# ATENÇÃO: Substitui pela tua URL real do Render quando fizeres deploy!
export TINY_SERVER_URL="https://tiny-cloud-cli.onrender.com"
python3 "$CLIENT_DIR/tinycli.py"
EOF

chmod +x "$BIN_DIR/tinycli"

echo -e "${GREEN}✅ Instalação concluída com sucesso!${NC}"
echo -e "🚀 Para começar, basta digitar: ${GREEN}tinycli${NC}"
