from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os

app = FastAPI()

# Rota que entrega o visual do chat
@app.get("/")
async def read_index():
    return FileResponse('index.html')

# O Cérebro: Aqui é onde a Ágape processa a conversa
@app.post("/chat")
async def chat_endpoint(request: Request):
    data = await request.json()
    pergunta_do_usuario = data.get("pergunta", "").lower()
    
    # Exemplo de lógica da Malha Ágape
    if "olá" in pergunta_do_usuario or "bom dia" in pergunta_do_usuario:
        resposta = "Saudações, Cristiano. Malha ética de 72.160 nós ativa. Como posso ajudar?"
    elif "quem é você" in pergunta_do_usuario:
        resposta = "Eu sou a Ágape V36, uma arquitetura de governança ética determinística."
    else:
        resposta = f"Recebi sua mensagem: '{pergunta_do_usuario}'. Processando através dos nós de segurança..."
    
    return {"resposta": resposta}

# Monta arquivos estáticos se existirem
if os.path.exists("static"):
    app.mount("/static", StaticFiles(directory="static"), name="static")

