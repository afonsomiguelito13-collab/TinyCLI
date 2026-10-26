const express = require('express');
const cors = require('cors');
const rateLimit = require('express-rate-limit');
const app = express();

app.set('trust proxy', 1);
app.use(cors());
app.use(express.json({ limit: '10mb' }));

// --- CONFIGURAÇÕES ---
const VERSAO_ATUAL = "20.0.0";
const MAX_CONCORRENTES = 5;
let pedidos_ativos = 0;
let fila_espera = [];

// --- CHAVES E PROVIDERS ---
const BEATAPI_KEY = process.env.BEATAPI_API_KEY;
const VYCEAI_KEY = process.env.VYCEAI_API_KEY;
const APIMASTER_KEY = process.env.APIMASTER_API_KEY;

const BEATAPI_URL = "https://api.beatapi.io/v1/chat/completions";
const VYCEAI_URL = "https://vyceai.com/v1/chat/completions";
const APIMASTER_URL = "https://apimaster.ai/v1/chat/completions";

// --- MODELOS E MULTIPLICADORES DE CUSTO ---
const MODELOS = {
    // Modelos Baratos (Free)
    "deepseek-v4.1": { url: VYCEAI_URL, key: VYCEAI_KEY, real_name: "deepseek-v4.1", custo: 3 },
    "agnes-3.0-flash": { url: VYCEAI_URL, key: VYCEAI_KEY, real_name: "agnes-3.0-flash", custo: 3 },
    "gemini-3.8-flash": { url: BEATAPI_URL, key: BEATAPI_KEY, real_name: "gemini-3.8-flash", custo: 4 },
    
    // Modelos Caros (Go / Premium)
    "gpt-6-luna": { url: VYCEAI_URL, key: VYCEAI_KEY, real_name: "gpt-6-luna", custo: 8 },
    
    // O NOVO MENINO (API Master - 20x)
    "claude-opus-4.8": { url: APIMASTER_URL, key: APIMASTER_KEY, real_name: "claude-opus-4-8", custo: 20 }
};

// --- LIMITE RÍGIDO (SIMULAÇÃO DE QUOTA) ---
// O plano Free tem 5M de tokens. O Opus 4.8 a 20x queima tudo em ~250k tokens reais.
const LIMITE_FREE_TOKENS = 5000000; 
let tokens_usados = 0; // Em produção, isto seria persistido num banco de dados por utilizador.

app.get('/', (req, res) => res.send(`🦁 Tiny Cloud Server v${VERSAO_ATUAL} (Rígido)`));
app.get('/api/version', (req, res) => res.json({ version: VERSAO_ATUAL }));
app.get('/api/status', (req, res) => {
    res.json({ ativos: pedidos_ativos, na_fila: fila_espera.length, tokens_usados, limite: LIMITE_FREE_TOKENS });
});

// --- RATE LIMIT (O CASTIGO) ---
const limitador = rateLimit({
    windowMs: 15 * 60 * 1000,
    limit: 50,
    message: { error: "🚫 CASTIGO ATIVADO: Abusaste do sistema." },
});
app.use('/api/', limitador);

// --- LÓGICA DA FILA ---
function processarFila() {
    if (pedidos_ativos < MAX_CONCORRENTES && fila_espera.length > 0) {
        pedidos_ativos++;
        const { req, res, messages, config, model } = fila_espera.shift();
        executarPedido(req, res, messages, config, model);
    }
}

async function executarPedido(req, res, messages, config, model) {
    global.tokens_usados;

    // Verifica o limite rígido antes de enviar para a API
    const custoEstimado = 1000 * config.custo; // Estimativa conservadora
    if ((tokens_usados + custoEstimado) > LIMITE_FREE_TOKENS) {
        return res.status(429).json({ 
            error: "🚫 LIMITE RÍGIDO ATINGIDO: O teu plano Free esgotou os 5M de tokens. Faz upgrade para o Tiny CLI Go." 
        });
    }

    try {
        const response = await fetch(config.url, {
            method: 'POST',
            headers: { 'Authorization': `Bearer ${config.key}`, 'Content-Type': 'application/json' },
            body: JSON.stringify({ model: config.real_name, messages: messages, temperature: 0.3 })
        });

        const data = await response.json();
        
        // Atualiza o uso com base no custo real do modelo (se a API devolver tokens)
        if (data.usage && data.usage.total_tokens) {
            tokens_usados += (data.usage.total_tokens * config.custo);
        } else {
            tokens_usados += custoEstimado;
        }

        res.json({ choices: data.choices, usage: data.usage, modelo_usado: model });
    } catch (error) {
        res.status(500).json({ error: error.message });
    } finally {
        pedidos_ativos--;
        processarFila();
    }
}

app.post('/api/chat', async (req, res) => {
    const { messages, model } = req.body;
    const config = MODELOS[model];
    
    if (!config || !config.key) {
        return res.status(400).json({ error: `Modelo '${model}' inválido ou sem chave.` });
    }

    if (pedidos_ativos < MAX_CONCORRENTES) {
        pedidos_ativos++;
        await executarPedido(req, res, messages, config, model);
    } else {
        fila_espera.push({ req, res, messages, config, model });
    }
});

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => console.log(`🦁 Tiny Cloud Server v${VERSAO_ATUAL} on port ${PORT}`));