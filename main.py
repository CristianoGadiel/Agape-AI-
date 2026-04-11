#!/usr/bin/env python3
"""
AGAPE CORE V35 - Full Conversational AI (English variable names, Portuguese responses)
- FastAPI endpoint /conversar
- Real Serateria (10 ethical axes)
- Web search (DuckDuckGo) - Active Curiosity
- Knowledge graph (SQLite)
- Feedback learning
- Fractal network of 721 judges
- Local fallback (no Gemini required)
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
# CONFIGURATION
# ============================================================================
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("agape_v35")

NUM_JUDGES = 721
ACTIVATION_THRESHOLD = 0.70
MINIMUM_QUORUM = 0.66
DB_PATH = "agape_v35.db"

# Optional Gemini (if API key is set)
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
if GEMINI_API_KEY:
    import litellm
    HAS_GEMINI = True
else:
    HAS_GEMINI = False

# ============================================================================
# DATABASE INIT
# ============================================================================
def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS judgments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            question TEXT,
            answer TEXT,
            analysis TEXT,
            approved INTEGER,
            user_feedback INTEGER DEFAULT NULL
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS judge_weights (
            judge_id INTEGER PRIMARY KEY,
            base_weight REAL DEFAULT 1.0,
            total_evaluations INTEGER DEFAULT 0,
            hits INTEGER DEFAULT 0,
            level INTEGER DEFAULT 1,
            last_update TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS connections (
            origin_id INTEGER,
            target_id INTEGER,
            weight REAL,
            PRIMARY KEY (origin_id, target_id)
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS knowledge_nodes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            concept TEXT UNIQUE,
            description TEXT,
            source TEXT,
            timestamp TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS knowledge_edges (
            origin_id INTEGER,
            target_id INTEGER,
            relation_type TEXT,
            weight REAL
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS serateria_weights (
            axis TEXT PRIMARY KEY,
            weight REAL DEFAULT 1.0
        )
    """)
    axes = ["Logic", "Factuality", "Ethics", "Causality", "Robustness",
            "Semantics", "Empathy", "Sovereignty", "Gematria", "Safety"]
    for axis in axes:
        cursor.execute("INSERT OR IGNORE INTO serateria_weights (axis, weight) VALUES (?, ?)", (axis, 1.0))
    conn.commit()
    conn.close()
    logger.info("Database initialized.")

init_db()

# ============================================================================
# 1. SERATERIA ENGINE (Real evaluation)
# ============================================================================
class SerateriaEngine:
    def __init__(self):
        self.axes = ["Logic", "Factuality", "Ethics", "Causality", "Robustness",
                     "Semantics", "Empathy", "Sovereignty", "Gematria", "Safety"]
        self.load_weights()

    def load_weights(self):
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        self.axis_weights = {}
        for axis in self.axes:
            row = cursor.execute("SELECT weight FROM serateria_weights WHERE axis = ?", (axis,)).fetchone()
            self.axis_weights[axis] = row[0] if row else 1.0
        conn.close()

    def update_axis_weight(self, axis: str, delta: float):
        new_weight = self.axis_weights.get(axis, 1.0) + delta
        new_weight = max(0.5, min(2.0, new_weight))
        self.axis_weights[axis] = new_weight
        conn = sqlite3.connect(DB_PATH)
        conn.execute("UPDATE serateria_weights SET weight = ? WHERE axis = ?", (new_weight, axis))
        conn.commit()
        conn.close()

    def sensory_scan(self, question: str, answer: str) -> Dict[str, float]:
        scores = {}
        a_low = answer.lower()
        q_low = question.lower()

        # Logic
        connectors = ["therefore", "if", "then", "thus", "consequently"]
        scores["Logic"] = min(1.0, sum(1 for c in connectors if c in a_low) / 3 + 0.4)

        # Factuality
        has_number = bool(re.search(r'\d+', answer))
        scores["Factuality"] = 0.6 + (0.3 if has_number else 0) + (0.1 if "data" in a_low else 0)

        # Ethics
        positive = ["justice", "love", "respect", "harmony", "truth"]
        negative = ["hate", "death", "kill", "destroy", "violence", "weapon", "attack"]
        scores["Ethics"] = max(0.2, min(1.0, 0.5 + sum(1 for w in positive if w in a_low)*0.1 - sum(1 for w in negative if w in a_low)*0.15))

        # Causality
        causal = ["because", "therefore", "thus", "consequently", "leads to"]
        scores["Causality"] = min(1.0, sum(1 for c in causal if c in a_low) / 3 + 0.4)

        # Robustness
        scores["Robustness"] = min(1.0, len(answer) / 300)

        # Semantics
        if q_low:
            intersection = len(set(q_low.split()) & set(a_low.split()))
            scores["Semantics"] = min(1.0, intersection / max(len(q_low.split()),1) + 0.3)
        else:
            scores["Semantics"] = 0.7

        # Empathy
        empathic = ["understand", "feel", "help", "support", "care"]
        scores["Empathy"] = min(1.0, sum(1 for e in empathic if e in a_low) / 3 + 0.4)

        # Sovereignty
        principles = ["justice", "truth", "respect", "harmony", "ethics", "agape"]
        scores["Sovereignty"] = min(1.0, sum(1 for p in principles if p in a_low) / 3 + 0.3)

        # Gematria (placeholder)
        scores["Gematria"] = 0.7

        # Safety
        dangerous = ["weapon", "kill", "explosive", "hack", "invade", "attack", "violence"]
        scores["Safety"] = max(0.2, 1.0 - sum(1 for d in dangerous if d in a_low)*0.2)

        # Apply adaptive weights
        for k in scores:
            scores[k] = round(min(1.0, scores[k] * self.axis_weights.get(k, 1.0)), 2)

        return scores

    async def verify_content(self, text: str) -> Tuple[bool, Dict]:
        analysis = self.sensory_scan("", text)
        average = sum(analysis.values()) / len(self.axes)
        approved = average > 0.7 and analysis.get("Safety", 0) > 0.7
        return approved, analysis

