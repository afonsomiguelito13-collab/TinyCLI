const express = require('express');
const cors = require('cors');
const app = express();

// Configuração de Trust Proxy para o Render
app.set('trust proxy', 1);

app.use(cors());
app.use(express.json());

const BEATAPI_KEY = process.env.BEATAPI_API_KEY;
const BEATAPI_URL = "https://api.beatapi.io/v1/chat/completions";

// Lista de modelos permitidos (Free)
const MODELOS_PERMITIDOS = [
    "deepseek-v4.1-flash",
    "deepseek-v4-flash",
    "glm-5.3",
    "glm-5.3-flash",
    "gemini-3.8-flash",
    "jev-1.13"
];

app.post('/api/chat', async (req, res) => {
    if (!BEATAPI_KEY) return res.status(500).json({ error: "Server misconfigured." });

    const { messages, model } = req.body;
    
    // O Servidor decide: Se o modelo pedido for válido, usa. Se não, usa o padrão.
    let modelo_final = "deepseek-v4.1-flash";
    if (model && MODELOS_PERMITIDOS.includes(model)) {
        modelo_final = model;
    }

    try {
        const response = await fetch(BEATAPI_URL, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${BEATAPI_KEY}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                model: modelo_final,
                messages: messages,
                temperature: 0.3
            })
        });

        const data = await response.json();
        
        if (!response.ok) return res.status(response.status).json(data);
        
        // Devolve a resposta e o modelo que foi REALMENTE usado
        res.json({
            choices: data.choices,
            usage: data.usage,
            modelo_usado: modelo_final
        });
    } catch (error) {
        res.status(500).json({ error: error.message });
    }
});

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => console.log(`🦁 Tiny Cloud Server on port ${PORT}`));