const express = require('express');
const cors = require('cors');
const rateLimit = require('express-rate-limit');
const fs = require('fs');
const path = require('path');
const app = express();

app.set('trust proxy', 1);
app.use(cors());
app.use(express.json({ limit: '10mb' }));

// --- SISTEMA DE FILA ---
const MAX_CONCORRENTES = 5;
let pedidos_ativos = 0;
let fila_espera = [];
let total_requests = 0;

const VERSAO_ATUAL = "19.0.0";
const SESSIONS_DIR = path.join(process.env.HOME || '/tmp', '.tinycli_sessions');

// Cria a pasta de sessões se não existir
if (!fs.existsSync(SESSIONS_DIR)) {
    fs.mkdirSync(SESSIONS_DIR, { recursive: true });
}

app.get('/', (req, res) => res.send(`🦁 Tiny Cloud Server v${VERSAO_ATUAL} (Fila Ativa)`));
app.get('/api/version', (req, res) => res.json({ version: VERSAO_ATUAL }));

app.get('/api/status', (req, res) => {
    res.json({ 
        ativos: pedidos_ativos, 
        na_fila: fila_espera.length, 
        total_requests: total_requests,
        capacidade: MAX_CONCORRENTES
    });
});

// --- RATE LIMIT ---
const limitador = rateLimit({
    windowMs: 15 * 60 * 1000,
    limit: 50,
    standardHeaders: 'draft-8',
    legacyHeaders: false,
    message: { error: "🚫 CASTIGO ATIVADO: Abusaste do sistema. Fica 15 minutos de castigo." },
});
app.use('/api/', limitador);

// --- ROTA PARA O GITHUB ---
app.post('/api/github-user', async (req, res) => {
    const { token } = req.body;
    if (!token) return res.status(400).json({ error: "Token do GitHub em falta." });

    try {
        const response = await fetch('https://api.github.com/user', {
            headers: {
                'Authorization': `Bearer ${token}`,
                'Accept': 'application/vnd.github+json',
                'X-GitHub-Api-Version': '2022-11-28'
            }
        });
        
        if (!response.ok) {
            return res.status(response.status).json({ error: "Token do GitHub inválido." });
        }

        const data = await response.json();
        res.json({ username: data.login, avatar: data.avatar_url });
    } catch (error) {
        res.status(500).json({ error: error.message });
    }
});

// --- ROTAS DE SESSÃO (PARA O INDEX.HTML) ---
app.get('/sessions', (req, res) => {
    try {
        const sessions = fs.readdirSync(SESSIONS_DIR)
            .filter(f => f.endsWith('.json'))
            .map(f => f.replace('.json', ''));
        res.json({ sessions });
    } catch (error) {
        res.json({ sessions: [] });
    }
});

app.get('/history/:session_id', (req, res) => {
    const sessionId = req.params.session_id;
    const filepath = path.join(SESSIONS_DIR, `${sessionId}.json`);
    
    if (fs.existsSync(filepath)) {
        res.json(JSON.parse(fs.readFileSync(filepath, 'utf8')));
    } else {
        res.json({ messages: [] });
    }
});

app.get('/usage', (req, res) => {
    // Simulação de usage (para o HTML não quebrar)
    res.json({ tokens: 0 });
});

// --- LÓGICA DA FILA (CHAT) ---
function processarFila() {
    if (pedidos_ativos < MAX_CONCORRENTES && fila_espera.length > 0) {
        pedidos_ativos++;
        const { req, res, messages, config, model, session_id } = fila_espera.shift();
        executarPedido(req, res, messages, config, model, session_id);
    }
}

async function executarPedido(req, res, messages, config, model, session_id) {
    try {
        const response = await fetch(config.url, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${config.key}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                model: config.real_name,
                messages: messages,
                temperature: 0.3
            })
        });

        const data = await response.json();
        
        // Guarda a sessão
        if (data.choices && data.choices[0]) {
            const botReply = data.choices[0].message.content;
            salvar_sessao(session_id, messages[messages.length - 1].content, botReply);
        }

        res.json({ 
            choices: data.choices, 
            usage: data.usage, 
            modelo_usado: model 
        });
    } catch (error) {
        res.status(500).json({ error: error.message });
    } finally {
        pedidos_ativos--;
        processarFila();
    }
}

function salvar_sessao(session_id, user_msg, bot_msg) {
    const filepath = path.join(SESSIONS_DIR, `${session_id}.json`);
    let messages = [];
    
    if (fs.existsSync(filepath)) {
        messages = JSON.parse(fs.readFileSync(filepath, 'utf8')).messages;
    }
    
    messages.push({ role: 'user', content: user_msg });
    messages.push({ role: 'assistant', content: bot_msg });
    
    fs.writeFileSync(filepath, JSON.stringify({ messages }));
}

// --- MODELOS ---
const BEATAPI_KEY = process.env.BEATAPI_API_KEY;
const VYCEAI_KEY = process.env.VYCEAI_API_KEY;

const MODELOS = {
    "deepseek-v4.1": { url: "https://vyceai.com/v1/chat/completions", key: VYCEAI_KEY, real_name: "deepseek-v4.1" },
    "agnes-3.0-flash": { url: "https://vyceai.com/v1/chat/completions", key: VYCEAI_KEY, real_name: "agnes-3.0-flash" },
    "gpt-6-luna": { url: "https://vyceai.com/v1/chat/completions", key: VYCEAI_KEY, real_name: "gpt-6-luna" },
    "gemini-3.8-flash": { url: "https://api.beatapi.io/v1/chat/completions", key: BEATAPI_KEY, real_name: "gemini-3.8-flash" },
    "space-bunny": { url: "https://api.xkiro.com/v1/chat/completions", key: process.env.XKIRO_API_KEY, real_name: "stealth/space-bunny-alpha:free" }
};

app.post('/api/chat', async (req, res) => {
    total_requests++;
    const { messages, model, session_id } = req.body;
    const config = MODELOS[model];
    if (!config || !config.key) return res.status(400).json({ error: `Modelo '${model}' inválido.` });

    if (pedidos_ativos < MAX_CONCORRENTES) {
        pedidos_ativos++;
        await executarPedido(req, res, messages, config, model, session_id);
    } else {
        console.log(`[FILA] Pedido em espera. Posição: ${fila_espera.length + 1}`);
        fila_espera.push({ req, res, messages, config, model, session_id });
    }
});

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => console.log(`🦁 Tiny Cloud Server v${VERSAO_ATUAL} on port ${PORT}`));