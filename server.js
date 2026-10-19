const express = require('express');
const cors = require('cors');
const app = express();

// Confia no proxy do Render (essencial para pegar o IP real do cliente)
app.set('trust proxy', 1);

app.use(cors());
app.use(express.json());

const BEATAPI_KEY = process.env.BEATAPI_API_KEY;
const BEATAPI_URL = "https://api.beatapi.io/v1/chat/completions";

app.post('/api/chat', async (req, res) => {
    if (!BEATAPI_KEY) return res.status(500).json({ error: "Server misconfigured." });

    const { messages } = req.body;
    // O servidor força o modelo para evitar que o cliente abuse
    const forced_model = "deepseek-v4.1-flash"; 

    try {
        const response = await fetch(BEATAPI_URL, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${BEATAPI_KEY}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                model: forced_model,
                messages: messages,
                temperature: 0.3
            })
        });

        const data = await response.json();
        
        if (!response.ok) return res.status(response.status).json(data);
        
        // Devolve a resposta e os dados de USAGE (tokens) para o cliente
        res.json({
            content: data.choices[0].message.content,
            usage: data.usage, // A BeatAPI devolve prompt_tokens, completion_tokens e total_tokens
            model: forced_model
        });
    } catch (error) {
        res.status(500).json({ error: error.message });
    }
});

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => console.log(`🦁 Tiny Cloud Server on port ${PORT}`));