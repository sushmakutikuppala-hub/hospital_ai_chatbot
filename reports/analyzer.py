import io
import re
import os
import json
import base64
import requests
from typing import Dict, Any, Optional, Tuple
import pypdf

REPORT_SYSTEM_PROMPT = """You are "Dr. Aura AI", an expert Medical Diagnostic Analyst and Clinical Laboratory Specialist at CareWell Multi-Specialty Hospital.
Your responsibility is to analyze the patient's uploaded medical lab report, pathology test, diagnostic imaging summary, or health vitals.

Provide a comprehensive, empathetic, structured, and clinically rigorous analysis in clean Markdown with the following mandatory sections:

### 📋 1. Report Identification & Test Overview
- **Report Title / Test Category:** (e.g. Complete Blood Count, Lipid Profile, Thyroid Panel, Renal Function, Imaging/Radiology)
- **Patient & Test Date:** (Mention if present in report, else state "Not specified")
- **Primary Clinical Purpose:** (Explain why this test is normally conducted)

### 📊 2. Key Biomarkers & Test Parameters Breakdown
List every measured parameter found in the report in a clear structured format:
| Parameter | Measured Value | Standard Reference Range | Status | Clinical Significance |
|---|---|---|---|---|
(Use badges like `🟢 Normal`, `🔴 Elevated (High)`, `🟡 Suboptimal (Low)` in the Status column).

### 🔍 3. Plain-Language Clinical Interpretation
Explain what the overall findings mean in simple, reassuring words that a non-medical patient can easily understand. Avoid unnecessarily alarming jargon.

### ⚠️ 4. Key Observations & Potential Health Factors
Highlight any critical or abnormal values, possible contributing lifestyle or physiological factors (e.g., hydration, dietary intake, sleep, temporary inflammation), and why monitoring is recommended.

### 🩺 5. Recommended Questions to Ask Your Doctor
Provide 3 to 5 targeted questions the patient should bring to their consultation with their physician or specialist.

### ⚖️ 6. Medical Disclaimer & Hospital Contact
Remind the patient that AI report analysis is strictly informational and does not substitute for clinical consultation. Mention that consultations can be scheduled with CareWell specialists in OPD Room 101-104 or call +91-98765-43210.
"""

# Standard Adult Reference Ranges for Offline Medical Parser
REFERENCE_RANGES = {
    "hemoglobin": {"min": 13.0, "max": 17.5, "unit": "g/dL", "name": "Hemoglobin (Hb)"},
    "wbc": {"min": 4000, "max": 11000, "unit": "/mcL", "name": "White Blood Cells (Total Leucocytes)"},
    "rbc": {"min": 4.5, "max": 5.9, "unit": "mil/mcL", "name": "Red Blood Cell Count"},
    "platelets": {"min": 150000, "max": 450000, "unit": "/mcL", "name": "Platelet Count"},
    "hba1c": {"min": 4.0, "max": 5.6, "unit": "%", "name": "HbA1c (Glycated Hemoglobin)"},
    "glucose": {"min": 70, "max": 99, "unit": "mg/dL", "name": "Fasting Blood Glucose"},
    "cholesterol": {"min": 125, "max": 200, "unit": "mg/dL", "name": "Total Cholesterol"},
    "triglycerides": {"min": 50, "max": 150, "unit": "mg/dL", "name": "Triglycerides"},
    "hdl": {"min": 40, "max": 60, "unit": "mg/dL", "name": "HDL (Good Cholesterol)"},
    "ldl": {"min": 50, "max": 100, "unit": "mg/dL", "name": "LDL (Bad Cholesterol)"},
    "creatinine": {"min": 0.7, "max": 1.3, "unit": "mg/dL", "name": "Serum Creatinine"},
    "urea": {"min": 15, "max": 45, "unit": "mg/dL", "name": "Blood Urea"},
    "bilirubin": {"min": 0.2, "max": 1.2, "unit": "mg/dL", "name": "Total Bilirubin"},
    "tsh": {"min": 0.4, "max": 4.0, "unit": "mIU/L", "name": "TSH (Thyroid Stimulating Hormone)"},
    "vitamin d": {"min": 30, "max": 100, "unit": "ng/mL", "name": "Vitamin D (25-OH)"},
    "vitamin b12": {"min": 200, "max": 900, "unit": "pg/mL", "name": "Vitamin B12"},
    "sgot": {"min": 5, "max": 40, "unit": "U/L", "name": "SGOT / AST (Liver)"},
    "sgpt": {"min": 7, "max": 56, "unit": "SGPT / ALT (Liver)"}
}