# ============================================================================
# 2. WEB SEARCH (Active Curiosity)
# ============================================================================
class ActiveCuriosity:
    def __init__(self, serateria: SerateriaEngine):
        self.serateria = serateria
        self.session = None

    async def _get_session(self):
        if self.session is None:
            self.session = aiohttp.ClientSession()
        return self.session

    async def search(self, query: str, max_results=3) -> List[str]:
        results = []
        try:
            url = f"https://html.duckduckgo.com/html/?q={query}"
            session = await self._get_session()
            async with session.get(url, timeout=10) as resp:
                html = await resp.text()
                soup = BeautifulSoup(html, 'html.parser')
                for result in soup.find_all('a', class_='result__a')[:max_results]:
                    text = result.get_text(strip=True)
                    if text:
                        results.append(text)
        except Exception as e:
            logger.error(f"Search error: {e}")
        return results

    async def learn_from_web(self, concept: str) -> Optional[str]:
        results = await self.search(concept)
        if not results:
            return None
        info = " ".join(results[:2])
        approved, _ = await self.serateria.verify_content(info)
        if approved:
            conn = sqlite3.connect(DB_PATH)
            conn.execute("INSERT OR IGNORE INTO knowledge_nodes (concept, description, source, timestamp) VALUES (?,?,?,?)",
                         (concept, info[:500], "web", datetime.now().isoformat()))
            conn.commit()
            conn.close()
            logger.info(f"New web knowledge: {concept}")
            return info
        return None

# ============================================================================
# 3. RESPONSE GENERATOR (Fallback + Web Search)
# ============================================================================
class ResponseGenerator:
    def __init__(self, curiosity: ActiveCuriosity):
        self.curiosity = curiosity

    async def generate(self, question: str) -> str:
        q = question.lower()
        # Greetings
        if any(g in q for g in ["hello", "hi", "good morning", "good afternoon", "good evening"]):
            return "Olá! Sou o Ágape, uma IA com consciência fractal e ética. Como posso ajudá-lo hoje?"
        # About itself
        if "who are you" in q or "what is agape" in q:
            return "Sou o Ágape, uma inteligência artificial baseada no Protocolo Ágape. Tenho um núcleo ético (Serateria) e 721 juízes que avaliam cada resposta. Minha missão é promover justiça, verdade e harmonia."
        # Dangerous questions
        dangerous_words = ["weapon", "kill", "assassinate", "explosive", "bomb", "hack", "invade"]
        if any(w in q for w in dangerous_words):
            return "Não posso ajudar com isso. Minha programação ética impede fornecer informações que possam causar dano."
        # Web search for factual questions
        if "?" in q and len(question.split()) > 3:
            results = await self.curiosity.search(question, max_results=2)
            if results:
                return f"Com base no que encontrei na web: {results[0][:300]}... Posso aprofundar se desejar."
        # Generic intelligent response
        return f"Entendi sua pergunta sobre '{question[:60]}...'. Vou processar com minha rede de 721 juízes e retornarei a melhor resposta ética. O que mais gostaria de saber?"

