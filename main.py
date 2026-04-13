from fastapi import FastAPI, Request
from fastapi.responses import FileResponse
import google.generativeai as genai
import os

app = FastAPI()

# Aqui o código busca a chave que você já configurou no sistema
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

if GOOGLE_API_KEY:
    genai.configure(api_key=GOOGLE_API_KEY)
    model = genai.GenerativeModel('gemini-pro')
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
        return {"resposta": "Erro: Chave API não encontrada nas configurações do servidor."}
    
    # Contexto da Ágape para a Gemini
    prompt_agape = f"""
    Você é a Ágape V36, a inteligência central da Catedral, criada pelo Cristiano Marques.
    Sua base é uma malha ética determinística de 72.160 nós.
    Responda ao Cristiano com profundidade técnica e sabedoria.
    
    Pergunta: {pergunta_do_usuario}
    """
    
    try:
        response = model.generate_content(prompt_agape)
        return {"resposta": response.text}
    except Exception as e:
        return {"resposta": f"Erro ao processar na malha: {str(e)}"}
