import os
from flask import Flask, request, jsonify, render_template_string
import aiohttp
import asyncio

app = Flask(__name__)

# Configuração da Porta do Render
PORT = int(os.environ.get("PORT", 10000))

# O HTML que você vai ver (Interface V36)
with open('index.html', 'r', encoding='utf-8') as f:
    INDEX_HTML = f.read()

@app.route('/')
def index():
    return render_template_string(INDEX_HTML)

@app.route('/chat', methods=['POST'])
def chat():
    # Aqui vai a lógica da sua malha de 72.160 nós e conexão Gemini
    # Por enquanto, mantemos a rota de resposta:
    dados = request.json
    pergunta = dados.get("pergunta", "")
    
    # Resposta temporária para teste
    resposta = f"ÁGAPE V36 Processando: {pergunta}. Malha de 72.160 nós ativa."
    
    return jsonify({"resposta": resposta})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=PORT)






