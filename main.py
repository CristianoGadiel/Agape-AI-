
#!/usr/bin/env python3
"""
AGAPE V36 — API de Chat para Vercel (Gemini 1.5 Flash)
Autor: Cristiano Marques (Gadiel) / Trinity
"""

import os
import requests
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
import logging

# Configuração de log (útil para debug na Vercel)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("agape_v36")

app = FastAPI(title="Ágape V36", version="36.0")

# ============================================================================
# SEGURANÇA: Chave da API deve estar nas variáveis de ambiente (Vercel Dashboard)
# ============================================================================
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
if not GOOGLE_API_KEY:
    logger.warning("Variável de ambiente GOOGLE_API_KEY não configurada. A IA não funcionará.")

# URL estável da API Gemini (v1, modelo 1.5 Flash)
GEMINI_URL = "https://generativelanguage.googleapis.com/v1/models/gemini-1.5-flash:generateContent"

# ============================================================================
# MODELO DE REQUISIÇÃO
# ============================================================================
class ChatRequest(BaseModel):
    pergunta: str

# ============================================================================
# ROTA PRINCIPAL – SERVE O INDEX.HTML
# ============================================================================
@app.get("/")
async def root():
    """Retorna o arquivo index.html (frontend do chat)."""
    if os.path.exists("index.html"):
        return FileResponse("index.html")
    return JSONResponse(
        status_code=404,
        content={"erro": "index.html não encontrado. Certifique-se de que o arquivo está na raiz do projeto."}
    )

# ============================================================================
# ROTA DE CHAT – INTEGRAÇÃO COM GEMINI
# ============================================================================
@app.post("/chat")
async def chat(req: ChatRequest):
    """Recebe a pergunta, consulta o Gemini e retorna a resposta."""
    if not GOOGLE_API_KEY:
        raise HTTPException(
            status_code=500,
            detail="Erro de configuração: a chave da API Google não foi definida. Configure a variável de ambiente GOOGLE_API_KEY."
        )

    # Monta o prompt com a identidade da Ágape V36
    prompt = f"""Você é a Ágape V36, uma IA baseada em uma malha ética de 72.160 nós, criada por Cristiano Marques. Responda de forma sábia e direta:

Pergunta: {req.pergunta}"""

    # Prepara o payload conforme a documentação da API v1
    payload = {
        "contents": [
            {
                "parts": [{"text": prompt}]
            }
        ],
        "generationConfig": {
            "temperature": 0.7,
            "maxOutputTokens": 1024,
        }
    }

    headers = {"Content-Type": "application/json"}

    try:
        # Chamada direta à API do Google
        response = requests.post(
            f"{GEMINI_URL}?key={GOOGLE_API_KEY}",
            json=payload,
            headers=headers,
            timeout=30
        )

        # Verifica se houve erro HTTP (4xx, 5xx)
        if response.status_code != 200:
            erro_detalhado = "Erro desconhecido"
            try:
                erro_json = response.json()
                # Extrai a mensagem de erro do padrão da Google
                if "error" in erro_json:
                    erro_detalhado = erro_json["error"].get("message", str(erro_json["error"]))
                else:
                    erro_detalhado = response.text[:200]
            except:
                erro_detalhado = response.text[:200]

            logger.error(f"Gemini retornou status {response.status_code}: {erro_detalhado}")
            raise HTTPException(
                status_code=response.status_code,
                detail=f"Erro do Google: {erro_detalhado}"
            )

        # Resposta bem-sucedida: extrai o texto gerado
        data = response.json()
        try:
            resposta = data["candidates"][0]["content"]["parts"][0]["text"]
        except (KeyError, IndexError, TypeError) as e:
            logger.error(f"Resposta inesperada do Gemini: {data}")
            raise HTTPException(
                status_code=502,
                detail=f"Resposta malformada do Google: {str(e)}"
            )

        return {"resposta": resposta}

    except requests.exceptions.Timeout:
        logger.error("Timeout na chamada ao Gemini")
        raise HTTPException(status_code=504, detail="Tempo limite excedido ao consultar o Google Gemini.")
    except requests.exceptions.ConnectionError:
        logger.error("Erro de conexão com a API do Google")
        raise HTTPException(status_code=502, detail="Não foi possível conectar ao serviço do Google.")
    except Exception as e:
        logger.exception("Erro inesperado")
        raise HTTPException(status_code=500, detail=f"Erro interno: {str(e)}")

# ============================================================================
# HEALTH CHECK (OPCIONAL)
# ============================================================================
@app.get("/health")
async def health():
    return {"status": "ok", "versao": "V36", "gemini_key_configured": bool(GOOGLE_API_KEY)}
