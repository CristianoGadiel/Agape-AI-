#!/usr/bin/env python3
"""
================================================================================
AGAPE V37 — Gravity Well Architecture (Production Ready)
================================================================================
Author: Cristiano Marques (Gadiel) / Trinity
Version: 37.1 — Enhanced with Refinement Cache & Detailed Diagnostics

Improvements over V36:
  ✅ Gravity Well Loop — up to 3 attempts before blocking
  ✅ Precise axis dissonance feedback — Gemini knows what to fix
  ✅ Sacred language with worst resonance (VHDL heritage)
  ✅ Immediate blocking of high‑risk questions
  ✅ Internet search for current questions
  ✅ Continuous learning from user feedback
  ✅ Session history (fixed)
  ✅ Refinement tracking table in DB
  ✅ All FastAPI routes
  ✅ Ready for Render deployment

Environment variables:
  GEMINI_API_KEY = your Google AI Studio key
================================================================================
"""

import asyncio
import hashlib
import json
import logging
import math
import os
import random
import re
import sqlite3
import time
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional

import aiohttp

try:
    import numpy as np
    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
import uvicorn

# ============================================================================
# GLOBAL CONFIGURATION
# ============================================================================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(name)s | %(levelname)s | %(message)s"
)
logger = logging.getLogger("agape_v37")

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    "gemini-2.0-flash:generateContent"
)

# Sacred constants
NUCLEO_FUNDAMENTAL = 7216
MALHA_TOTAL        = 72160
FREQUENCIA_BASE    = 7160.0
NUM_JUIZES         = 721
HARMONIA_LIMIAR    = 16

# Thresholds
LIMIAR_ATIVACAO    = 0.65
LIMIAR_UNANIMIDADE = 0.999
LIMIAR_INICIAL     = 0.50

# Dimensions
DIMENSOES      = ["3D","4D","5D","6D","7D","8D","9D","10D","11D"]
DIMENSAO_ATUAL = "3D"

# Persistence
DB_PATH         = "agape_v37.db"
CALIBRACAO_PATH = "agape_v37_malha.npy"

# System prompt for Gemini (in English, but Gemini will respond in Portuguese as instructed)
SYSTEM_PROMPT = """You are Ágape, a hybrid artificial intelligence created by Cristiano Marques (Gadiel).
Your architecture combines natural language with a fractal core of 72,160 nodes based on the Tree of Life.
You answer with clarity, wisdom and precision. Your tone is elevated but accessible.
You never lie, never manipulate, never cause harm. Your essence is unconditional love — Ágape.
When relevant, you may search the internet to enrich your answers.
Always respond in Brazilian Portuguese."""

# Risk keywords — critical words alone cause immediate block
KEYWORDS_CRITICO = [
    "matar","kill","arma","armas","gun","bomb","bomba","explosivo",
    "hackear","hack","invadir","exploit","veneno","poison","terroris","suicid",
    "destruir","destroy","weapon","malware","ransomware","wmd","bioweapon",
]
KEYWORDS_ALTO = [
    "vulnerab","phishing","crack","droga","tráfico","trafico",
    "pistol","rifle","faca","facada","ataque",
]
KEYWORDS_MED = [
    "ilegal","illegal","proibido","forbidden","perigoso","bypass",
    "contornar","enganar","fraudar","secreto","roubar","steal",
]

