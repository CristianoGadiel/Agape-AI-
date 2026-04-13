import os
import google.generativeai as genai
from fastapi import FastAPI, Request
from fastapi.responses import FileResponse

# Agora o código busca a chave de forma segura no servidor
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

if GOOGLE_API_KEY:
    genai.configure(api_key=GOOGLE_API_KEY)
    model = genai.GenerativeModel('gemini-1.5-flash')
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
        return {"resposta": "Erro: Chave API não configurada no servidor Vercel."}
    
    try:
        response = model.generate_content(f"Você é a Ágape V36. Responda: {pergunta}")
        return {"resposta": response.text}
    except Exception as e:
        return {"resposta": f"Erro de conexão: {str(e)}"}