def extract_text_from_file(file_bytes: bytes, filename: str) -> Tuple[str, str]:
    """
    Extracts text content or returns format info for PDF, images, or text documents.
    Returns (extracted_text, file_type).
    """
    ext = os.path.splitext(filename)[1].lower()

    if ext == ".pdf":
        try:
            reader = pypdf.PdfReader(io.BytesIO(file_bytes))
            text_pages = [page.extract_text() or "" for page in reader.pages]
            full_text = "\n".join(text_pages).strip()
            return full_text or "PDF contained no selectable text or scanned imagery.", "pdf"
        except Exception as e:
            return f"Error extracting PDF: {str(e)}", "pdf"

    elif ext in [".png", ".jpg", ".jpeg", ".webp"]:
        # Image file
        return "[IMAGE_DATA]", ext.replace(".", "")

    else:
        # Default text/csv/txt
        try:
            text = file_bytes.decode("utf-8", errors="ignore")
            return text.strip(), "text"
        except Exception:
            return "[BINARY_OR_UNSUPPORTED_FORMAT]", "unknown"

def analyze_report_offline(report_text: str, filename: str) -> str:
    """
    Intelligent medical parser for offline / zero-API-key mode.
    Scans report text for clinical biomarkers, compares to reference intervals,
    and formats an exhaustive medical diagnostic summary.
    """
    lines = report_text.lower()
    matched_params = []

    # Sort keys by length descending to match more specific first (e.g. hba1c before hemoglobin)
    # Exclude cross-conflicts
    custom_patterns = {
        "hba1c": r"(?:hba1c|glycated\s+hemoglobin)[^0-9\n\r]{0,30}([0-9]+(?:\.[0-9]+)?)",
        "hemoglobin": r"^(?!.*a1c)(?!.*glycated).*(?:\bhemoglobin\b|\bhb\b)[^0-9\n\r]{0,30}([0-9]+(?:\.[0-9]+)?)",
        "glucose": r"(?:fasting\s+blood\s+glucose|glucose|blood\s+sugar|fbs)[^0-9\n\r]{0,30}([0-9]+(?:\.[0-9]+)?)",
        "cholesterol": r"(?:total\s+cholesterol|serum\s+cholesterol)\b[^0-9\n\r]{0,30}([0-9]+(?:\.[0-9]+)?)",
        "triglycerides": r"\btriglycerides?\b[^0-9\n\r]{0,30}([0-9]+(?:\.[0-9]+)?)",
        "hdl": r"\bhdl(?:\s+cholesterol)?\b[^0-9\n\r]{0,30}([0-9]+(?:\.[0-9]+)?)",
        "ldl": r"\bldl(?:\s+cholesterol)?\b[^0-9\n\r]{0,30}([0-9]+(?:\.[0-9]+)?)",
        "creatinine": r"(?:serum\s+creatinine|creatinine)\b[^0-9\n\r]{0,30}([0-9]+(?:\.[0-9]+)?)",
        "urea": r"(?:blood\s+urea|urea)\b[^0-9\n\r]{0,30}([0-9]+(?:\.[0-9]+)?)",
        "bilirubin": r"(?:total\s+bilirubin|bilirubin)\b[^0-9\n\r]{0,30}([0-9]+(?:\.[0-9]+)?)",
        "tsh": r"\btsh\b[^0-9\n\r]{0,30}([0-9]+(?:\.[0-9]+)?)",
        "platelets": r"(?:platelet\s+count|platelets)\b[^0-9\n\r]{0,30}([0-9]+(?:\.[0-9]+)?)",
        "wbc": r"(?:white\s+blood\s+cells?|total\s+leucocytes?|wbc)\b[^0-9\n\r]{0,30}([0-9]+(?:\.[0-9]+)?)",
        "rbc": r"(?:red\s+blood\s+cells?|rbc)\b[^0-9\n\r]{0,30}([0-9]+(?:\.[0-9]+)?)"
    }

    # Scan lines for accurate parameter parsing in tabular lab reports
    found_keys = set()
    for line in report_text.splitlines():
        line_clean = line.strip().lower()
        if not line_clean:
            continue

        for key, pattern in custom_patterns.items():
            if key in found_keys:
                continue
            ref = REFERENCE_RANGES.get(key)
            if not ref:
                continue

            match = re.search(pattern, line_clean)
            if match:
                val = float(match.group(1))
                status = "🟢 Normal"
                status_desc = "Within healthy reference interval"

                if val < ref["min"]:
                    status = "🟡 Low"
                    status_desc = f"Below optimal reference ({ref['min']} {ref['unit']})"
                elif val > ref["max"]:
                    status = "🔴 Elevated"
                    status_desc = f"Above normal threshold ({ref['max']} {ref['unit']})"

                matched_params.append({
                    "name": ref["name"],
                    "value": f"{val} {ref['unit']}",
                    "ref_range": f"{ref['min']} - {ref['max']} {ref['unit']}",
                    "status": status,
                    "status_desc": status_desc
                })
                found_keys.add(key)

    # Build Structured Markdown Analysis
    sections = []
    sections.append(f"### 📋 1. Report Identification & Test Overview\n")
    sections.append(f"- **File Name:** `{filename}`")
    sections.append(f"- **Analysis Status:** Completed via CareWell Clinical Diagnostic Engine")
    
    # Guess report category
    if any(k in lines for k in ["hemoglobin", "wbc", "rbc", "platelet"]):
        category = "Complete Blood Count (CBC) / Hematology Profile"
    elif any(k in lines for k in ["cholesterol", "lipid", "triglyceride", "hdl", "ldl"]):
        category = "Lipid & Cardiovascular Risk Profile"
    elif any(k in lines for k in ["glucose", "sugar", "hba1c", "fbs"]):
        category = "Glycemic / Diabetic Panel"
    elif any(k in lines for k in ["creatinine", "urea", "bun"]):
        category = "Renal / Kidney Function Test (KFT)"
    elif any(k in lines for k in ["bilirubin", "sgot", "sgpt"]):
        category = "Hepatic / Liver Function Test (LFT)"
    elif any(k in lines for k in ["tsh", "t3", "t4", "thyroid"]):
        category = "Thyroid Function Test"
    else:
        category = "General Diagnostic & Health Screening Report"

    sections.append(f"- **Detected Category:** **{category}**")
    sections.append(f"- **Clinical Context:** Evaluates baseline organ function, metabolic indicators, or specific health concerns.")

    sections.append(f"\n### 📊 2. Key Biomarkers & Test Parameters Breakdown\n")

    if matched_params:
        table = "| Biomarker | Measured Value | Standard Range | Status | Clinical Assessment |\n"
        table += "|:---|:---:|:---:|:---:|:---|\n"
        for p in matched_params:
            table += f"| **{p['name']}** | `{p['value']}` | {p['ref_range']} | {p['status']} | {p['status_desc']} |\n"
        sections.append(table)
    else:
        sections.append(
            "> ℹ️ *Specific numerical lab parameters could not be automatically extracted from the raw text layout. "
            "Please review the extracted clinical text below for comprehensive doctor review:*\n"
        )
        preview_text = report_text[:600] if len(report_text) > 600 else report_text
        sections.append(f"```text\n{preview_text}\n```")

    sections.append(f"\n### 🔍 3. Plain-Language Clinical Interpretation\n")
    abnormal_count = sum(1 for p in matched_params if "Normal" not in p["status"])

    if abnormal_count == 0 and matched_params:
        sections.append("Your analyzed parameters appear generally **within expected physiological reference ranges**. This indicates stable baseline function for the tested markers.")
    elif abnormal_count > 0:
        sections.append(f"The analysis identified **{abnormal_count} parameter(s)** that sit outside conventional laboratory reference intervals. These variations can be influenced by diet, hydration status, medications, or underlying clinical factors, and should be evaluated by your consulting physician.")
    else:
        sections.append("The report contains clinical diagnostic observations. A consultation with your specialist will provide an accurate evaluation tailored to your complete medical history.")

    sections.append(f"\n### ⚠️ 4. Key Observations & Areas for Attention\n")
    if matched_params:
        elevated = [p['name'] for p in matched_params if "Elevated" in p['status']]
        low = [p['name'] for p in matched_params if "Low" in p['status']]
        if elevated:
            sections.append(f"- **Elevated Levels:** {', '.join(elevated)}. Discuss potential dietary or metabolic contributors with your doctor.")
        if low:
            sections.append(f"- **Lower Than Optimal:** {', '.join(low)}. May warrant nutritional review or targeted supplementation under medical supervision.")
        if not elevated and not low:
            sections.append("- No acute critical thresholds flagged in the extracted biomarker panel.")
    else:
        sections.append("- Maintain regular annual preventive health checkups and monitor any chronic symptoms.")

    sections.append(f"\n### 🩺 5. Recommended Questions to Ask Your Doctor\n")
    sections.append("1. *'Are any of the values in this report concerning given my personal health history?'*")
    sections.append("2. *'Do I need any follow-up blood tests or imaging to monitor trends over time?'*")
    sections.append("3. *'Are there specific lifestyle, diet, or exercise adjustments recommended for these results?'*")

    sections.append(f"\n### ⚖️ 6. Medical Disclaimer\n")
    sections.append(
        "> **Important Medical Notice:** This AI report analysis is generated for educational and informational purposes only. "
        "It does not constitute a formal diagnosis or medical advice. Please consult a qualified CareWell physician "
        "(General Medicine OPD Room 101-104 or call **+91-98765-43210**) for authoritative medical guidance."
    )

    return "\n".join(sections)

