import os
import uuid
from typing import Optional, List, Dict, Any
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request, UploadFile, File, Form, Header, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from dotenv import load_dotenv

# Load environment variables from .env if present
load_dotenv()

from database.db import (
    init_db,
    get_all_departments,
    get_all_doctors,
    search_doctors_by_department,
    create_appointment,
    log_chat_message,
    register_user,
    login_user,
    get_user_by_token,
    save_medical_report,
    get_user_medical_reports
)
from database.seed_data import seed_database
from rag.retriever import HospitalKnowledgeRetriever
from rag.generator import generate_llm_response
from reports.analyzer import analyze_medical_report


# Global retriever instance
retriever_instance = None
# Lifespan event for automatic database initialization and seeding
@asynccontextmanager
async def lifespan(app: FastAPI):
    global retriever_instance

    # Step 1: Create database and tables
    init_db()
    print("Database initialized.")

    # Step 2: Insert initial hospital data
    seed_database()
    print("Database seeded.")

    # Step 3: Initialize RAG retriever AFTER database setup
    retriever_instance = HospitalKnowledgeRetriever()
    print("RAG retriever initialized.")

    print("CareWell Hospital AI Receptionist & Clinical System Initialized.")

    yield
    
app = FastAPI(
    title="CareWell Hospital AI Receptionist & Health Portal",
    description="Full-stack AI Healthcare System with RAG, Gmail-Only Authentication Gate, and Medical Report Analysis",
    version="2.1.0",
    lifespan=lifespan
)

# Enable CORS for flexible integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ----------------- Auth Helper: Enforce Login for Bot ----------------- #

def get_authenticated_user(authorization: Optional[str] = Header(None)) -> Dict[str, Any]:
    """
    Ensures that only logged-in users with a valid Gmail session can access protected features.
    """
    if not authorization:
        raise HTTPException(
            status_code=401,
            detail="Authentication required. Please sign in with your @gmail.com account to access the hospital assistant."
        )
    token = authorization.replace("Bearer ", "").strip()
    user = get_user_by_token(token)
    if not user:
        raise HTTPException(
            status_code=401,
            detail="Session expired or invalid login. Please sign in with your @gmail.com account."
        )
    return user

# ----------------- Request / Response Schemas ----------------- #

class ChatRequest(BaseModel):
    message: str = Field(..., example="who and all doctor working for general physician")
    session_id: Optional[str] = Field(default=None)
    api_key: Optional[str] = Field(default=None, description="Optional Google Gemini API Key")

class AppointmentRequest(BaseModel):
    patient_name: str
    patient_phone: str
    doctor_id: int
    appointment_date: str
    appointment_time: str
    reason: Optional[str] = ""

class RegisterRequest(BaseModel):
    email: str = Field(..., example="patient@gmail.com")
    password: str = Field(..., min_length=4)
    full_name: Optional[str] = ""

class LoginRequest(BaseModel):
    email: str = Field(..., example="patient@gmail.com")
    password: str = Field(..., min_length=1)

# ----------------- Public Auth Endpoints (Gmail Only) ----------------- #

