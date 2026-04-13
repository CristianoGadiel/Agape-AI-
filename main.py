import os
import requests
from fastapi import FastAPI, Request
from fastapi.responses import FileResponse

# Pega a chave que você salvou com sucesso na Vercel
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
    
    # Esta é a URL definitiva para faturamento e estabilidade
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GOOGLE_API_KEY}"
    
    payload = {
        "contents": [{
            "parts": [{"text": f"Você é a Ágape V36. Responda de forma direta: {pergunta}"}]
        }]
    }
    
    try:
        response = requests.post(url, json=payload)
        result = response.json()
        
        # Se houver erro de cota ou chave, ele aparecerá aqui
        if 'error' in result:
            return {"resposta": f"Aviso do Google: {result['error']['message']}"}
            
        # Extração segura da resposta
        if 'candidates' in result and len(result['candidates']) > 0:
            texto = result['candidates'][0]['content']['parts'][0]['text']
            return {"resposta": texto}
        else:
            return {"resposta": "O modelo não gerou uma resposta. Verifique seu painel do Google AI Studio."}
            
    except Exception as e:
        return {"resposta": f"Erro de conexão: {str(e)}"}
