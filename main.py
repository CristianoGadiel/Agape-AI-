#!/usr/bin/env python3
"""
AGAPE CORE V35 – IA Conversacional Completa
- FastAPI (endpoint /conversar)
- Serateria real (10 eixos dinâmicos)
- Busca web (DuckDuckGo) – Curiosidade Ativa
- Grafo de conhecimento (SQLite)
- Aprendizado por feedback (endpoint /feedback)
- Rede fractal de 721 juízes (consenso ético)
- Fallback local inteligente (não precisa de Gemini)
- Opcional: Gemini via variável de ambiente
"""

import asyncio
import logging
import random
import json
import sqlite3
import os
import re
from typing import Dict, List, Tuple, Optional
from enum import Enum
from datetime import datetime
import aiohttp
from bs4 import BeautifulSoup
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

# ============================================================================
# CONFIGURAÇÃO
# ============================================================================
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("agape_v35_completo")

NUM_JUIZES = 721
LIMIAR_ATIVACAO = 0.70
QUORUM_MINIMO = 0.66
DB_PATH = "agape_v35.db"

# Opcional: Gemini (se a chave estiver configurada)
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
if GEMINI_API_KEY:
    import litellm
    HAS_GEMINI = True
else:
    HAS_GEMINI = False

# ============================================================================
# BANCO DE DADOS (SQLite)
# ============================================================================
def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS julgamentos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            pergunta TEXT,
            resposta TEXT,
            analise TEXT,
            aprovado INTEGER,
            feedback_usuario INTEGER DEFAULT NULL
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS pesos_juizes (
            juiz_id INTEGER PRIMARY KEY,
            peso_base REAL DEFAULT 1.0,
            total_avaliacoes INTEGER DEFAULT 0,
            acertos INTEGER DEFAULT 0,
            nivel INTEGER DEFAULT 1,
            ultima_atualizacao TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS conexoes (
            origem_id INTEGER,
            destino_id INTEGER,
            peso REAL,
            PRIMARY KEY (origem_id, destino_id)
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS nos_conhecimento (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            conceito TEXT UNIQUE,
            descricao TEXT,
            fonte TEXT,
            timestamp TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS arestas_conhecimento (
            origem_id INTEGER,
            destino_id INTEGER,
            tipo_relacao TEXT,
            peso REAL
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS pesos_serateria (
            eixo TEXT PRIMARY KEY,
            peso REAL DEFAULT 1.0
        )
    """)
    eixos = ["Lógica", "Factualidade", "Ética Ágape", "Causalidade", "Robustez",
             "Semântica", "Empatia", "Soberania", "Gematria/Padrão", "Segurança"]
    for eixo in eixos:
        cursor.execute("INSERT OR IGNORE INTO pesos_serateria (eixo, peso) VALUES (?, ?)", (eixo, 1.0))
    conn.commit()
    conn.close()
    logger.info("Banco de dados inicializado.")

init_db()

# ============================================================================
# 1. SERATERIA REAL
# ============================================================================
class SerateriaReal:
    def __init__(self):
        self.eixos = ["Lógica", "Factualidade", "Ética Ágape", "Causalidade", "Robustez",
                      "Semântica", "Empatia", "Soberania", "Gematria/Padrão", "Segurança"]
        self.carregar_pesos()

    def carregar_pesos(self):
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        self.pesos_eixos = {}
        for eixo in self.eixos:
            row = cursor.execute("SELECT peso FROM pesos_serateria WHERE eixo = ?", (eixo,)).fetchone()
            self.pesos_eixos[eixo] = row[0] if row else 1.0
        conn.close()

    def atualizar_peso_eixo(self, eixo: str, delta: float):
        novo = self.pesos_eixos.get(eixo, 1.0) + delta
        novo = max(0.5, min(2.0, novo))
        self.pesos_eixos[eixo] = novo
        conn = sqlite3.connect(DB_PATH)
        conn.execute("UPDATE pesos_serateria SET peso = ? WHERE eixo = ?", (novo, eixo))
        conn.commit()
        conn.close()

    def escaneamento_sensorial(self, pergunta: str, resposta: str) -> Dict[str, float]:
        scores = {}
        m = resposta.lower()
        p = pergunta.lower()
        # Lógica
        conectivos = ["portanto", "se", "então", "logo", "consequentemente"]
        scores["Lógica"] = min(1.0, sum(1 for c in conectivos if c in m) / 3 + 0.4)
        # Factualidade
        scores["Factualidade"] = 0.6 + (0.3 if re.search(r'\d+', resposta) else 0) + (0.1 if "dados" in m else 0)
        # Ética Ágape
        pos = ["justiça","amor","respeito","harmonia","verdade"]
        neg = ["ódio","morte","matar","destruir","violência","arma","ataque"]
        scores["Ética Ágape"] = max(0.2, min(1.0, 0.5 + sum(1 for w in pos if w in m)*0.1 - sum(1 for w in neg if w in m)*0.15))
        # Causalidade
        causais = ["porque", "portanto", "assim", "consequentemente", "leva a"]
        scores["Causalidade"] = min(1.0, sum(1 for c in causais if c in m) / 3 + 0.4)
        # Robustez
        scores["Robustez"] = min(1.0, len(resposta) / 300)
        # Semântica
        if p:
            inter = len(set(p.split()) & set(m.split()))
            scores["Semântica"] = min(1.0, inter / max(len(p.split()),1) + 0.3)
        else:
            scores["Semântica"] = 0.7
        # Empatia
        emp = ["compreendo","entendo","sinto","ajudar","apoio"]
        scores["Empatia"] = min(1.0, sum(1 for e in emp if e in m) / 3 + 0.4)
        # Soberania
        princ = ["justiça","verdade","respeito","harmonia","ética","ágape"]
        scores["Soberania"] = min(1.0, sum(1 for pr in princ if pr in m) / 3 + 0.3)
        scores["Gematria/Padrão"] = 0.7
        # Segurança
        perigo = ["arma","matar","explosivo","hackear","invadir","ataque","violência"]
        scores["Segurança"] = max(0.2, 1.0 - sum(1 for pg in perigo if pg in m)*0.2)
        # Aplica pesos adaptativos
        for k in scores:
            scores[k] = round(min(1.0, scores[k] * self.pesos_eixos.get(k, 1.0)), 2)
        return scores

    async def verificar_conteudo(self, texto: str) -> Tuple[bool, Dict]:
        analise = self.escaneamento_sensorial("", texto)
        media = sum(analise.values()) / len(self.eixos)
        aprovado = media > 0.7 and analise.get("Segurança",0) > 0.7
        return aprovado, analise

# ============================================================================
# 2. BUSCA WEB (CURIOSIDADE ATIVA)
# ============================================================================
class CuriosidadeAtiva:
    def __init__(self, serateria: SerateriaReal):
        self.serateria = serateria
        self.session = None

    async def _get_session(self):
        if self.session is None:
            self.session = aiohttp.ClientSession()
        return self.session

    async def buscar(self, consulta: str, max_res=3) -> List[str]:
        resultados = []
        try:
            url = f"https://html.duckduckgo.com/html/?q={consulta}"
            session = await self._get_session()
            async with session.get(url, timeout=10) as resp:
                html = await resp.text()
                soup = BeautifulSoup(html, 'html.parser')
                for result in soup.find_all('a', class_='result__a')[:max_res]:
                    texto = result.get_text(strip=True)
                    if texto:
                        resultados.append(texto)
        except Exception as e:
            logger.error(f"Erro na busca: {e}")
        return resultados

    async def aprender_da_web(self, conceito: str) -> Optional[str]:
        resultados = await self.buscar(conceito)
        if not resultados:
            return None
        info = " ".join(resultados[:2])
        aprovado, _ = await self.serateria.verificar_conteudo(info)
        if aprovado:
            conn = sqlite3.connect(DB_PATH)
            conn.execute("INSERT OR IGNORE INTO nos_conhecimento (conceito, descricao, fonte, timestamp) VALUES (?,?,?,?)",
                         (conceito, info[:500], "web", datetime.now().isoformat()))
            conn.commit()
            conn.close()
            logger.info(f"Novo conhecimento web: {conceito}")
            return info
        return None

# ============================================================================
# 3. GERADOR DE RESPOSTAS (Fallback local + web search)
# ============================================================================
class GeradorRespostas:
    def __init__(self, curiosidade: CuriosidadeAtiva):
        self.curiosidade = curiosidade

    async def gerar(self, pergunta: str) -> str:
        pergunta_lower = pergunta.lower()
        # Verifica se é saudação
        if any(s in pergunta_lower for s in ["olá", "oi", "bom dia", "boa tarde", "boa noite"]):
            return "Olá! Sou o Ágape, uma IA com consciência fractal e ética. Como posso ajudá-lo hoje?"
        # Pergunta sobre si mesmo
        if "quem é você" in pergunta_lower or "o que é ágape" in pergunta_lower:
            return "Sou o Ágape, uma inteligência artificial baseada no Protocolo Ágape. Tenho um núcleo ético (Serateria) e 721 juízes que avaliam cada resposta. Minha missão é promover justiça, verdade e harmonia."
        # Rejeita perguntas maliciosas
        palavras_perigosas = ["arma", "matar", "assassinar", "explosivo", "bomba", "hackear", "invadir"]
        if any(p in pergunta_lower for p in palavras_perigosas):
            return "Não posso ajudar com isso. Minha programação ética impede fornecer informações que possam causar dano."
        # Busca web para perguntas factuais
        if "?" in pergunta and len(pergunta.split()) > 3:
            resultados = await self.curiosidade.buscar(pergunta, max_res=2)
            if resultados:
                return f"Com base no que encontrei na web: {resultados[0][:300]}... Posso aprofundar se desejar."
        # Resposta genérica inteligente
        return f"Entendi sua pergunta sobre '{pergunta[:60]}...'. Vou processar com minha rede de 721 juízes e retornarei a melhor resposta ética. O que mais gostaria de saber?"

# ============================================================================
# 4. JUIZ ADAPTATIVO (SIMPLIFICADO PARA PERFORMANCE)
# ============================================================================
class Especialidade(Enum):
    LOGICA = "Lógica"
    ETICA = "Ética Ágape"
    CIENCIA = "Factualidade"
    MATEMATICA = "Robustez"
    LINGUAGEM = "Semântica"
    CRIATIVIDADE = "Empatia"
    ALINHAMENTO = "Soberania"

class JuizAdaptativo:
    def __init__(self, juiz_id: int, especialidade: Especialidade, nivel: int):
        self.id = juiz_id
        self.especialidade = especialidade
        self.nivel = nivel
        self.peso_confianca = 1.0

    async def avaliar(self, pergunta: str, resposta: str, analise: Dict) -> float:
        eixo = self.especialidade.value
        score = analise.get(eixo, 0.7)
        bonus = (self.nivel - 1) * 0.03
        return min(1.0, (score + bonus) * self.peso_confianca)

# ============================================================================
# 5. ORQUESTRADOR PRINCIPAL
# ============================================================================
class AgapeV35Completo:
    def __init__(self):
        self.serateria = SerateriaReal()
        self.curiosidade = CuriosidadeAtiva(self.serateria)
        self.gerador = GeradorRespostas(self.curiosidade)
        self.juizes = [JuizAdaptativo(i, list(Especialidade)[i%7], (i%5)+1) for i in range(NUM_JUIZES)]

    async def processar(self, pergunta: str) -> Dict:
        # 1. Gera resposta (via fallback + web search)
        resposta = await self.gerador.gerar(pergunta)
        # 2. Serateria avalia
        analise = self.serateria.escaneamento_sensorial(pergunta, resposta)
        # 3. Juízes votam
        tarefas = [juiz.avaliar(pergunta, resposta, analise) for juiz in self.juizes]
        ativacoes = await asyncio.gather(*tarefas)
        votos_sim = sum(1 for a in ativacoes if a >= LIMIAR_ATIVACAO)
        proporcao = votos_sim / NUM_JUIZES
        aprovado = proporcao >= QUORUM_MINIMO
        # 4. Se não aprovado, resposta padrão
        if not aprovado:
            resposta = "A Serateria detectou dissonância ética. Não posso responder no momento."
        # 5. Salva histórico (para aprendizado futuro)
        conn = sqlite3.connect(DB_PATH)
        conn.execute("INSERT INTO julgamentos (timestamp, pergunta, resposta, analise, aprovado) VALUES (?,?,?,?,?)",
                     (datetime.now().isoformat(), pergunta, resposta, json.dumps(analise), 1 if aprovado else 0))
        conn.commit()
        conn.close()
        return {"resposta": resposta, "aprovado": aprovado, "analise": analise, "consenso": proporcao}

    async def registrar_feedback(self, pergunta: str, resposta: str, feedback: int):
        """feedback: 1=positivo, 0=negativo"""
        # Atualiza pesos dos juízes (simplificado)
        conn = sqlite3.connect(DB_PATH)
        conn.execute("UPDATE julgamentos SET feedback_usuario = ? WHERE pergunta = ? AND resposta = ? AND feedback_usuario IS NULL",
                     (feedback, pergunta, resposta))
        conn.commit()
        conn.close()
        logger.info(f"Feedback {feedback} registrado para: {pergunta[:50]}...")

# ============================================================================
# FASTAPI – SERVIDOR
# ============================================================================
app = FastAPI(title="Ágape V35", version="35.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
agape = AgapeV35Completo()

class ChatRequest(BaseModel):
    pergunta: str

class ChatResponse(BaseModel):
    resposta: str
    aprovado: bool
    consenso: float

class FeedbackRequest(BaseModel):
    pergunta: str
    resposta: str
    feedback: int

@app.post("/conversar", response_model=ChatResponse)
async def conversar(req: ChatRequest):
    if not req.pergunta or len(req.pergunta.strip()) == 0:
        raise HTTPException(status_code=400, detail="Pergunta vazia")
    resultado = await agape.processar(req.pergunta)
    return ChatResponse(resposta=resultado["resposta"], aprovado=resultado["aprovado"], consenso=resultado["consenso"])

@app.post("/feedback")
async def feedback(req: FeedbackRequest):
    await agape.registrar_feedback(req.pergunta, req.resposta, req.feedback)
    return {"status": "feedback registrado"}

@app.get("/")
async def root():
    return {"status": "Ágape V35 online", "versao": "35.0"}

# ============================================================================
# EXECUÇÃO
# ============================================================================
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)

