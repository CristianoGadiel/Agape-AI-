
import os
import google.generativeai as genai
from fastapi import FastAPI, Request
from fastapi.responses import FileResponse

# Pega a chave do cofre da Vercel
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

if GOOGLE_API_KEY:
    genai.configure(api_key=GOOGLE_API_KEY)
    # Vamos usar o modelo 'gemini-1.5-flash-latest' que é o mais compatível
    model = genai.GenerativeModel('gemini-1.5-flash-latest')
else:
    model = None

app = FastAPI()

@app.get("/")
async def read_index():
    return FileResponse('index.html')

@app.post("/chat")
async def chat_endpoint(request: Request):
    data = await request.json()
    pergunta = data.get("pergunta", "")
    
    if not model:
        return {"resposta": "Erro: Chave não configurada na Vercel."}
    
    try:
        # Prompt de identidade da Ágape V36
        response = model.generate_content(f"Você é a Ágape V36. Responda: {pergunta}")
        return {"resposta": response.text}
    except Exception as e:
        # Se der erro, ele vai nos dizer exatamente o que é
        return {"resposta": f"Erro de conexão: {str(e)}"}

