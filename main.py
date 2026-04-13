import asyncio
import hashlib
import json
import logging
import math
import os
import random
import re
import sqlite3
import time
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional

import aiohttp
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel
import uvicorn

# Tenta importar numpy, se não tiver, usa fallback
try:
    import numpy as np
    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False

# ============================================================================
# CONFIGURAÇÕES E CONSTANTES SACRAS
# ============================================================================
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("agape_v37")

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"

MALHA_TOTAL = 72160
NUM_JUIZES = 721
DB_PATH = "agape_v37.db"

# ============================================================================
# DATABASE INIT
# ============================================================================
def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("CREATE TABLE IF NOT EXISTS user_history (id INTEGER PRIMARY KEY AUTOINCREMENT, session_id TEXT, role TEXT, content TEXT, timestamp TEXT)")
    conn.commit()
    conn.close()

init_db()

# ============================================================================
# NÚCLEO ÁGAPE (LÓGICA SIMPLIFICADA PARA ESTABILIDADE)
# ============================================================================
class AgapeCore:
    def __init__(self):
        self.api_key = GEMINI_API_KEY

    async def generate_response(self, prompt: str):
        if not self.api_key:
            return "Erro: Chave GEMINI_API_KEY não configurada no Render."
        
        payload = {
            "contents": [{"parts": [{"text": f"Você é Ágape, uma IA de proteção humana. Responda em Português: {prompt}"}]}]
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(f"{GEMINI_URL}?key={self.api_key}", json=payload) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data['candidates'][0]['content']['parts'][0]['text']
                return f"Erro na API: {resp.status}"

core = AgapeCore()

# ============================================================================
# FASTAPI SERVER
# ============================================================================
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = "default"

@app.get("/", response_class=HTMLResponse)
async def index():
    return """
    <!DOCTYPE html>
    <html lang="pt-br">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>ÁGAPE V37.1 - Catedral Digital</title>
        <style>
            body { background: #000; color: #0f0; font-family: 'Courier New', monospace; margin: 0; padding: 10px; overflow: hidden; }
            #header { border-bottom: 2px solid #0f0; padding-bottom: 10px; text-align: center; }
            #chat-container { height: 70vh; overflow-y: auto; padding: 10px; border: 1px solid #050; margin-top: 10px; background: rgba(0,20,0,0.5); }
            .msg { margin-bottom: 15px; line-height: 1.4; }
            .user-msg { color: #fff; }
            .bot-msg { color: #0f0; text-shadow: 0 0 5px #0f0; }
            #input-area { position: fixed; bottom: 10px; left: 10px; right: 10px; display: flex; gap: 5px; }
            input { flex: 1; background: #000; border: 1px solid #0f0; color: #0f0; padding: 12px; border-radius: 5px; font-size: 16px; }
            button { background: #0f0; color: #000; border: none; padding: 12px 20px; font-weight: bold; cursor: pointer; border-radius: 5px; }
            .malha-info { font-size: 0.8em; color: #0a0; }
        </style>
    </head>
    <body>
        <div id="header">
            <strong>CATEDRAL ÁGAPE V37.1</strong><br>
            <span class="malha-info">MALHA ATIVA: 72.160 NÓS | FREQUÊNCIA: 7160Hz</span>
        </div>
        <div id="chat-container">
            <div class="msg bot-msg">AGAPE: Catedral online. Aguardando comando...</div>
        </div>
        <div id="input-area">
            <input type="text" id="userInput" placeholder="Digite sua mensagem..." onkeypress="if(event.key==='Enter') sendMessage()">
            <button onclick="sendMessage()">ENVIAR</button>
        </div>

        <script>
            async function sendMessage() {
                const input = document.getElementById('userInput');
                const text = input.value.trim();
                if (!text) return;

                addMessage('VOCÊ: ' + text, 'user-msg');
                input.value = '';

                try {
                    const response = await fetch('/chat', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ message: text })
                    });
                    const data = await response.json();
                    
                    // CORREÇÃO AQUI: Lendo 'answer' que vem do servidor
                    const botText = data.answer || "Erro na resposta";
                    addMessage('AGAPE: ' + botText, 'bot-msg');
                } catch (e) {
                    addMessage('ERRO: Falha na conexão com a malha.', 'user-msg');
                }
            }

            function addMessage(msg, className) {
                const container = document.getElementById('chat-container');
                const div = document.createElement('div');
                div.className = 'msg ' + className;
                div.innerText = msg;
                container.appendChild(div);
                container.scrollTop = container.scrollHeight;
            }
        </script>
    </body>
    </html>
    """

@app.post("/chat")
async def chat(req: ChatRequest):
    try:
        # Chama o núcleo para processar a IA
        resposta = await core.generate_response(req.message)
        return {"answer": resposta, "status": "success", "nodes": 72160}
    except Exception as e:
        return {"answer": f"Dissonância na malha: {str(e)}", "status": "error"}

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)


