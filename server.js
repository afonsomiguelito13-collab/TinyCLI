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
    limit: 20,
    standardHeaders: 'draft-8',
    legacyHeaders: false,
    message: { error: "🚫 CASTIGO ATIVADO: Tu abusaste do sistema. Fica 15 minutos de castigo." },
});
app.use('/api/', limitador);

// --- VERSÃO DO SISTEMA ---
const VERSAO_ATUAL = "11.0.0";

app.get('/api/version', (req, res) => {
    res.json({ version: VERSAO_ATUAL });
});

// --- CHAVES E MODELOS ---
const BEATAPI_KEY = process.env.BEATAPI_API_KEY;
const VYCEAI_KEY = process.env.VYCEAI_API_KEY;
const XKIRO_KEY = process.env.XKIRO_API_KEY; // A chave nova

const BEATAPI_URL = "https://api.beatapi.io/v1/chat/completions";
const VYCEAI_URL = "https://vyceai.com/v1/chat/completions";
const XKIRO_URL = "https://api.xkiro.com/v1/chat/completions";

const MODELOS = {
    // VyceAI
    "agnes-3.0-flash": { url: VYCEAI_URL, key: VYCEAI_KEY },
    "deepseek-v4-flash": { url: VYCEAI_URL, key: VYCEAI_KEY },
    "deepseek-v4.1": { url: VYCEAI_URL, key: VYCEAI_KEY },
    "deepseek-v4.1-flash": { url: VYCEAI_URL, key: VYCEAI_KEY },
    "gpt-6-luna": { url: VYCEAI_URL, key: VYCEAI_KEY },
    
    // BeatAPI
    "gemini-3.8-flash": { url: BEATAPI_URL, key: BEATAPI_KEY },
    "jev-1.13": { url: BEATAPI_URL, key: BEATAPI_KEY },

    // xKiro (Space Bunny)
    "space-bunny": { url: XKIRO_URL, key: XKIRO_KEY }
};

app.post('/api/chat', async (req, res) => {
    const { messages, model } = req.body;
    
    const config = MODELOS[model];
    if (!config || !config.key) {
        return res.status(400).json({ error: "Modelo inválido ou provider sem chave." });
    }

    try {
        const response = await fetch(config.url, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${config.key}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                model: model,
                messages: messages,
                temperature: 0.3
            })
        });

        const data = await response.json();
        
        if (!response.ok) return res.status(response.status).json(data);
        
        res.json({
            choices: data.choices,
            usage: data.usage,
            modelo_usado: model
        });
    } catch (error) {
        res.status(500).json({ error: error.message });
    }
});

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => console.log(`🦁 Tiny Cloud Server (v${VERSAO_ATUAL}) on port ${PORT}`));