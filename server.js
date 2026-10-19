const express = require('express');
const cors = require('cors');
const app = express();

app.use(cors());
app.use(express.json());

// A chave da BeatAPI fica protegida nas Environment Variables do Render
const BEATAPI_KEY = process.env.BEATAPI_API_KEY;
const BEATAPI_URL = "https://api.beatapi.io/v1/chat/completions";

app.post('/api/chat', async (req, res) => {
    if (!BEATAPI_KEY) return res.status(500).json({ error: "Server misconfigured." });

    const { messages } = req.body;
    
    // O SERVIDOR DECIDE O MODELO. O cliente não tem escolha. (Close Source)
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
                temperature: 0.3 // Equilíbrio perfeito para agentes
            })
        });

        const data = await response.json();
        if (!response.ok) return res.status(response.status).json(data);
        
        res.json(data);
    } catch (error) {
        res.status(500).json({ error: error.message });
    }
});

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => console.log(`🦁 Tiny Cloud Server on port ${PORT}`));