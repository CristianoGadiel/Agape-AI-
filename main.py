import os
import requests
from fastapi import FastAPI, Request
from fastapi.responses import FileResponse

# Pega a chave que já está salva na sua Vercel
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
    
    # URL atualizada para o modelo 1.5-flash (mais estável para produção)
    # Você também pode trocar para 'gemini-2.0-flash' se preferir o mais novo
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GOOGLE_API_KEY}"
    
    payload = {
        "contents": [{
            "parts": [{"text": f"Você é a Ágape V36. Responda: {pergunta}"}]
        }]
    }
    
    try:
        response = requests.post(url, json=payload)
        result = response.json()
        
        # Mostra o erro real do Google caso algo aconteça
        if 'error' in result:
            return {"resposta": f"Google diz: {result['error']['message']}"}
            
        candidates = result.get('candidates', [])
        if candidates:
            texto = candidates[0].get('content', {}).get('parts', [{}])[0].get('text', 'Resposta vazia.')
            return {"resposta": texto}
        else:
            return {"resposta": "O Google não gerou resposta. Verifique sua conta."}
            
    except Exception as e:
        return {"resposta": f"Erro técnico: {str(e)}"}
