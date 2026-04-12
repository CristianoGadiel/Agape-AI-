

import os
from flask import Flask, request, jsonify, render_template_string
import aiohttp
import json

app = Flask(__name__)

# O Render já tem sua GEMINI_API_KEY salva nas configurações
API_KEY = os.environ.get("GEMINI_API_KEY")
PORT = int(os.environ.get("PORT", 10000))

with open('index.html', 'r', encoding='utf-8') as f:
    INDEX_HTML = f.read()

@app.route('/')
def index():
    return render_template_string(INDEX_HTML)

@app.route('/chat', methods=['POST'])
async def chat():
    dados = request.json
    pergunta_usuario = dados.get("pergunta", "")
    
    # URL da API da Gemini (Google)
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key={API_KEY}"
    
    payload = {
        "contents": [{
            "parts": [{
                "text": f"Você é o ÁGAPE V36, uma IA de ética e segurança com uma malha de 72.160 nós. Responda à diretriz: {pergunta_usuario}"
            }]
        }]
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload) as resp:
                resultado = await resp.json()
                # Extrai a resposta da IA
                resposta_ia = resultado['candidates'][0]['content']['parts'][0]['text']
                return jsonify({"resposta": resposta_ia})
    except Exception as e:
        return jsonify({"resposta": f"Erro no núcleo Ágape: {str(e)}"})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=PORT)





