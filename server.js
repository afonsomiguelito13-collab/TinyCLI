const express = require('express');
const cors = require('cors');
const app = express();

app.set('trust proxy', 1);
app.use(cors());
app.use(express.json());

// Chaves de API
const BEATAPI_KEY = process.env.BEATAPI_API_KEY;
const VYCEAI_KEY = process.env.VYCEAI_API_KEY;

// Endpoints dos Providers
const BEATAPI_URL = "https://api.beatapi.io/v1/chat/completions";
const VYCEAI_URL = "https://vyceai.com/v1/chat/completions";

// Lista de modelos permitidos e os seus providers
const MODELOS = {
    // VyceAI (os teus créditos)
    "agnes-3.0-flash": { provider: "vyceai", url: VYCEAI_URL, key: VYCEAI_KEY },
    "deepseek-v4-flash": { provider: "vyceai", url: VYCEAI_URL, key: VYCEAI_KEY },
    "deepseek-v4.1": { provider: "vyceai", url: VYCEAI_URL, key: VYCEAI_KEY },
    
    // BeatAPI (grátis)
    "gemini-3.8-flash": { provider: "beatapi", url: BEATAPI_URL, key: BEATAPI_KEY },
    "jev-1.13": { provider: "beatapi", url: BEATAPI_URL, key: BEATAPI_KEY }
};

app.post('/api/chat', async (req, res) => {
    const { messages, model } = req.body;
    
    // Valida se o modelo existe e se o provider tem chave
    const config = MODELOS[model];
    if (!config || !config.key) {
        return res.status(400).json({ error: "Modelo inválido ou provider sem chave configurada." });
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
        
        // Devolve a resposta, os tokens gastos e o modelo usado
        res.json({
            choices: data.choices,
            usage: data.usage || { total_tokens: 0 }, // Fallback se o provider não mandar tokens
            modelo_usado: model
        });
    } catch (error) {
        res.status(500).json({ error: error.message });
    }
});

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => console.log(`🦁 Tiny Cloud Server on port ${PORT} - Providers: BeatAPI & VyceAI`));