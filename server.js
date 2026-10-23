const express = require('express');
const cors = require('cors');
const rateLimit = require('express-rate-limit');
const app = express();

app.set('trust proxy', 1);
app.use(cors());
app.use(express.json());

// --- SISTEMA DE FILA ---
const MAX_CONCORRENTES = 5;
let pedidos_ativos = 0;
let fila_espera = [];
let total_requests = 0;

const VERSAO_ATUAL = "18.0.0";

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

// --- ROTA PARA OBTER O NICKNAME DO GITHUB ---
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

// --- LÓGICA DA FILA (CHAT) ---
function processarFila() {
    if (pedidos_ativos < MAX_CONCORRENTES && fila_espera.length > 0) {
        pedidos_ativos++;
        const { req, res, messages, config, model } = fila_espera.shift();
        executarPedido(req, res, messages, config, model);
    }
}

async function executarPedido(req, res, messages, config, model) {
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
        res.json({ choices: data.choices, usage: data.usage, modelo_usado: model });
    } catch (error) {
        res.status(500).json({ error: error.message });
    } finally {
        pedidos_ativos--;
        processarFila();
    }
}

// --- MODELOS ---
const BEATAPI_KEY = process.env.BEATAPI_API_KEY;
const VYCEAI_KEY = process.env.VYCEAI_API_KEY;

const MODELOS = {
    "agnes-3.0-flash": { url: "https://vyceai.com/v1/chat/completions", key: VYCEAI_KEY, real_name: "agnes-3.0-flash" },
    "gpt-6-luna": { url: "https://vyceai.com/v1/chat/completions", key: VYCEAI_KEY, real_name: "gpt-6-luna" },
    "deepseek-v4.1": { url: "https://vyceai.com/v1/chat/completions", key: VYCEAI_KEY, real_name: "deepseek-v4.1" },
    "deepseek-v4-flash": { url: "https://vyceai.com/v1/chat/completions", key: VYCEAI_KEY, real_name: "deepseek-v4-flash" },
    "gemini-3.8-flash": { url: "https://api.beatapi.io/v1/chat/completions", key: BEATAPI_KEY, real_name: "gemini-3.8-flash" }
};

app.post('/api/chat', async (req, res) => {
    total_requests++;
    const { messages, model } = req.body;
    const config = MODELOS[model];
    if (!config || !config.key) return res.status(400).json({ error: `Modelo '${model}' inválido.` });

    if (pedidos_ativos < MAX_CONCORRENTES) {
        pedidos_ativos++;
        await executarPedido(req, res, messages, config, model);
    } else {
        console.log(`[FILA] Pedido em espera. Posição: ${fila_espera.length + 1}`);
        fila_espera.push({ req, res, messages, config, model });
    }
});

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => console.log(`🦁 Tiny Cloud Server v${VERSAO_ATUAL} on port ${PORT}`));