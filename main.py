
import os
import requests
from fastapi import FastAPI, Request
from fastapi.responses import FileResponse

# Pega a chave que está salva com sucesso na sua Vercel
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
    
    # URL DE PRODUÇÃO ESTÁVEL (v1)
    # Usando o modelo 'gemini-pro', que é o padrão ouro de compatibilidade
    url = f"https://generativelanguage.googleapis.com/v1/models/gemini-pro:generateContent?key={GOOGLE_API_KEY}"
    
    payload = {
        "contents": [{
            "parts": [{"text": f"Você é a Ágape V36. Responda: {pergunta}"}]
        }]
    }
    
    try:
        response = requests.post(url, json=payload)
        result = response.json()
        
        # Captura mensagens reais do Google sobre saldo ou chave
        if 'error' in result:
            return {"resposta": f"Google informa: {result['error']['message']}"}
            
        # Extração do texto
        candidates = result.get('candidates', [])
        if candidates:
            texto = candidates[0].get('content', {}).get('parts', [{}])[0].get('text', 'Sem resposta.')
            return {"resposta": texto}
        else:
            return {"resposta": "Erro: O Google não gerou resposta. Verifique seu crédito no Cloud Console."}
            
    except Exception as e:
        return {"resposta": f"Erro técnico: {str(e)}"}