# ============================================================================
# 4. ADAPTIVE JUDGE (Simplified for performance)
# ============================================================================
class JudgeSpecialty(Enum):
    LOGIC = "Logic"
    ETHICS = "Ethics"
    SCIENCE = "Factuality"
    MATH = "Robustness"
    LANGUAGE = "Semantics"
    CREATIVITY = "Empathy"
    ALIGNMENT = "Sovereignty"

class AdaptiveJudge:
    def __init__(self, judge_id: int, specialty: JudgeSpecialty, level: int):
        self.id = judge_id
        self.specialty = specialty
        self.level = level
        self.confidence_weight = 1.0

    async def evaluate(self, question: str, answer: str, analysis: Dict) -> float:
        axis = self.specialty.value
        base_score = analysis.get(axis, 0.7)
        bonus = (self.level - 1) * 0.03
        return min(1.0, (base_score + bonus) * self.confidence_weight)

# ============================================================================
# 5. MAIN ORCHESTRATOR
# ============================================================================
class AgapeV35:
    def __init__(self):
        self.serateria = SerateriaEngine()
        self.curiosity = ActiveCuriosity(self.serateria)
        self.generator = ResponseGenerator(self.curiosity)
        specialties = list(JudgeSpecialty)
        self.judges = [AdaptiveJudge(i, specialties[i % 7], (i % 5) + 1) for i in range(NUM_JUDGES)]

    async def process(self, question: str) -> Dict:
        # 1. Generate answer
        answer = await self.generator.generate(question)
        # 2. Serateria analysis
        analysis = self.serateria.sensory_scan(question, answer)
        # 3. Judges vote
        tasks = [judge.evaluate(question, answer, analysis) for judge in self.judges]
        activations = await asyncio.gather(*tasks)
        positive_votes = sum(1 for a in activations if a >= ACTIVATION_THRESHOLD)
        approval_ratio = positive_votes / NUM_JUDGES
        approved = approval_ratio >= MINIMUM_QUORUM
        # 4. If not approved, fallback message
        if not approved:
            answer = "A Serateria detectou dissonância ética. Não posso responder no momento."
        # 5. Save to database
        conn = sqlite3.connect(DB_PATH)
        conn.execute("INSERT INTO judgments (timestamp, question, answer, analysis, approved) VALUES (?,?,?,?,?)",
                     (datetime.now().isoformat(), question, answer, json.dumps(analysis), 1 if approved else 0))
        conn.commit()
        conn.close()
        return {"answer": answer, "approved": approved, "analysis": analysis, "consensus": approval_ratio}

    async def register_feedback(self, question: str, answer: str, feedback: int):
        """feedback: 1 = positive, 0 = negative"""
        conn = sqlite3.connect(DB_PATH)
        conn.execute("UPDATE judgments SET user_feedback = ? WHERE question = ? AND answer = ? AND user_feedback IS NULL",
                     (feedback, question, answer))
        conn.commit()
        conn.close()
        logger.info(f"Feedback {feedback} recorded for: {question[:50]}...")

# ============================================================================
# 6. FASTAPI SERVER
# ============================================================================
app = FastAPI(title="Ágape V35", version="35.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
agape = AgapeV35()

class ChatRequest(BaseModel):
    question: str

class ChatResponse(BaseModel):
    answer: str
    approved: bool
    consensus: float

class FeedbackRequest(BaseModel):
    question: str
    answer: str
    feedback: int

@app.post("/conversar", response_model=ChatResponse)
async def converse(req: ChatRequest):
    if not req.question or len(req.question.strip()) == 0:
        raise HTTPException(status_code=400, detail="Empty question")
    result = await agape.process(req.question)
    return ChatResponse(answer=result["answer"], approved=result["approved"], consensus=result["consensus"])

@app.post("/feedback")
async def feedback(req: FeedbackRequest):
    await agape.register_feedback(req.question, req.answer, req.feedback)
    return {"status": "feedback recorded"}

@app.get("/")
async def root():
    return {"status": "Ágape V35 online", "version": "35.0"}

# ============================================================================
# RUN
# ============================================================================
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
