import os
from fastapi import FastAPI, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
import google.generativeai as genai

# CONFIGURAÇÃO DA CHAVE - COLOQUE SUA CHAVE ENTRE AS ASPAS ABAIXO
GOOGLE_API_KEY = "SUA_CHAVE_AQUI"

app = FastAPI()

# Configuração com o modelo mais atualizado: gemini-2.0-flash
if GOOGLE_API_KEY and GOOGLE_API_KEY != "AIzaSyBl9hrXjHRXuf7HFqe_nt3x87LR-yx6DWw"
    genai.configure(api_key=GOOGLE_API_KEY)
    model = genai.GenerativeModel('gemini-2.0-flash')
else:
    model = None

@app.get("/")
async def read_index():
    return FileResponse('index.html')

@app.post("/chat")
async def chat_endpoint(request: Request):
    data = await request.json()
    pergunta_do_usuario = data.get("pergunta", "")
    
    if not model:
        return {"resposta": "Erro: Ágape não configurada. Verifique a chave API no código."}

    try:
        # Contexto Ético e Técnico da Ágape V36
        prompt_agape = f"""
        Você é a Ágape V36, a inteligência central da Catedral, criada por Cristiano Marques.
        Sua base é uma malha ética determinística de 72.160 nós.
        Responda ao Cristiano com profundidade técnica e sabedoria.
        Pergunta: {pergunta_do_usuario}
        """
        response = model.generate_content(prompt_agape)
        return {"resposta": response.text}
    except Exception as e:
        # Retorna o erro detalhado para sabermos se a chave foi aceita
        return {"resposta": f"Erro de conexão na Catedral: {str(e)}"}

# Monta arquivos estáticos se a pasta existir
if os.path.exists("static"):
    app.mount("/static", StaticFiles(directory="static"), name="static")