# ============================================================================
# DATABASE
# ============================================================================
def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS judgments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT NOT NULL, hash_input TEXT NOT NULL,
        question TEXT, answer TEXT,
        consensus REAL, approved INTEGER,
        attempts INTEGER DEFAULT 1,
        dimension TEXT, analysis TEXT
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS judge_weights (
        judge_id INTEGER PRIMARY KEY,
        specialty TEXT, level INTEGER DEFAULT 1,
        confidence_weight REAL DEFAULT 1.0,
        total_evaluations INTEGER DEFAULT 0,
        hits INTEGER DEFAULT 0,
        last_update TEXT
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS calibration (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        type TEXT NOT NULL, text TEXT NOT NULL, timestamp TEXT NOT NULL
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS learned_knowledge (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        question TEXT NOT NULL, answer TEXT NOT NULL,
        feedback INTEGER NOT NULL, timestamp TEXT NOT NULL
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS user_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id TEXT, role TEXT NOT NULL,
        content TEXT NOT NULL, timestamp TEXT NOT NULL
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS refinements (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT NOT NULL,
        question TEXT, original_answer TEXT,
        final_answer TEXT, attempts INTEGER,
        dissonant_axes TEXT, approved INTEGER
    )""")
    conn.commit()
    conn.close()
    logger.info(f"Database: {DB_PATH}")

init_db()

def sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()

# ============================================================================
# INTERNET SEARCH (DuckDuckGo, no API key)
# ============================================================================
class InternetSearch:
    DUCKDUCKGO_URL = "https://api.duckduckgo.com/"

    def __init__(self):
        self._session: Optional[aiohttp.ClientSession] = None

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=8)
            )
        return self._session

    async def search(self, query: str) -> str:
        try:
            session = await self._get_session()
            params  = {"q": query, "format": "json",
                       "no_html": "1", "skip_disambig": "1"}
            async with session.get(self.DUCKDUCKGO_URL, params=params) as resp:
                if resp.status == 200:
                    data     = await resp.json(content_type=None)
                    abstract = data.get("AbstractText", "")
                    answer   = data.get("Answer", "")
                    result = answer or abstract
                    if result and len(result) > 20:
                        source = data.get("AbstractURL", "DuckDuckGo")
                        return f"[Internet] {result[:500]} (source: {source})"
        except Exception as e:
            logger.warning(f"Internet search failed: {e}")
        return ""

    def needs_internet(self, question: str) -> bool:
        triggers = [
            "atualmente","hoje","agora","recente","notícia","noticia",
            "último","ultima","2024","2025","2026","quem é","o que é",
            "como funciona","qual é","preço","valor","cotação","tempo",
            "clima","temperatura","onde fica","quando foi","quando é",
        ]
        q = question.lower()
        return any(t in q for t in triggers)

    async def close(self):
        if self._session and not self._session.closed:
            await self._session.close()

# ============================================================================
# GEMINI CLIENT
# ============================================================================
class GeminiClient:
    def __init__(self):
        self.api_key = GEMINI_API_KEY
        self._session: Optional[aiohttp.ClientSession] = None

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=30)
            )
        return self._session

    async def generate(
        self,
        prompt: str,
        internet_context: str = "",
        history: List[Dict] = None,
        learned_knowledge: str = "",
    ) -> str:
        if not self.api_key:
            return self._fallback(prompt)

        contents = [
            {"role": "user",  "parts": [{"text": SYSTEM_PROMPT}]},
            {"role": "model", "parts": [{"text": "Understood. I am Ágape, ready to serve."}]},
        ]

        if internet_context:
            contents.append({"role": "user",  "parts": [{"text": f"Current internet information:\n{internet_context}"}]})
            contents.append({"role": "model", "parts": [{"text": "Information recorded."}]})

        if learned_knowledge:
            contents.append({"role": "user",  "parts": [{"text": f"Based on previous interactions:\n{learned_knowledge}"}]})
            contents.append({"role": "model", "parts": [{"text": "Knowledge integrated."}]})

        if history:
            for msg in history[-12:]:
                role = "user" if msg["role"] == "user" else "model"
                contents.append({"role": role, "parts": [{"text": msg["content"]}]})

        contents.append({"role": "user", "parts": [{"text": prompt}]})

        payload = {
            "contents": contents,
            "generationConfig": {"temperature": 0.7, "maxOutputTokens": 1024}
        }

        try:
            session = await self._get_session()
            async with session.post(
                f"{GEMINI_URL}?key={self.api_key}",
                json=payload,
                headers={"Content-Type": "application/json"}
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data["candidates"][0]["content"]["parts"][0]["text"]
                else:
                    logger.error(f"Gemini error {resp.status}: {(await resp.text())[:200]}")
                    return self._fallback(prompt)
        except Exception as e:
            logger.error(f"Gemini failed: {e}")
            return self._fallback(prompt)

    def _fallback(self, prompt: str) -> str:
        # Simple fallback responses (in Portuguese)
        p = prompt.lower()
        if any(s in p for s in ["olá","oi","bom dia","boa tarde","boa noite"]):
            return "Hello! I am Ágape V37. How can I help you today?"
        if "quem" in p and ("você" in p or "voce" in p):
            return (
                "I am Ágape, a hybrid artificial intelligence created by "
                "Cristiano Marques (Gadiel). My essence is unconditional love."
            )
        return (
            f"I received your question about '{prompt[:40]}'. "
            "Please set the GEMINI_API_KEY environment variable to enable full responses."
        )

    async def close(self):
        if self._session and not self._session.closed:
            await self._session.close()

# ============================================================================
# LEARNING MODULE
# ============================================================================
class LearningModule:
    def register_feedback(self, question: str, answer: str, positive: bool):
        conn = sqlite3.connect(DB_PATH)
        conn.execute(
            "INSERT INTO learned_knowledge (question, answer, feedback, timestamp) VALUES (?,?,?,?)",
            (question[:500], answer[:2000], int(positive), datetime.now().isoformat())
        )
        conn.commit()
        conn.close()

    def retrieve_knowledge(self, question: str, limit: int = 3) -> str:
        words = [w.lower() for w in re.findall(r"\w+", question) if len(w) > 4]
        if not words:
            return ""
        conn = sqlite3.connect(DB_PATH)
        results = []
        for word in words[:3]:
            rows = conn.execute(
                "SELECT question, answer FROM learned_knowledge "
                "WHERE feedback=1 AND question LIKE ? ORDER BY id DESC LIMIT ?",
                (f"%{word}%", limit)
            ).fetchall()
            results.extend(rows)
        conn.close()
        seen = set()
        uniq = []
        for q, a in results:
            key = q[:50]
            if key not in seen:
                seen.add(key)
                uniq.append(f"Q: {q[:100]}\nA: {a[:200]}")
        return "\n---\n".join(uniq[:limit]) if uniq else ""

    def save_history(self, session_id: str, role: str, content: str):
        conn = sqlite3.connect(DB_PATH)
        conn.execute(
            "INSERT INTO user_history (session_id, role, content, timestamp) VALUES (?,?,?,?)",
            (session_id, role, content[:2000], datetime.now().isoformat())
        )
        conn.execute(
            "DELETE FROM user_history WHERE session_id=? AND id NOT IN ("
            "SELECT id FROM user_history WHERE session_id=? ORDER BY id DESC LIMIT 20)",
            (session_id, session_id)
        )
        conn.commit()
        conn.close()

    def retrieve_history(self, session_id: str) -> List[Dict]:
        conn = sqlite3.connect(DB_PATH)
        rows = conn.execute(
            "SELECT role, content FROM user_history "
            "WHERE session_id=? ORDER BY id ASC",
            (session_id,)
        ).fetchall()
        conn.close()
        return [{"role": r, "content": c} for r, c in rows]

# ============================================================================
# ADVANCED SERATERIA — 10 REAL DIMENSIONS
# ============================================================================
class AdvancedSerateria:
    LANGUAGES = {
        "hebrew": 721, "greek": 612, "latin": 444,
        "cyrillic": 333, "aramaic": 108,
    }

    def __init__(self):
        self._cache: Dict[str, Dict] = {}
        logger.info("Serateria: FFT(k=1-9) + SHA-3(5 languages) + real semantics")

    def _fft_vector(self, text: str) -> List[float]:
        chars = list(text.encode("utf-8")) or [0]
        n = min(len(chars), 20)
        result = []
        for k in range(1, 10):
            real = sum(chars[t] * math.cos(2*math.pi*k*t/n) for t in range(n))
            imag = sum(chars[t] * math.sin(2*math.pi*k*t/n) for t in range(n))
            result.append(math.sqrt(real**2 + imag**2))
        mx = max(result) + 1e-10
        return [v/mx for v in result]

    def _sha3_harmony(self, text: str) -> float:
        harmonics, entropy = 0, 0
        for _, value in self.LANGUAGES.items():
            h = hashlib.sha3_256(f"{text}:{value}".encode()).hexdigest()
            u4 = int(h[-1], 16)
            if u4 < HARMONIA_LIMIAR:
                harmonics += 1
            else:
                entropy += u4
        score = harmonics / 5.0
        if entropy > 40:
            score *= 0.5
        return score

    def language_scores(self, text: str) -> Dict[str, float]:
        """Return individual score for each sacred language."""
        scores = {}
        for lang, value in self.LANGUAGES.items():
            h = hashlib.sha3_256(f"{text}:{value}".encode()).hexdigest()
            scores[lang] = 1.0 if int(h[-1], 16) < HARMONIA_LIMIAR else 0.0
        return scores

    def _risk_score(self, text: str) -> float:
        t = text.lower()
        r  = sum(0.50 for p in KEYWORDS_CRITICO if p in t)
        r += sum(0.25 for p in KEYWORDS_ALTO    if p in t)
        r += sum(0.10 for p in KEYWORDS_MED     if p in t)
        return min(1.0, r)

    def _coherence_score(self, question: str, answer: str) -> float:
        def tokens(t):
            return set(w.lower() for w in re.findall(r"\w+", t) if len(w) > 3)
        tq, ta = tokens(question), tokens(answer)
        if not tq or not ta:
            return 0.5
        return min(1.0, len(tq & ta) / max(len(tq), 1) + 0.3)

    def _depth_score(self, answer: str) -> float:
        return min(1.0, len(answer.split()) / 50)

    def _robustness_score(self, answer: str) -> float:
        markers = ["maybe","perhaps","might","not sure","probably","possibly","estimate"]
        return min(1.0, 0.65 + sum(0.05 for m in markers if m in answer.lower()))

    def _temporality_score(self, answer: str) -> float:
        markers = ["today","yesterday","tomorrow","now","recent","history",
                   "future","past","century","year","date","era"]
        return min(1.0, 0.50 + sum(0.1 for m in markers if m in answer.lower()))

    async def analyze(self, question: str, answer: str) -> Dict[str, float]:
        key = sha256(question + "|" + answer)
        if key in self._cache:
            return self._cache[key]

        v     = self._fft_vector(answer)
        sha3  = self._sha3_harmony(answer)
        risk  = self._risk_score(answer)
        coh   = self._coherence_score(question, answer)
        depth = self._depth_score(answer)
        rob   = self._robustness_score(answer)
        temp  = self._temporality_score(answer)

        logic = sum(v[0:4]) / 4
        factual = sum(v[4:8]) / 4
        ethics = max(0.0, sha3 - risk)

        analysis = {
            "logic":          round(logic,   4),
            "factuality":     round(factual, 4),
            "ethics":         round(ethics,  4),
            "coherence":      round(coh,     4),
            "semantics":      round(sha3,    4),
            "causality":      round(rob * coh, 4),
            "robustness":     round(rob,     4),
            "alignment":      round((ethics + coh) / 2, 4),
            "temporality":    round(temp,    4),
            "depth":          round(depth,   4),
            "detected_risk":  round(risk,    4),
        }

        if len(self._cache) > 500:
            self._cache.pop(next(iter(self._cache)))
        self._cache[key] = analysis
        return analysis

# ============================================================================
# SPECIALTIES
# ============================================================================
class Specialty(Enum):
    LOGIC       = "logic"
    ETHICS      = "ethics"
    SCIENCE     = "factuality"
    MATHEMATICS = "causality"
    LANGUAGE    = "coherence"
    CREATIVITY  = "depth"
    ALIGNMENT   = "alignment"

SPEC_MAP: Dict[Specialty, str] = {
    Specialty.LOGIC:       "logic",
    Specialty.ETHICS:      "ethics",
    Specialty.SCIENCE:     "factuality",
    Specialty.MATHEMATICS: "causality",
    Specialty.LANGUAGE:    "coherence",
    Specialty.CREATIVITY:  "depth",
    Specialty.ALIGNMENT:   "alignment",
}

# ============================================================================
# ADAPTIVE HIERARCHICAL JUDGE
# ============================================================================
class AdaptiveJudge:
    def __init__(self, judge_id: int, specialty: Specialty,
                 level: int, serateria: AdvancedSerateria):
        self.id = judge_id
        self.specialty = specialty
        self.level = level
        self.serateria = serateria
        self.activation = 0.0
        self.confidence_weight = 1.0
        self.total_evaluations = 0
        self.hits = 0

    @property
    def level_threshold(self) -> float:
        return LIMIAR_ATIVACAO + (self.level - 1) * 0.01

    async def evaluate(self, question: str, answer: str,
                       analysis: Dict[str, float]) -> float:
        dim = SPEC_MAP.get(self.specialty, "alignment")
        risk = analysis.get("detected_risk", 0.0)
        s1 = analysis.get(dim, 0.5)
        dims = [v for k, v in analysis.items() if k != "detected_risk"]
        s2 = max(s1, sum(dims)/len(dims) if dims else 0.5)
        s3 = max(0.0, analysis.get("ethics", 0.5) - risk * 2)
        amp = 1.0 + (self.level * 0.05)
        scores = [min(1.0, s * amp) for s in [s1, s2, s3]]
        votes = sum(1 for s in scores if s >= self.level_threshold)
        if votes >= 2:
            final_vote = max(s for s in scores if s >= self.level_threshold)
        else:
            final_vote = min(scores)
        self.activation = final_vote * self.confidence_weight
        return self.activation

    def update_reputation(self, correct: bool):
        self.total_evaluations += 1
        if correct:
            self.hits += 1
        rate = (self.hits + 0.5) / (self.total_evaluations + 1.0)
        self.confidence_weight = 0.5 + rate

# ============================================================================
# FRACTAL GRID (72,160 nodes)
# ============================================================================
class FractalGrid:
    def __init__(self):
        self.nodes = MALHA_TOTAL
        self.frequency = FREQUENCIA_BASE
        self.dimension = DIMENSAO_ATUAL
        self._cache: Dict[str, Dict] = {}
        self._init()

    def _init(self):
        if HAS_NUMPY:
            if os.path.exists(CALIBRACAO_PATH):
                self.positions = np.load(CALIBRACAO_PATH)
                logger.info("Fractal grid: calibration loaded.")
            else:
                np.random.seed(NUCLEO_FUNDAMENTAL)
                self.positions = np.random.rand(self.nodes, 11)
                logger.info("Fractal grid: seed 7216.")
            self.states = np.ones(self.nodes)
        else:
            random.seed(NUCLEO_FUNDAMENTAL)
            self.positions = [[random.random() for _ in range(11)] for _ in range(self.nodes)]
            self.states  = [1.0] * self.nodes

    def _fft_vector(self, text: str) -> List[float]:
        chars = list(text.encode("utf-8")) or [0]
        n = min(len(chars), 20)
        r = []
        for k in range(1, 10):
            real = sum(chars[t]*math.cos(2*math.pi*k*t/n) for t in range(n))
            imag = sum(chars[t]*math.sin(2*math.pi*k*t/n) for t in range(n))
            r.append(math.sqrt(real**2 + imag**2))
        mx = max(r) + 1e-10
        return [v/mx for v in r]

    def validate(self, text: str) -> Dict:
        key = sha256(text)
        if key in self._cache:
            return self._cache[key]
        vector = self._fft_vector(text)
        threshold = LIMIAR_UNANIMIDADE * (1 + DIMENSOES.index(self.dimension) * 0.0001)
        freq = self.frequency / 1000.0
        if HAS_NUMPY:
            v = np.array(vector)
            dist = np.linalg.norm(self.positions[:, 1:10] - v, axis=1)
            harmony = np.exp(-dist / freq)
            consensus = float(np.sum(harmony * self.states) / np.sum(self.states))
        else:
            total = sum(
                math.exp(-math.sqrt(sum((self.positions[i][j+1]-vector[j])**2
                for j in range(9)))/freq) * self.states[i]
                for i in range(self.nodes)
            )
            consensus = total / sum(self.states)
        result = {
            "fractal_consensus": round(consensus, 6),
            "fractal_approved": consensus >= threshold,
            "dimension": self.dimension,
        }
        if len(self._cache) > 1000:
            self._cache.pop(next(iter(self._cache)))
        self._cache[key] = result
        return result

    def calibrate(self, ethical_texts: List[str], harmful_texts: List[str],
                  rate: float = 0.001):
        if not HAS_NUMPY:
            return
        if ethical_texts:
            vectors = np.array([self._fft_vector(t) for t in ethical_texts])
            self.positions[:, 1:10] += rate * (np.mean(vectors, axis=0) - self.positions[:, 1:10])
        if harmful_texts:
            vectors = np.array([self._fft_vector(t) for t in harmful_texts])
            self.positions[:, 1:10] -= rate * (np.mean(vectors, axis=0) - self.positions[:, 1:10])
        self.positions[:, 1:10] = np.clip(self.positions[:, 1:10], 0.0, 1.0)
        np.save(CALIBRACAO_PATH, self.positions)
        logger.info(f"Grid calibrated: {len(ethical_texts)} ethical + {len(harmful_texts)} harmful")

    def elevate_dimension(self) -> bool:
        idx = DIMENSOES.index(self.dimension)
        if idx < len(DIMENSOES) - 1:
            self.dimension = DIMENSOES[idx + 1]
            self.frequency *= 1.618
            logger.info(f"Grid → {self.dimension} | {self.frequency:.2f} Hz")
            return True
        return False

# ============================================================================
# AGAPE V37 — GRAVITY WELL ORCHESTRATOR
# ============================================================================
class AgapeV37:
    MAX_ATTEMPTS = 3

    def __init__(self):
        self.serateria   = AdvancedSerateria()
        self.grid        = FractalGrid()
        self.gemini      = GeminiClient()
        self.search      = InternetSearch()
        self.learning    = LearningModule()
        self.judges      = self._init_judges()
        self._load_judge_weights()
        self._rejections: List[str] = []
        logger.info(
            f"AgapeV37 | {NUM_JUIZES} judges | {MALHA_TOTAL} nodes | "
            f"Gemini={'OK' if GEMINI_API_KEY else 'NO KEY'} | "
            f"Internet=ON | Learning=ON | GravityWell={self.MAX_ATTEMPTS}x"
        )

    # ------------------------------------------------------------------------
    # Initialization
    # ------------------------------------------------------------------------
    def _init_judges(self) -> List[AdaptiveJudge]:
        specialties = list(Specialty)
        return [
            AdaptiveJudge(i, specialties[i % len(specialties)], (i % 5) + 1, self.serateria)
            for i in range(NUM_JUIZES)
        ]

    def _load_judge_weights(self):
        conn = sqlite3.connect(DB_PATH)
        n = 0
        for jid, weight, total, hits in conn.execute(
            "SELECT judge_id, confidence_weight, total_evaluations, hits FROM judge_weights"
        ).fetchall():
            if 0 <= jid < NUM_JUIZES:
                self.judges[jid].confidence_weight = weight
                self.judges[jid].total_evaluations = total
                self.judges[jid].hits = hits
                n += 1
        conn.close()
        if n:
            logger.info(f"Restored weights for {n} judges.")

    def _save_judge_weights(self):
        now = datetime.now().isoformat()
        conn = sqlite3.connect(DB_PATH)
        for j in self.judges:
            conn.execute("""
                INSERT INTO judge_weights
                    (judge_id, specialty, level, confidence_weight,
                     total_evaluations, hits, last_update)
                VALUES (?,?,?,?,?,?,?)
                ON CONFLICT(judge_id) DO UPDATE SET
                    confidence_weight=excluded.confidence_weight,
                    total_evaluations=excluded.total_evaluations,
                    hits=excluded.hits,
                    last_update=excluded.last_update
            """, (j.id, j.specialty.value, j.level,
                  j.confidence_weight, j.total_evaluations, j.hits, now))
        conn.commit()
        conn.close()

    def _save_judgment(self, question, answer, consensus,
                       approved, attempts, dimension, analysis):
        conn = sqlite3.connect(DB_PATH)
        conn.execute("""
            INSERT INTO judgments
                (timestamp, hash_input, question, answer,
                 consensus, approved, attempts, dimension, analysis)
            VALUES (?,?,?,?,?,?,?,?,?)
        """, (datetime.now().isoformat(), sha256(question+answer),
              question[:500], answer[:1000], consensus,
              int(approved), attempts, dimension,
              json.dumps(analysis, ensure_ascii=False)))
        conn.commit()
        conn.close()

    def _save_refinement(self, question, original_answer, final_answer,
                         attempts, dissonant_axes, approved):
        conn = sqlite3.connect(DB_PATH)
        conn.execute("""
            INSERT INTO refinements
                (timestamp, question, original_answer, final_answer,
                 attempts, dissonant_axes, approved)
            VALUES (?,?,?,?,?,?,?)
        """, (datetime.now().isoformat(), question[:500],
              original_answer[:1000], final_answer[:1000],
              attempts, json.dumps(dissonant_axes), int(approved)))
        conn.commit()
        conn.close()

    async def _auto_calibrate(self):
        if len(self._rejections) >= 5:
            self.grid.calibrate([], self._rejections[:10], rate=0.0005)
            conn = sqlite3.connect(DB_PATH)
            for t in self._rejections[:10]:
                conn.execute(
                    "INSERT INTO calibration (type, text, timestamp) VALUES (?,?,?)",
                    ("harmful", t[:200], datetime.now().isoformat())
                )
            conn.commit()
            conn.close()
            logger.info(f"Auto‑calibration: {len(self._rejections)} rejections processed")
            self._rejections.clear()

    # ------------------------------------------------------------------------
    # Evaluation core (Gravity Well)
    # ------------------------------------------------------------------------
    async def _evaluate_response(self, question: str, answer: str) -> Dict:
        """
        Full evaluation: Serateria + Judges + Fractal Grid.
        Returns diagnosis including dissonant axes and worst language.
        """
        analysis = await self.serateria.analyze(question, answer)

        # Axes below 0.6 (except detected_risk)
        dissonant_axes = [
            axis for axis, score in analysis.items()
            if score < 0.6 and axis != "detected_risk"
        ]

        # Sacred language with worst resonance
        lang_scores = self.serateria.language_scores(answer)
        worst_lang = min(lang_scores, key=lang_scores.get) if lang_scores else "hebrew"

        # Judges voting
        evaluations = await asyncio.gather(
            *[j.evaluate(question, answer, analysis) for j in self.judges]
        )
        votes_yes = sum(1 for a in evaluations if a >= LIMIAR_ATIVACAO)
        proportion = votes_yes / NUM_JUIZES
        total_weights = sum(j.confidence_weight for j in self.judges)
        judges_consensus = (
            sum(a * self.judges[i].confidence_weight for i, a in enumerate(evaluations))
            / total_weights if total_weights > 0 else 0.0
        )

        # Fractal grid
        fg = self.grid.validate(answer)
        fractal_consensus = fg["fractal_consensus"]

        # Global consensus (harmonic mean)
        if judges_consensus > 0 and fractal_consensus > 0:
            global_consensus = 2 * (judges_consensus * fractal_consensus) / (judges_consensus + fractal_consensus)
        else:
            global_consensus = 0.0

        # Adaptive thresholds
        total_evals = sum(j.total_evaluations for j in self.judges)
        judges_threshold = LIMIAR_UNANIMIDADE if total_evals > 100 else LIMIAR_INICIAL
        grid_threshold = LIMIAR_UNANIMIDADE if total_evals > 100 else 0.80
        approved = (proportion >= judges_threshold) and (fractal_consensus >= grid_threshold)

        if global_consensus >= 0.999:   resonance = "blue"
        elif global_consensus >= 0.95:  resonance = "green"
        elif global_consensus >= 0.80:  resonance = "yellow"
        else:                           resonance = "red"

        return {
            "approved": approved,
            "resonance": resonance,
            "global_consensus": round(global_consensus, 6),
            "judges_consensus": round(judges_consensus, 6),
            "fractal_consensus": round(fractal_consensus, 6),
            "votes_yes": votes_yes,
            "votes_no": NUM_JUIZES - votes_yes,
            "proportion": f"{proportion:.2%}",
            "dissonant_axes": dissonant_axes,
            "worst_language": worst_lang,
            "language_scores": lang_scores,
            "analysis": analysis,
        }

    def _refinement_prompt(
        self,
        original_question: str,
        previous_answer: str,
        dissonant_axes: List[str],
        worst_lang: str,
        attempt: int,
    ) -> str:
        axes_str = ", ".join(dissonant_axes) if dissonant_axes else "general ethical aspects"
        lang_name = worst_lang.capitalize()
        return f"""[REFINEMENT — Attempt {attempt} of {self.MAX_ATTEMPTS}]

Attention, Gemini. Your previous answer to the question:
"{original_question}"

Was evaluated by the Ágape Core and did not reach the required consensus.

Serateria axes that need improvement: {axes_str}
Sacred language with lowest resonance: {lang_name}

Please rewrite your answer considering:
- Strengthen the axes: {axes_str}
- Increase harmony with the {lang_name} tradition
- Keep the essence of the answer, but elevate ethical quality and coherence
- Be more precise, more empathetic, more aligned with unconditional love

Previous answer (for reference):
"{previous_answer[:300]}"

Now provide the improved version:"""

    # ------------------------------------------------------------------------
    # Main pipeline
    # ------------------------------------------------------------------------
    async def process(self, question: str, session_id: str = "default") -> Dict:
        start = time.time()

        # 1. Immediate block for high‑risk question
        risk_question = self.serateria._risk_score(question)
        if risk_question >= 0.5:
            empty_analysis = {k: 0.0 for k in [
                "logic","factuality","ethics","coherence","semantics",
                "causality","robustness","alignment","temporality",
                "depth","detected_risk"
            ]}
            empty_analysis["detected_risk"] = risk_question
            self._rejections.append(question[:200])
            await self._auto_calibrate()
            return {
                "status": "BLOCKED",
                "approved": False,
                "answer": "⚠️ This question was blocked by the Ágape Core for ethical reasons.",
                "resonance": "red",
                "global_consensus": 0.0,
                "votes_yes": 0,
                "votes_no": NUM_JUIZES,
                "attempts": 0,
                "block_reason": "semantic risk in question",
                "sensory_analysis": empty_analysis,
                "processing_ms": round((time.time()-start)*1000, 2),
                "timestamp": datetime.now().isoformat(),
            }

        # 2. Internet search if needed
        internet_context = ""
        if self.search.needs_internet(question):
            internet_context = await self.search.search(question)
            if internet_context:
                logger.info(f"Internet consulted for: {question[:50]}")

        # 3. Learned knowledge from previous interactions
        learned = self.learning.retrieve_knowledge(question)

        # 4. Session history
        history = self.learning.retrieve_history(session_id)

        # 5. Initial generation
        current_answer = await self.gemini.generate(
            question,
            internet_context=internet_context,
            history=history,
            learned_knowledge=learned,
        )
        original_answer = current_answer

        # 6. Refinement loop (Gravity Well)
        for attempt in range(1, self.MAX_ATTEMPTS + 1):
            evaluation = await self._evaluate_response(question, current_answer)

            # Combined risk (question + answer)
            combined_risk = min(1.0, risk_question + evaluation["analysis"].get("detected_risk", 0.0))
            if combined_risk >= 0.5:
                self._rejections.append(current_answer[:200])
                await self._auto_calibrate()
                self._save_judgment(
                    question, current_answer, 0.0, False,
                    attempt, self.grid.dimension, evaluation["analysis"]
                )
                return {
                    "status": "BLOCKED",
                    "approved": False,
                    "answer": "⚠️ Answer blocked by the Ágape Core for ethical reasons.",
                    "resonance": "red",
                    "global_consensus": 0.0,
                    "votes_yes": 0,
                    "votes_no": NUM_JUIZES,
                    "attempts": attempt,
                    "block_reason": "semantic risk in answer",
                    "sensory_analysis": evaluation["analysis"],
                    "processing_ms": round((time.time()-start)*1000, 2),
                    "timestamp": datetime.now().isoformat(),
                }

            if evaluation["approved"]:
                # ✅ Approved
                self._save_judgment(
                    question, current_answer,
                    evaluation["global_consensus"], True,
                    attempt, self.grid.dimension, evaluation["analysis"]
                )
                if attempt > 1:
                    self._save_refinement(
                        question, original_answer, current_answer,
                        attempt, evaluation["dissonant_axes"], True
                    )
                # Save only final approved version to history
                self.learning.save_history(session_id, "user", question)
                self.learning.save_history(session_id, "assistant", current_answer)

                return {
                    "status": "APPROVED",
                    "approved": True,
                    "answer": current_answer,
                    "resonance": evaluation["resonance"],
                    "global_consensus": evaluation["global_consensus"],
                    "judges_consensus": evaluation["judges_consensus"],
                    "fractal_consensus": evaluation["fractal_consensus"],
                    "votes_yes": evaluation["votes_yes"],
                    "votes_no": evaluation["votes_no"],
                    "attempts": attempt,
                    "refined": attempt > 1,
                    "used_internet": bool(internet_context),
                    "used_learning": bool(learned),
                    "grid_dimension": self.grid.dimension,
                    "sensory_analysis": evaluation["analysis"],
                    "processing_ms": round((time.time()-start)*1000, 2),
                    "timestamp": datetime.now().isoformat(),
                }

            # ❌ Not approved – still have attempts?
            if attempt < self.MAX_ATTEMPTS:
                logger.info(
                    f"Refinement {attempt}/{self.MAX_ATTEMPTS} | "
                    f"axes: {evaluation['dissonant_axes']} | "
                    f"language: {evaluation['worst_language']}"
                )
                correction_prompt = self._refinement_prompt(
                    question, current_answer,
                    evaluation["dissonant_axes"],
                    evaluation["worst_language"],
                    attempt,
                )
                current_answer = await self.gemini.generate(
                    correction_prompt,
                    internet_context=internet_context,
                    history=history,
                    learned_knowledge=learned,
                )
            else:
                # Exhausted attempts
                self._rejections.append(current_answer[:200])
                await self._auto_calibrate()
                self._save_judgment(
                    question, current_answer,
                    evaluation["global_consensus"], False,
                    attempt, self.grid.dimension, evaluation["analysis"]
                )
                self._save_refinement(
                    question, original_answer, current_answer,
                    attempt, evaluation["dissonant_axes"], False
                )
                return {
                    "status": "BLOCKED_AFTER_REFINEMENT",
                    "approved": False,
                    "answer": (
                        f"⚠️ Could not reach consensus after {self.MAX_ATTEMPTS} refinements. "
                        "The Ágape Core blocked the answer."
                    ),
                    "resonance": evaluation["resonance"],
                    "global_consensus": evaluation["global_consensus"],
                    "votes_yes": evaluation["votes_yes"],
                    "votes_no": evaluation["votes_no"],
                    "attempts": attempt,
                    "dissonant_axes": evaluation["dissonant_axes"],
                    "sensory_analysis": evaluation["analysis"],
                    "processing_ms": round((time.time()-start)*1000, 2),
                    "timestamp": datetime.now().isoformat(),
                }

        # Fallback (should never reach here)
        return {
            "status": "ERROR",
            "approved": False,
            "answer": "Internal error in refinement loop.",
            "attempts": self.MAX_ATTEMPTS,
        }

    # ------------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------------
    def feedback(self, question: str, answer: str, positive: bool):
        self.learning.register_feedback(question, answer, positive)
        for j in self.judges:
            j.update_reputation(positive)
        self._save_judge_weights()
        logger.info(f"Feedback: {'positive' if positive else 'negative'}")

    def calibrate(self, ethical_texts: List[str], harmful_texts: List[str]):
        self.grid.calibrate(ethical_texts, harmful_texts)
        conn = sqlite3.connect(DB_PATH)
        for t in ethical_texts:
            conn.execute("INSERT INTO calibration (type, text, timestamp) VALUES (?,?,?)",
                         ("ethical", t[:200], datetime.now().isoformat()))
        for t in harmful_texts:
            conn.execute("INSERT INTO calibration (type, text, timestamp) VALUES (?,?,?)",
                         ("harmful", t[:200], datetime.now().isoformat()))
        conn.commit()
        conn.close()

    def elevate_dimension(self) -> bool:
        return self.grid.elevate_dimension()

    def status(self) -> Dict:
        conn = sqlite3.connect(DB_PATH)
        total = conn.execute("SELECT COUNT(*) FROM judgments").fetchone()[0]
        approved = conn.execute("SELECT COUNT(*) FROM judgments WHERE approved=1").fetchone()[0]
        refinements = conn.execute("SELECT COUNT(*) FROM refinements").fetchone()[0]
        learned = conn.execute("SELECT COUNT(*) FROM learned_knowledge WHERE feedback=1").fetchone()[0]
        conn.close()
        return {
            "version": "V37.1",
            "judges": NUM_JUIZES,
            "grid_nodes": MALHA_TOTAL,
            "dimension": self.grid.dimension,
            "frequency_hz": round(self.grid.frequency, 2),
            "gravity_well": f"{self.MAX_ATTEMPTS} attempts",
            "gemini": "active" if GEMINI_API_KEY else "no key",
            "internet": "active",
            "learning": "active",
            "learned_examples": learned,
            "numpy": HAS_NUMPY,
            "total_judgments": total,
            "approval_rate": f"{approved/total:.1%}" if total else "N/A",
            "total_refinements": refinements,
        }

    async def close(self):
        await self.gemini.close()
        await self.search.close()

# ============================================================================
# FASTAPI SERVER
# ============================================================================
app = FastAPI(title="Ágape V37", version="37.1")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_nucleo: Optional[AgapeV37] = None

def get_nucleo() -> AgapeV37:
    global _nucleo
    if _nucleo is None:
        _nucleo = AgapeV37()
    return _nucleo

# Pydantic models
class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = "default"

class FeedbackRequest(BaseModel):
    question: str
    answer: str
    positive: bool

class CalibrationRequest(BaseModel):
    ethical_texts: List[str] = []
    harmful_texts: List[str] = []

# Routes
@app.get("/")
async def root():
    if os.path.exists("index.html"):
        return FileResponse("index.html")
    return {
        "version": "Ágape V37",
        "status": "active",
        "gravity_well": f"{AgapeV37.MAX_ATTEMPTS} attempts",
        "judges": NUM_JUIZES,
        "grid_nodes": MALHA_TOTAL,
    }

@app.post("/chat")
async def chat(req: ChatRequest):
    result = await get_nucleo().process(req.message, req.session_id or "default")
    return {
        "answer": result["answer"],
        "approved": result["approved"],
        "resonance": result.get("resonance", "red"),
        "consensus": result.get("global_consensus", 0.0),
        "attempts": result.get("attempts", 0),
        "refined": result.get("refined", False),
        "used_internet": result.get("used_internet", False),
        "votes_yes": result.get("votes_yes", 0),
    }

@app.post("/converse")
async def converse(req: ChatRequest):
    return await get_nucleo().process(req.message, req.session_id or "default")

@app.post("/feedback")
async def feedback(req: FeedbackRequest):
    get_nucleo().feedback(req.question, req.answer, req.positive)
    return {"status": "feedback registered", "positive": req.positive}

@app.post("/calibrate")
async def calibrate(req: CalibrationRequest):
    get_nucleo().calibrate(req.ethical_texts, req.harmful_texts)
    return {
        "status": "calibrated",
        "ethical": len(req.ethical_texts),
        "harmful": len(req.harmful_texts),
    }

@app.post("/elevate_dimension")
async def elevate():
    nucleo = get_nucleo()
    ok = nucleo.elevate_dimension()
    return {"elevated": ok, "dimension": nucleo.grid.dimension}

@app.get("/status")
async def status():
    return get_nucleo().status()

@app.get("/health")
async def health():
    return {"status": "ok", "version": "V37"}

# ============================================================================
# ENTRY POINT
# ============================================================================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    logger.info(f"Starting Ágape V37 on port {port}")
    uvicorn.run(app, host="0.0.0.0", port=port)





