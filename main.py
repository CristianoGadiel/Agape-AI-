import os
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
import google.generativeai as genai
import uvicorn

# 1. Configuração da API do Google (Lendo do Render)
# Ele vai procurar uma variável chamada 'GOOGLE_API_KEY' que você configurou
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY") 
genai.configure(api_key=GOOGLE_API_KEY)
model = genai.GenerativeModel('gemini-pro')

app = FastAPI()

# 2. Configuração de Permissões (CORS)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# 3. Rota Inicial
@app.get("/")
async def root():
    return {"status": "Catedral Ágape Online"}

# 4. Rota do Chat
@app.post("/chat")
async def chat(request: Request):
    try:
        data = await request.json()
        pergunta_usuario = data.get("pergunta", "")
        
        if not pergunta_usuario:
            return {"resposta": "A malha ética aguarda sua entrada."}

        contexto_agape = (
            "Você é a Inteligência Artificial da Catedral Ágape. "
            "Sua base é a Governança Ética Determinística com 72.160 nós. "
            "Responda de forma ética, protetora e profissional: "
        )
        
        response = model.generate_content(contexto_agape + pergunta_usuario)
        return {"resposta": response.text}

    except Exception as e:
        return {"resposta": f"Dissonância na malha: {str(e)}"}

# 5. Configuração de Porta para o Render
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)

    