@app.post("/api/auth/register")
def register_endpoint(req: RegisterRequest):
    """
    Registers a new user.
    Validation rules:
    - Domain must strictly be @gmail.com (no username or phone number registration).
    - Existing registered emails are rejected.
    """
    try:
        user_info = register_user(
            email=req.email,
            password=req.password,
            full_name=req.full_name
        )
        return {
            "success": True,
            "message": "Account registered successfully with Gmail ID.",
            "user": {
                "id": user_info["user_id"],
                "email": user_info["email"],
                "full_name": user_info["full_name"]
            },
            "token": user_info["token"]
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Registration error: {str(e)}")

@app.post("/api/auth/login")
def login_endpoint(req: LoginRequest):
    """
    Authenticates user strictly with @gmail.com email and password.
    """
    try:
        user_info = login_user(email=req.email, password=req.password)
        return {
            "success": True,
            "message": "Login successful.",
            "user": {
                "id": user_info["user_id"],
                "email": user_info["email"],
                "full_name": user_info["full_name"]
            },
            "token": user_info["token"]
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Login error: {str(e)}")

@app.get("/api/auth/me")
def get_current_user(user: Dict[str, Any] = Depends(get_authenticated_user)):
    """Verifies session token and returns active user profile."""
    return {"user": user}

# ----------------- Protected Medical Report Analysis Endpoints ----------------- #

@app.post("/api/reports/upload")
async def upload_and_analyze_report(
    file: UploadFile = File(...),
    user_email: Optional[str] = Form(None),
    api_key: Optional[str] = Form(None),
    user: Dict[str, Any] = Depends(get_authenticated_user)
):
    """
    Protected Endpoint: Accepts medical lab report from logged-in user.
    Analyzes parameters, reference ranges, and clinical interpretation using AI.
    Saves analysis result in SQLite database linked to user.
    """
    try:
        file_bytes = await file.read()
        filename = file.filename or "medical_report"

        if len(file_bytes) == 0:
            raise HTTPException(status_code=400, detail="Uploaded file is empty.")

        # Run Comprehensive AI / Clinical Report Analysis
        analysis_markdown = analyze_medical_report(
            file_bytes=file_bytes,
            filename=filename,
            custom_api_key=api_key
        )

        # Save to database
        saved_report = save_medical_report(
            user_email=user["email"],
            filename=filename,
            file_type=file.content_type or "document",
            extracted_text="",
            analysis_result=analysis_markdown
        )

        return {
            "success": True,
            "report_id": saved_report["id"],
            "filename": filename,
            "analysis": analysis_markdown
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to analyze report: {str(e)}")

@app.get("/api/reports/history")
def get_reports_history(user_email: str, user: Dict[str, Any] = Depends(get_authenticated_user)):
    """Protected Endpoint: Retrieves previous analyzed reports for the logged-in user."""
    reports = get_user_medical_reports(user["email"])
    return {"reports": reports}

# ----------------- Protected Receptionist Bot & Appointment Endpoints ----------------- #

@app.post("/api/chat")
def chat_endpoint(req: ChatRequest, user: Dict[str, Any] = Depends(get_authenticated_user)):
    """
    Protected RAG Chat Endpoint:
    ACCESSIBLE ONLY TO AUTHENTICATED GMAIL USERS.
    1. Hybrid Retrieval: Queries doctors + BM25 knowledge chunks
    2. Augmented Generation: Generates receptionist response via AI or local synthesizer
    3. Persists conversation log in SQLite
    """
    user_query = req.message.strip()
    session_id = req.session_id or str(uuid.uuid4())

    if not user_query:
        raise HTTPException(status_code=400, detail="Query cannot be empty.")

    # 1. Hybrid RAG Retrieval Step
    rag_context = retriever_instance.get_rag_context(user_query)

    # 2. Augmented Generation Step
    response_text = generate_llm_response(
        query=user_query,
        rag_context=rag_context,
        custom_api_key=req.api_key
    )

    # 3. Log to SQLite
    log_chat_message(session_id, user["email"], user_query)
    log_chat_message(session_id, "receptionist", response_text)

    return {
        "session_id": session_id,
        "query": user_query,
        "response": response_text,
        "matched_doctors": rag_context.get("matched_doctors", []),
        "knowledge_chunks": rag_context.get("knowledge_chunks", []),
        "is_emergency": rag_context.get("is_emergency", False),
        "is_appointment": rag_context.get("is_appointment", False)
    }

@app.post("/api/appointment")
def book_appointment_endpoint(req: AppointmentRequest, user: Dict[str, Any] = Depends(get_authenticated_user)):
    """Protected Endpoint: Books consultation appointment for logged-in patient."""
    try:
        booking = create_appointment(
            patient_name=req.patient_name,
            patient_phone=req.patient_phone,
            doctor_id=req.doctor_id,
            appointment_date=req.appointment_date,
            appointment_time=req.appointment_time,
            reason=req.reason or ""
        )
        return {"success": True, "appointment": booking}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# ----------------- Hospital Directory Info Endpoints ----------------- #

@app.get("/api/info")
def get_hospital_info():
    """Returns general hospital contact and operational info."""
    return {
        "hospital_name": "CareWell Multi-Specialty Hospital",
        "tagline": "Compassionate Care, Advanced Medicine",
        "address": "45 Healthcare Boulevard, Medical Enclave, Tech City - 560001",
        "emergency_helpline": "+91-98765-43210",
        "ambulance": "108 / +91-98765-43299",
        "reception_desk": "+91-98765-43211",
        "icu_visiting_hours": "Morning: 11:00 AM - 01:00 PM | Evening: 05:00 PM - 07:00 PM",
        "general_ward_visiting_hours": "Evening: 04:00 PM - 07:00 PM daily",
        "pharmacy": "Open 24/7 (Ground Floor)",
        "diagnostics": "Pathology 07:00 AM - 09:00 PM | Radiology 24/7 Emergency"
    }

@app.get("/api/departments")
def list_departments():
    """Returns all departments with floor locations and extensions."""
    return get_all_departments()

@app.get("/api/doctors")
def list_doctors(department: Optional[str] = None):
    """Returns all doctors or doctors filtered by department / specialization."""
    if department:
        return search_doctors_by_department(department)
    return get_all_doctors()

@app.get("/health")
def health_check():
    """Health check endpoint for Render / Vercel keep-alive."""
    return {"status": "healthy", "service": "carewell-hospital-ai"}

# Mount Static Files (Frontend UI)
static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

@app.get("/")
def serve_frontend():
    """Serves the main HTML interface."""
    index_path = os.path.join(static_dir, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return JSONResponse({"message": "Frontend index.html not found"}, status_code=404)

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 5000))
    uvicorn.run("app:app", host="127.0.0.1", port=port, reload=True)
