import os
import google.generativeai as genai
from fastapi import FastAPI, Request
from fastapi.responses import FileResponse

# Sua chave real aqui
GOOGLE_API_KEY = "AIzaSyBl9hrXjHRXuf7HFqe_nt3x87LR-yx6DWw"

genai.configure(api_key=GOOGLE_API_KEY)
# Mudança para o modelo 2.0-flash (mais estável)
model = genai.GenerativeModel('gemini-2.0-flash')

app = FastAPI()

@app.get("/")
async def read_index():
    return FileResponse('index.html')

@app.post("/chat")
async def chat_endpoint(request: Request):
    data = await request.json()
    pergunta = data.get("pergunta", "")
    try:
        response = model.generate_content(f"Você é a Ágape V36. Responda: {pergunta}")
        return {"resposta": response.text}
    except Exception as e:
        return {"resposta": f"Erro técnico: {str(e)}"}
