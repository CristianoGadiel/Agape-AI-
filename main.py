
import os
import requests
from flask import Flask, request, jsonify, render_template_string
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# Configurações do Google Gemini 2026
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
URL_BASE = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"

# Carrega o seu index.html (certifique-se que o arquivo existe no GitHub)
with open('index.html', 'r', encoding='utf-8') as f:
    INDEX_HTML = f.read()

@app.route('/')
def index():
    return render_template_string(INDEX_HTML)

@app.route('/chat', methods=['POST'])
def chat():
    data = request.get_json()
    pergunta = data.get('pergunta', '')
    
    if not pergunta:
        return jsonify({"resposta": "Diretriz ética não identificada."}), 400

    payload = {
        "contents": [{
            "parts": [{"text": f"Você é o ÁGAPE V36. Malha: 72.160 nós. Diretriz: {pergunta}"}]
        }]
    }

    try:
        response = requests.post(
            URL_BASE, 
            params={'key': GEMINI_API_KEY}, 
            json=payload, 
            timeout=30
        )
        response.raise_for_status()
        result = response.json()
        
        resposta_ia = result['candidates'][0]['content']['parts'][0]['text']
        return jsonify({"resposta": resposta_ia})
        
    except Exception as e:
        return jsonify({"resposta": f"Erro no núcleo Ágape: {str(e)}"}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)






