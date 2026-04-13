import os
import requests
from fastapi import FastAPI, Request
from fastapi.responses import FileResponse

# Pega a chave do cofre da Vercel
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
    
    # Chamada direta para a API estável
    url = f"https://generativelanguage.googleapis.com/v1/models/gemini-1.5-flash:generateContent?key={GOOGLE_API_KEY}"
    
    payload = {
        "contents": [{
            "parts": [{"text": f"Você é a Ágape V36. Responda: {pergunta}"}]
        }]
    }
    
    try:
        response = requests.post(url, json=payload)
        result = response.json()
        
        # Se o Google mandar um erro de saldo ou chave, o código nos avisa
        if 'error' in result:
            return {"resposta": f"Mensagem do Google: {result['error']['message']}"}
            
        # Pega a resposta com segurança
        candidates = result.get('candidates', [])
        if candidates:
            texto_resposta = candidates[0].get('content', {}).get('parts', [{}])[0].get('text', 'Resposta vazia.')
            return {"resposta": texto_resposta}
        else:
            return {"resposta": "O Google não gerou resposta. Verifique o saldo ou a chave."}
            
    except Exception as e:
        return {"resposta": f"Erro de processamento: {str(e)}"}
