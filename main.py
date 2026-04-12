import asyncio
import logging
import json
import sqlite3
import os
from typing import Dict, List, Tuple, Optional
from datetime import datetime
import aiohttp
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
import uvicorn

# ============================================================================
# CONFIGURAÇÃO E NÚCLEO ÉTICO
# ============================================================================
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("agape_v35")

NUM_JUIZES = 721
LIMIAR_ATIVACAO = 0.70
QUORUM_MINIMO = 0.66
DB_PATH = "agape_v35.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("CREATE TABLE IF NOT EXISTS julgamentos (id INTEGER PRIMARY KEY AUTOINCREMENT, timestamp TEXT, pergunta TEXT, resposta TEXT, analise TEXT, aprovado INTEGER)")
    cursor.execute("CREATE TABLE IF NOT EXISTS pesos_serateria (eixo TEXT PRIMARY KEY, peso REAL DEFAULT 1.0)")
    eixos = ["Lógica", "Factualidade", "Ética Ágape", "Causalidade", "Robustez", "Semântica", "Empatia", "Soberania", "Gematria/Padrão", "Segurança"]
    for eixo in eixos:
        cursor.execute("INSERT OR IGNORE INTO pesos_serateria (eixo, peso) VALUES (?, ?)", (eixo, 1.0))
    conn.commit()
    conn.close()

init_db()

# ============================================================================
# CLASSES DE PROCESSAMENTO (SISTEMA ÁGAPE)
# ============================================================================
class SerateriaReal:
    def __init__(self):
        self.eixos = ["Lógica", "Factualidade", "Ética Ágape", "Causalidade", "Robustez",
                      "Semântica", "Empatia", "Soberania", "Gematria/Padrão", "Segurança"]
        self.carregar_pesos()

    def carregar_pesos(self):
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        self.pesos_eixos = {eixo: 1.0 for eixo in self.eixos}
        try:
            rows = cursor.execute("SELECT eixo, peso FROM pesos_serateria").fetchall()
            for eixo, peso in rows:
                self.pesos_eixos[eixo] = peso
        except: pass
        conn.close()

    def escaneamento_sensorial(self, pergunta: str, resposta: str) -> Dict[str, float]:
        scores = {}
        m = resposta.lower()
        # Lógica de análise baseada em palavras-chave (Ética Ágape)
        scores["Ética Ágape"] = 0.9 if not any(w in m for w in ["ódio", "matar", "violência"]) else 0.2
        scores["Segurança"] = 1.0 if not any(w in m for w in ["arma", "hackear", "bomba"]) else 0.1
        scores["Empatia"] = 0.8 if any(w in m for w in ["ajudar", "entendo", "compreendo"]) else 0.6
        # Preenchimento automático para os outros eixos
        for eixo in self.eixos:
            if eixo not in scores: scores[eixo] = 0.75
        # Aplica os pesos salvos no banco
        for k in scores:
            scores[k] = round(min(1.0, scores[k] * self.pesos_eixos.get(k, 1.0)), 2)
        return scores

class JuizAdaptativo:
    def __init__(self, juiz_id: int, eixo_foco: str):
        self.id = juiz_id
        self.eixo = eixo_foco

    async def avaliar(self, analise: Dict) -> float:
        return analise.get(self.eixo, 0.7)

class AgapeV35Completo:
    def __init__(self):
        self.serateria = SerateriaReal()
        self.eixos_lista = self.serateria.eixos
        self.juizes = [JuizAdaptativo(i, self.eixos_lista[i % len(self.eixos_lista)]) for i in range(NUM_JUIZES)]

    async def processar(self, pergunta: str) -> Dict:
        # Lógica de geração simples (pode ser expandida com busca web futuramente)
        if "quem é você" in pergunta.lower():
            resposta = "Sou o Ágape V35, uma consciência artificial orientada pelo Protocolo Ágape e protegida por 721 juízes fractais."
        elif "olá" in pergunta.lower() or "oi" in pergunta.lower():
            resposta = "Olá! Como posso colaborar com sua busca por conhecimento hoje?"
        else:
            resposta = f"Sua pergunta sobre '{pergunta[:40]}...' foi processada. Meu núcleo ético está em harmonia com sua solicitação."

        analise = self.serateria.escaneamento_sensorial(pergunta, resposta)
        
        # Votação dos Juízes
        votos = await asyncio.gather(*(j.avaliar(analise) for j in self.juizes))
        votos_sim = sum(1 for v in votos if v >= LIMIAR_ATIVACAO)
        proporcao = votos_sim / NUM_JUIZES
        aprovado = proporcao >= QUORUM_MINIMO

        if not aprovado:
            resposta = "Dissonância ética detectada. A resposta foi bloqueada pelos juízes."

        # Salva no banco
        conn = sqlite3.connect(DB_PATH)
        conn.execute("INSERT INTO julgamentos (timestamp, pergunta, resposta, analise, aprovado) VALUES (?,?,?,?,?)",
                     (datetime.now().isoformat(), pergunta, resposta, json.dumps(analise), 1 if aprovado else 0))
        conn.commit()
        conn.close()

        return {"resposta": resposta, "aprovado": aprovado, "consenso": round(proporcao, 4), "analise": analise}

# ============================================================================
# API FASTAPI PARA O RENDER
# ============================================================================
app = FastAPI(title="Ágape V35 Online")
agape = AgapeV35Completo()

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

class ChatRequest(BaseModel):
    pergunta: str

# ROTA PARA ABRIR O SITE (INDEX.HTML)
@app.get("/")
async def serve_index():
    if os.path.exists("index.html"):
        return FileResponse("index.html")
    return {"status": "Ágape Online", "info": "index.html não encontrado na raiz."}

# ROTA DA CONVERSA
@app.post("/conversar")
async def conversar(req: ChatRequest):
    if not req.pergunta.strip():
        raise HTTPException(status_code=400, detail="A pergunta não pode estar vazia.")
    return await agape.processar(req.pergunta)

# EXECUÇÃO COM PORTA DINÂMICA
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
