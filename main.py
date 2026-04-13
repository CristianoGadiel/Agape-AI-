import os
import requests
from fastapi import FastAPI, Request
from fastapi.responses import FileResponse

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
        return {"resposta": "Erro: Chave não configurada na Vercel."}
    
    # URL atualizada com '-latest' para a versão estável v1
    url = f"https://generativelanguage.googleapis.com/v1/models/gemini-1.5-flash-latest:generateContent?key={GOOGLE_API_KEY}"
    
    payload = {
        "contents": [{
            "parts": [{"text": f"Você é a Ágape V36. Responda de forma curta: {pergunta}"}]
        }]
    }
    
    try:
        response = requests.post(url, json=payload)
        result = response.json()
        
        if 'error' in result:
            return {"resposta": f"Google diz: {result['error']['message']}"}
            
        candidates = result.get('candidates', [])
        if candidates:
            texto = candidates[0].get('content', {}).get('parts', [{}])[0].get('text', 'Resposta vazia.')
            return {"resposta": texto}
        else:
            return {"resposta": "Resposta não gerada. Verifique o saldo."}
            
    except Exception as e:
        return {"resposta": f"Erro técnico: {str(e)}"}
