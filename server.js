const express = require('express');
const cors = require('cors');
const rateLimit = require('express-rate-limit');
const app = express();

app.set('trust proxy', 1);
app.use(cors());
app.use(express.json());

// --- SISTEMA DE CASTIGO (RATE LIMIT) ---
const limitador = rateLimit({
    windowMs: 15 * 60 * 1000,
    limit: 50,
    standardHeaders: 'draft-8',
    legacyHeaders: false,
    message: { error: "🚫 CASTIGO ATIVADO: Tu abusaste do sistema. Fica 15 minutos de castigo." },
});
app.use('/api/', limitador);

const VERSAO_ATUAL = "12.0.0";

app.get('/', (req, res) => res.send(`🦁 Tiny Cloud Server v${VERSAO_ATUAL} (Model Pool) está online.`));
app.get('/api/version', (req, res) => res.json({ version: VERSAO_ATUAL }));

// --- CONFIGURAÇÃO DOS PROVIDERS ---
const PROVIDERS = {
    vyceai: {
        url: "https://vyceai.com/v1/chat/completions",
        key: process.env.VYCEAI_API_KEY
    },
    beatapi: {
        url: "https://api.beatapi.io/v1/chat/completions",
        key: process.env.BEATAPI_API_KEY
    },
    xkiro: {
        url: "https://api.xkiro.com/v1/chat/completions",
        key: process.env.XKIRO_API_KEY
    }
};

// --- O MODEL POOL ---
// Cada "nome amigável" tem uma lista de fallbacks (provider + nome real)
const MODEL_POOL = {
    "deepseek-v4.1": [
        { provider: "vyceai", model: "deepseek-v4.1" },
        { provider: "beatapi", model: "deepseek-v4.1" }
    ],
    "deepseek-v4.1-flash": [
        { provider: "vyceai", model: "deepseek-v4.1-flash" }
    ],
    "gemini-3.8-flash": [
        { provider: "beatapi", model: "gemini-3.8-flash" }
    ],
    "agnes-3.0-flash": [
        { provider: "vyceai", model: "agnes-3.0-flash" }
    ],
    "jev-1.13": [
        { provider: "beatapi", model: "jev-1.13" }
    ],
    "gpt-6-luna": [
        { provider: "vyceai", model: "gpt-6-luna" },
        { provider: "beatapi", model: "gpt-6-luna" } // Fallback
    ],
    "space-bunny": [
        { provider: "xkiro", model: "stealth/space-bunny-alpha:free" }
    ],
    "longcat-2.5": [
        { provider: "xkiro", model: "meituan/longcat-2.5-preview:free" }
    ]
};

app.post('/api/chat', async (req, res) => {
    const { messages, model } = req.body;
    
    console.log(`[LOG] Pedido recebido. Modelo: ${model}`);

    const pool = MODEL_POOL[model];
    if (!pool) {
        return res.status(400).json({ error: `Modelo '${model}' não encontrado no Pool.` });
    }

    let ultimo_erro = null;

    // Itera sobre os modelos do pool (Failover)
    for (const config of pool) {
        const provider = PROVIDERS[config.provider];
        
        if (!provider || !provider.key) {
            console.log(`[AVISO] Provider ${config.provider} sem chave. A saltar...`);
            continue;
        }

        try {
            console.log(`[TENTATIVA] A usar ${config.provider} com o modelo ${config.model}`);
            
            const response = await fetch(provider.url, {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${provider.key}`,
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    model: config.model,
                    messages: messages,
                    temperature: 0.3
                })
            });

            const data = await response.json();

            if (!response.ok) {
                console.log(`[ERRO] Provider ${config.provider} devolveu ${response.status}. A tentar próximo...`);
                ultimo_erro = data;
                continue; // Tenta o próximo do pool
            }

            // SUCESSO!
            console.log(`[SUCESSO] ${config.provider} respondeu!`);
            return res.json({
                choices: data.choices,
                usage: data.usage || { total_tokens: 0 },
                modelo_usado: model, // Devolve o nome amigável para o CLI
                provider_usado: config.provider
            });

        } catch (error) {
            console.log(`[ERRO DE REDE] ${config.provider}: ${error.message}`);
            ultimo_erro = { error: error.message };
            // Continua para o próximo do pool
        }
    }

    // Se chegou aqui, todos falharam
    console.log(`[FALHA TOTAL] Todos os modelos do pool '${model}' falharam.`);
    res.status(503).json({ 
        error: "Todos os modelos deste pool estão indisponíveis no momento. Tenta outro modelo.",
        detalhes: ultimo_erro 
    });
});

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => console.log(`🦁 Tiny Cloud Server v${VERSAO_ATUAL} on port ${PORT}`));