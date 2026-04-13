
import os
import requests
from fastapi import FastAPI, Request
from fastapi.responses import FileResponse

# Pega a chave do cofre da Vercel que você configurou
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

app = FastAPI()

@app.get("/")
async def read_index():
    return FileResponse('index.html')

@app.post("/chat")
async def chat_endpoint(request: Request):
    data = await request.json()
    pergunta = data.get("pergunta", "")
    
    if not GOOGLE_API_KEY:
        return {"resposta": "Erro: Chave não encontrada na Vercel."}
    
    # Chamada direta para a API estável v1
    url = f"https://generativelanguage.googleapis.com/v1/models/gemini-1.5-flash:generateContent?key={GOOGLE_API_KEY}"
    
    payload = {
        "contents": [{
            "parts": [{"text": f"Você é a Ágape V36, criada por Cristiano Marques. Responda: {pergunta}"}]
        }]
    }
    
    try:
        response = requests.post(url, json=payload)
        result = response.json()
        
        # Pega a resposta do texto
        texto_resposta = result['candidates'][0]['content']['parts'][0]['text']
        return {"resposta": texto_resposta}
    except Exception as e:
        return {"resposta": f"Erro na conexão: {str(e)}"}
