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
    limit: 50, // Aumentado para 50 para não te bloquear durante os testes
    standardHeaders: 'draft-8',
    legacyHeaders: false,
    message: { error: "🚫 CASTIGO ATIVADO: Tu abusaste do sistema. Fica 15 minutos de castigo." },
});
app.use('/api/', limitador);

const VERSAO_ATUAL = "11.6.0";

app.get('/', (req, res) => res.send("🦁 Tiny Cloud Server está online."));
app.get('/api/version', (req, res) => res.json({ version: VERSAO_ATUAL }));

// --- CHAVES E MODELOS ---
const BEATAPI_KEY = process.env.BEATAPI_API_KEY;
const VYCEAI_KEY = process.env.VYCEAI_API_KEY;
const XKIRO_KEY = process.env.XKIRO_API_KEY;

const BEATAPI_URL = "https://api.beatapi.io/v1/chat/completions";
const VYCEAI_URL = "https://vyceai.com/v1/chat/completions";
const XKIRO_URL = "https://api.xkiro.com/v1/chat/completions";

const MODELOS = {
    "agnes-3.0-flash": { url: VYCEAI_URL, key: VYCEAI_KEY, real_name: "agnes-3.0-flash" },
    "deepseek-v4-flash": { url: VYCEAI_URL, key: VYCEAI_KEY, real_name: "deepseek-v4-flash" },
    "deepseek-v4.1": { url: VYCEAI_URL, key: VYCEAI_KEY, real_name: "deepseek-v4.1" },
    "deepseek-v4.1-flash": { url: VYCEAI_URL, key: VYCEAI_KEY, real_name: "deepseek-v4.1-flash" },
    "gpt-6-luna": { url: VYCEAI_URL, key: VYCEAI_KEY, real_name: "gpt-6-luna" },
    "gemini-3.8-flash": { url: BEATAPI_URL, key: BEATAPI_KEY, real_name: "gemini-3.8-flash" },
    "jev-1.13": { url: BEATAPI_URL, key: BEATAPI_KEY, real_name: "jev-1.13" },
    
    // Space Bunny mapeado para o nome real da xKiro
    "space-bunny": { url: XKIRO_URL, key: XKIRO_KEY, real_name: "stealth/space-bunny-alpha:free" },
    "stealth/space-bunny-alpha:free": { url: XKIRO_URL, key: XKIRO_KEY, real_name: "stealth/space-bunny-alpha:free" }
};

app.post('/api/chat', async (req, res) => {
    const { messages, model } = req.body;
    
    console.log(`[LOG] Pedido recebido para o modelo: ${model}`);

    const config = MODELOS[model];
    if (!config) {
        console.log(`[ERRO] Modelo '${model}' não encontrado na lista MODELOS.`);
        return res.status(400).json({ error: `Modelo '${model}' não encontrado no servidor.` });
    }
    
    if (!config.key) {
        console.log(`[ERRO] Chave de API em falta para o modelo: ${model}`);
        return res.status(400).json({ error: "Provider sem chave configurada nas Environment Variables do Render." });
    }

    try {
        const payload = {
            model: config.real_name, // Usa o nome real esperado pela API
            messages: messages,
            temperature: 0.3
        };

        console.log(`[LOG] A enviar para ${config.url} com o modelo ${config.real_name}`);

        const response = await fetch(config.url, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${config.key}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(payload)
        });

        const data = await response.json();
        
        if (!response.ok) {
            console.log(`[ERRO API] Status: ${response.status} - Resposta:`, data);
            return res.status(response.status).json(data);
        }
        
        res.json({
            choices: data.choices,
            usage: data.usage || { total_tokens: 0 }, // Previne erros se a API não mandar usage
            modelo_usado: model
        });
    } catch (error) {
        console.log(`[ERRO INTERNO]`, error.message);
        res.status(500).json({ error: error.message });
    }
});

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => console.log(`🦁 Tiny Cloud Server (v${VERSAO_ATUAL}) on port ${PORT}`));