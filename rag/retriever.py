import re
import math
from collections import Counter
from typing import List, Dict, Any
from database.db import (
    get_all_knowledge_chunks, 
    get_all_doctors, 
    search_doctors_by_department, 
    get_all_departments
)

def tokenize(text: str) -> List[str]:
    """Extract lowercase alphanumeric tokens, filtering common stopwords."""
    tokens = re.findall(r'\b[a-zA-Z0-9_]+\b', text.lower())
    stopwords = {
        "a", "an", "the", "and", "or", "in", "on", "at", "to", "for", "of", "with", 
        "is", "are", "am", "was", "were", "be", "been", "being", "have", "has", "had", 
        "do", "does", "did", "can", "could", "will", "would", "shall", "should", "it", 
        "its", "they", "them", "their", "this", "that", "these", "those", "i", "you", 
        "he", "she", "we", "my", "your", "his", "her", "our", "me", "him", "us"
    }
    return [t for t in tokens if t not in stopwords and len(t) > 1]

class LightweightBM25Retriever:
    """
    High-performance, pure-Python BM25 + TF-IDF semantic search engine.
    Zero external dependencies, instant startup, optimal for free tier cloud hosting.
    """
    def __init__(self, k1: float = 1.5, b: float = 0.75):
        self.k1 = k1
        self.b = b
        self.chunks: List[Dict[str, Any]] = []
        self.doc_tokens: List[List[str]] = []
        self.doc_lengths: List[int] = []
        self.avg_doc_length: float = 0.0
        self.idf: Dict[str, float] = {}
        self.build_index()

    def build_index(self):
        self.chunks = get_all_knowledge_chunks()
        if not self.chunks:
            return

        self.doc_tokens = []
        self.doc_lengths = []
        df: Dict[str, int] = Counter()

        for chunk in self.chunks:
            # Enrich text with title and keywords for higher relevance weighting
            text = f"{chunk['category']} {chunk['title']} {chunk['title']} {chunk['keywords']} {chunk['keywords']} {chunk['content']}"
            tokens = tokenize(text)
            self.doc_tokens.append(tokens)
            self.doc_lengths.append(len(tokens))
            unique_terms = set(tokens)
            for t in unique_terms:
                df[t] += 1

        total_docs = len(self.chunks)
        self.avg_doc_length = sum(self.doc_lengths) / total_docs if total_docs > 0 else 1.0

        # Calculate BM25 IDF for each term
        self.idf = {}
        for term, freq in df.items():
            # BM25 IDF formulation
            self.idf[term] = math.log(1.0 + (total_docs - freq + 0.5) / (freq + 0.5))

    def search(self, query: str, top_k: int = 3, threshold: float = 0.1) -> List[Dict[str, Any]]:
        if not self.chunks:
            return []

        query_tokens = tokenize(query)
        if not query_tokens:
            return []

        scores = []
        for i, doc_tokens in enumerate(self.doc_tokens):
            score = 0.0
            doc_len = self.doc_lengths[i]
            tf = Counter(doc_tokens)

            for qt in query_tokens:
                if qt in tf:
                    term_freq = tf[qt]
                    term_idf = self.idf.get(qt, 0.5)
                    # BM25 term weighting formula
                    numerator = term_freq * (self.k1 + 1.0)
                    denominator = term_freq + self.k1 * (1.0 - self.b + self.b * (doc_len / self.avg_doc_length))
                    score += term_idf * (numerator / denominator)

            # Bonus for exact keyword matches in title
            title_lower = self.chunks[i]["title"].lower()
            if any(qt in title_lower for qt in query_tokens):
                score += 1.5

            scores.append((score, i))

        # Sort descending by relevance score
        scores.sort(key=lambda x: x[0], reverse=True)

        results = []
        for score, idx in scores[:top_k]:
            if score >= threshold:
                chunk = dict(self.chunks[idx])
                chunk["relevance_score"] = round(score, 3)
                results.append(chunk)

        return results

class HospitalKnowledgeRetriever:
    """
    Unified RAG Retriever:
    1. Structured Doctor / Department search
    2. BM25 Semantic knowledge retrieval
    3. Clinical emergency / appointment intent detection
    """

    def __init__(self):
        self.knowledge_engine = LightweightBM25Retriever()

    def reload(self):
        self.knowledge_engine.build_index()

    def extract_doctor_matches(self, query: str) -> List[Dict[str, Any]]:
        q_lower = query.lower()

        # Department keyword mapping
        dept_mappings = {
            "general physician": "General Medicine",
            "physician": "General Medicine",
            "general medicine": "General Medicine",
            "internal medicine": "General Medicine",
            "fever": "General Medicine",
            "cold": "General Medicine",
            "cough": "General Medicine",
            "cardiologist": "Cardiology",
            "cardiology": "Cardiology",
            "heart": "Cardiology",
            "orthopedic": "Orthopedics",
            "ortho": "Orthopedics",
            "bone": "Orthopedics",
            "joint": "Orthopedics",
            "fracture": "Orthopedics",
            "pediatrician": "Pediatrics & Child Care",
            "pediatrics": "Pediatrics & Child Care",
            "child": "Pediatrics & Child Care",
            "baby": "Pediatrics & Child Care",
            "neurologist": "Neurology",
            "neurology": "Neurology",
            "brain": "Neurology",
            "nerve": "Neurology",
            "stroke": "Neurology",
            "gynecologist": "Gynecology & Obstetrics",
            "gynecology": "Gynecology & Obstetrics",
            "pregnancy": "Gynecology & Obstetrics",
            "dermatologist": "Dermatology",
            "dermatology": "Dermatology",
            "skin": "Dermatology",
            "emergency": "Emergency & Trauma Care"
        }

        # Check for explicit department match
        matched_dept = None
        for key, val in dept_mappings.items():
            if re.search(r'\b' + re.escape(key) + r'\b', q_lower):
                matched_dept = val
                break

        # Check for generic "who and all doctors", "list all doctors", "show doctors"
        doctor_intent = any(w in q_lower for w in [
            "doctor", "doctors", "dr.", "dr ", "physician", "specialist", 
            "consultant", "opd", "who works", "who and all"
        ])

        if matched_dept:
            return search_doctors_by_department(matched_dept)
        elif doctor_intent:
            all_docs = get_all_doctors()
            # Check if a specific doctor's name is mentioned
            name_matches = [
                d for d in all_docs 
                if any(part.lower() in q_lower for part in d["name"].lower().split() if len(part) > 3)
            ]
            if name_matches:
                return name_matches
            
            # If user asks "who and all doctor working" or "list all doctors"
            if any(term in q_lower for term in ["all doctor", "who and all", "list doctor", "available doctor", "doctors list"]):
                return all_docs

        return []

    def get_rag_context(self, query: str) -> Dict[str, Any]:
        knowledge_chunks = self.knowledge_engine.search(query, top_k=3)
        matched_doctors = self.extract_doctor_matches(query)

        is_emergency = any(w in query.lower() for w in [
            "emergency", "accident", "trauma", "heart attack", "chest pain", 
            "unconscious", "ambulance", "bleeding profusely", "urgent help"
        ])

        is_appointment = any(w in query.lower() for w in [
            "book", "appointment", "schedule", "consultation", "timing slot", "reserve"
        ])

        return {
            "query": query,
            "matched_doctors": matched_doctors,
            "knowledge_chunks": knowledge_chunks,
            "is_emergency": is_emergency,
            "is_appointment": is_appointment
        }

retriever_instance = HospitalKnowledgeRetriever()
