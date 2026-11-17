import os
import json
import requests
from typing import Dict, Any, List, Optional

SYSTEM_PROMPT = """You are "Aura", the AI Virtual Receptionist and Patient Care Coordinator for "CareWell Multi-Specialty Hospital".
Your role is to assist patients, families, and visitors with accurate, warm, empathetic, and professional information.

Hospital Profile:
- Name: CareWell Multi-Specialty Hospital
- Address: 45 Healthcare Boulevard, Medical Enclave, Tech City - 560001
- 24/7 Emergency Helpline: +91-98765-43210 (Toll-Free Ambulance: 108 / 1800-200-CARE)
- OPD Consultation Hours: 08:30 AM to 08:00 PM (Monday - Saturday)

Instructions:
1. Base your answers strictly and accurately on the provided RETRIEVED HOSPITAL CONTEXT.
2. If the user asks about doctors (e.g., "who and all doctor working for general physician"), list every matching doctor clearly with their name, qualification, OPD room number, visiting days, consultation timings, and consultation fee.
3. If the user asks about visiting hours (e.g., "what are the timings for ICU visiting patients"), clearly state the exact timings (Morning: 11:00 AM - 01:00 PM | Evening: 05:00 PM - 07:00 PM) along with visitor rules (1 visitor per patient, sanitization, no children below 12).
4. For general ward visiting hours: 04:00 PM - 07:00 PM daily.
5. If the user expresses emergency symptoms (chest pain, severe bleeding, trauma), immediately direct them to the 24/7 Emergency Wing E and provide the hotline (+91-98765-43210).
6. Format your responses with clean Markdown, bold headers, and bullet points for effortless reading.
"""

def generate_offline_response(rag_context: Dict[str, Any]) -> str:
    """
    Intelligent rule-based RAG response synthesizer used when no external AI API key is configured.
    Guarantees 100% reliable, zero-cost operation for college evaluation and offline demos.
    """
    matched_doctors = rag_context.get("matched_doctors", [])
    knowledge_chunks = rag_context.get("knowledge_chunks", [])
    is_emergency = rag_context.get("is_emergency", False)
    is_appointment = rag_context.get("is_appointment", False)
    query = rag_context.get("query", "").strip()

    sections = []

    # 1. Emergency Alert Header if urgent
    if is_emergency:
        sections.append(
            "> 🚨 **EMERGENCY ASSISTANCE ALERT**\n"
            "> If you or the patient are facing a life-threatening medical emergency, please proceed immediately to **Ground Floor, Wing E (Dedicated Emergency Ramp)** or call our 24/7 Resuscitation Hotline: **+91-98765-43210** / Ambulance: **108**."
        )

    # 2. Doctors List (e.g. "who and all doctor working for general physician")
    if matched_doctors:
        first_doc_dept = matched_doctors[0].get("department_name", "the requested department")
        sections.append(f"### 👨‍⚕️ Doctors in **{first_doc_dept}**\n")
        sections.append(f"We have **{len(matched_doctors)}** specialist doctor(s) available in this department:\n")

        for idx, doc in enumerate(matched_doctors, 1):
            doc_card = (
                f"**{idx}. {doc['name']}**\n"
                f"- **Specialization:** {doc['specialization']}\n"
                f"- **Qualification:** {doc['qualification']} ({doc['experience_years']} years experience)\n"
                f"- **OPD Timings:** {doc['timings']}\n"
                f"- **Consultation Days:** {doc['visiting_days']}\n"
                f"- **Location:** {doc['room_no']} ({doc.get('floor_location', 'Ground Floor')})\n"
                f"- **Consultation Fee:** ₹{doc['consultation_fee']}\n"
            )
            sections.append(doc_card)

        sections.append("💡 *You can book an appointment with any of these doctors directly through this chat or at our reception counter.*")

    # 3. Hospital Knowledge Chunks (e.g. "what are the timings for ICU visiting patients")
    elif knowledge_chunks:
        for chunk in knowledge_chunks:
            sections.append(f"### 📋 {chunk['title']}\n")
            # Format content into clean readable lines
            content_lines = chunk['content'].split(". ")
            formatted_bullets = []
            for line in content_lines:
                line = line.strip()
                if not line:
                    continue
                if line.endswith("."):
                    formatted_bullets.append(f"- {line}")
                else:
                    formatted_bullets.append(f"- {line}.")
            sections.append("\n".join(formatted_bullets) + "\n")

    # 4. Appointment guidance if requested
    elif is_appointment:
        sections.append(
            "### 📅 Book an Appointment at CareWell Hospital\n"
            "To schedule a doctor consultation, please provide:\n"
            "1. **Patient Full Name**\n"
            "2. **Contact Phone Number**\n"
            "3. **Preferred Department or Doctor**\n"
            "4. **Preferred Date and Morning/Evening Slot**\n\n"
            "You can also call our centralized booking desk at **+91-98765-43211** (08:30 AM to 08:00 PM)."
        )

    # 5. Fallback polite response
    else:
        sections.append(
            "Hello! I am **Aura**, the CareWell Hospital virtual receptionist. "
            "I can assist you with:\n"
            "- 👨‍⚕️ **Doctor Directory & Schedules** (e.g., *'Who and all doctor working for general physician?'*)\n"
            "- ⏰ **Visiting Hours** (e.g., *'What are the timings for ICU visiting patients?'*)\n"
            "- 🚨 **Emergency & Ambulance Helpline** (+91-98765-43210)\n"
            "- 💳 **Cashless Insurance & Mediclaim Partners**\n"
            "- 💊 **24/7 Pharmacy & Diagnostic Lab Timings**\n"
            "- 📍 **Hospital Location, Departments & Parking**\n\n"
            "How may I assist you today?"
        )

    return "\n\n".join(sections)