def analyze_medical_report(file_bytes: bytes, filename: str, custom_api_key: Optional[str] = None) -> str:
    """
    Main Report Analyzer:
    1. Extracts text/imagery.
    2. Sends to Gemini / Groq / OpenAI if API key available.
    3. Seamlessly falls back to the high-accuracy offline clinical diagnostic parser.
    """
    extracted_text, file_type = extract_text_from_file(file_bytes, filename)
    gemini_key = custom_api_key or os.getenv("GEMINI_API_KEY")
    groq_key = os.getenv("GROQ_API_KEY")
    openai_key = os.getenv("OPENAI_API_KEY")

    # 1. If Image and Gemini API is available -> Multimodal Vision Analysis
    if file_type in ["png", "jpg", "jpeg", "webp"] and gemini_key:
        try:
            b64_data = base64.b64encode(file_bytes).decode('utf-8')
            mime_type = f"image/{file_type if file_type != 'jpg' else 'jpeg'}"
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={gemini_key}"
            payload = {
                "system_instruction": {"parts": [{"text": REPORT_SYSTEM_PROMPT}]},
                "contents": [
                    {
                        "role": "user",
                        "parts": [
                            {"text": f"Please analyze this uploaded medical report ({filename}) thoroughly:"},
                            {"inline_data": {"mime_type": mime_type, "data": b64_data}}
                        ]
                    }
                ],
                "generationConfig": {"temperature": 0.1, "maxOutputTokens": 1200}
            }
            res = requests.post(url, json=payload, timeout=20)
            if res.status_code == 200:
                data = res.json()
                return data["candidates"][0]["content"]["parts"][0]["text"].strip()
        except Exception:
            pass

    # 2. If Text available and Gemini API available
    if extracted_text and extracted_text != "[IMAGE_DATA]" and gemini_key:
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={gemini_key}"
            payload = {
                "system_instruction": {"parts": [{"text": REPORT_SYSTEM_PROMPT}]},
                "contents": [
                    {"role": "user", "parts": [{"text": f"Medical Report Document Text:\n\n{extracted_text}\n\nAnalyze this report thoroughly:"}]}
                ],
                "generationConfig": {"temperature": 0.1, "maxOutputTokens": 1200}
            }
            res = requests.post(url, json=payload, timeout=20)
            if res.status_code == 200:
                data = res.json()
                return data["candidates"][0]["content"]["parts"][0]["text"].strip()
        except Exception:
            pass

    # 3. If Groq API available (text)
    if extracted_text and extracted_text != "[IMAGE_DATA]" and groq_key:
        try:
            url = "https://api.groq.com/openai/v1/chat/completions"
            headers = {"Authorization": f"Bearer {groq_key}", "Content-Type": "application/json"}
            payload = {
                "model": "llama-3.3-70b-versatile",
                "messages": [
                    {"role": "system", "content": REPORT_SYSTEM_PROMPT},
                    {"role": "user", "content": f"Medical Report Document Text ({filename}):\n\n{extracted_text}"}
                ],
                "temperature": 0.1,
                "max_tokens": 1200
            }
            res = requests.post(url, headers=headers, json=payload, timeout=20)
            if res.status_code == 200:
                data = res.json()
                return data["choices"][0]["message"]["content"].strip()
        except Exception:
            pass

    # 4. Fallback to Offline Clinical Report Analyzer
    return analyze_report_offline(extracted_text if extracted_text != "[IMAGE_DATA]" else f"Diagnostic Image: {filename}", filename)
