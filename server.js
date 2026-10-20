const express = require('express');
const cors = require('cors');
const app = express();

app.set('trust proxy', 1);
app.use(cors());
app.use(express.json());

const BEATAPI_KEY = process.env.BEATAPI_API_KEY;
const VYCEAI_KEY = process.env.VYCEAI_API_KEY;

const BEATAPI_URL = "https://api.beatapi.io/v1/chat/completions";
const VYCEAI_URL = "https://vyceai.com/v1/chat/completions";

const MODELOS = {
    "agnes-3.0-flash": { url: VYCEAI_URL, key: VYCEAI_KEY },
    "deepseek-v4-flash": { url: VYCEAI_URL, key: VYCEAI_KEY },
    "deepseek-v4.1": { url: VYCEAI_URL, key: VYCEAI_KEY },
    "gemini-3.8-flash": { url: BEATAPI_URL, key: BEATAPI_KEY },
    "jev-1.13": { url: BEATAPI_URL, key: BEATAPI_KEY }
};

app.post('/api/chat', async (req, res) => {
    const { messages, model } = req.body;
    
    const config = MODELOS[model];
    if (!config || !config.key) {
        return res.status(400).json({ error: "Modelo inválido ou provider sem chave." });
    }

    // Configura os headers para Streaming (SSE)
    res.setHeader('Content-Type', 'text/event-stream');
    res.setHeader('Cache-Control', 'no-cache');
    res.setHeader('Connection', 'keep-alive');

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
                temperature: 0.3,
                stream: true // Pede streaming à API de origem
            })
        });

        if (!response.ok) {
            res.write(`data: ${JSON.stringify({ error: `Erro na API: ${response.status}` })}\n\n`);
            return res.end();
        }

        // Lê o corpo da resposta como um stream e repassa para o cliente
        const reader = response.body.getReader();
        const decoder = new TextDecoder();

        while (true) {
            const { done, value } = await reader.read();
            if (done) break;
            
            const chunk = decoder.decode(value, { stream: true });
            // Repassa o chunk exatamente como veio (já está no formato SSE)
            res.write(chunk);
        }
        
        res.end();

    } catch (error) {
        res.write(`data: ${JSON.stringify({ error: error.message })}\n\n`);
        res.end();
    }
});

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => console.log(`🦁 Tiny Cloud Server (Streaming) on port ${PORT}`));