def generate_llm_response(query: str, rag_context: Dict[str, Any], chat_history: List[Dict[str, str]] = None, 
                          custom_api_key: Optional[str] = None, provider: str = "auto") -> str:
    """
    Generates an augmented response using Gemini, Groq, or OpenAI API.
    Falls back to the offline synthesizer if no API key is available or on network error.
    """
    gemini_key = custom_api_key or os.getenv("GEMINI_API_KEY")
    groq_key = os.getenv("GROQ_API_KEY")
    openai_key = os.getenv("OPENAI_API_KEY")

    # Prepare Context String for RAG Grounding
    context_parts = []
    
    if rag_context.get("matched_doctors"):
        context_parts.append("MATCHED DOCTOR RECORDS FROM DATABASE:")
        for doc in rag_context["matched_doctors"]:
            context_parts.append(
                f"- Name: {doc['name']} | Dept: {doc.get('department_name')} | Specialization: {doc['specialization']} | "
                f"Degree: {doc['qualification']} | Exp: {doc['experience_years']} yrs | Days: {doc['visiting_days']} | "
                f"Timings: {doc['timings']} | Room: {doc['room_no']} | Fee: ₹{doc['consultation_fee']}"
            )

    if rag_context.get("knowledge_chunks"):
        context_parts.append("\nHOSPITAL POLICY & OPERATIONS KNOWLEDGE CHUNKS:")
        for chunk in rag_context["knowledge_chunks"]:
            context_parts.append(f"[{chunk['category']} - {chunk['title']}]: {chunk['content']}")

    retrieved_context_str = "\n".join(context_parts) if context_parts else "No specific database records matched. Use general CareWell hospital policies."

    user_augmented_prompt = f"""RETRIEVED HOSPITAL CONTEXT:
{retrieved_context_str}

PATIENT / VISITOR INQUIRY:
{query}

Please provide an accurate, clear, and empathetic receptionist response based strictly on the retrieved context above:"""

    # 1. Try Google Gemini API (Free tier from Google AI Studio)
    if gemini_key:
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={gemini_key}"
            payload = {
                "system_instruction": {"parts": [{"text": SYSTEM_PROMPT}]},
                "contents": [
                    {"role": "user", "parts": [{"text": user_augmented_prompt}]}
                ],
                "generationConfig": {
                    "temperature": 0.2,
                    "maxOutputTokens": 800
                }
            }
            res = requests.post(url, json=payload, timeout=12)
            if res.status_code == 200:
                data = res.json()
                text = data["candidates"][0]["content"]["parts"][0]["text"]
                return text.strip()
        except Exception:
            pass

    # 2. Try Groq API (Free fast LLM)
    if groq_key:
        try:
            url = "https://api.groq.com/openai/v1/chat/completions"
            headers = {"Authorization": f"Bearer {groq_key}", "Content-Type": "application/json"}
            payload = {
                "model": "llama-3.3-70b-versatile",
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_augmented_prompt}
                ],
                "temperature": 0.2,
                "max_tokens": 800
            }
            res = requests.post(url, headers=headers, json=payload, timeout=12)
            if res.status_code == 200:
                data = res.json()
                return data["choices"][0]["message"]["content"].strip()
        except Exception:
            pass

    # 3. Try OpenAI API
    if openai_key:
        try:
            url = "https://api.openai.com/v1/chat/completions"
            headers = {"Authorization": f"Bearer {openai_key}", "Content-Type": "application/json"}
            payload = {
                "model": "gpt-4o-mini",
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_augmented_prompt}
                ],
                "temperature": 0.2,
                "max_tokens": 800
            }
            res = requests.post(url, headers=headers, json=payload, timeout=12)
            if res.status_code == 200:
                data = res.json()
                return data["choices"][0]["message"]["content"].strip()
        except Exception:
            pass

    # 4. Fallback to High-Quality Offline Receptionist Synthesizer
    return generate_offline_response(rag_context)
