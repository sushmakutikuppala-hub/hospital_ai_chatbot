import sqlite3
import os
import hashlib
import uuid
from typing import List, Dict, Any, Optional

DB_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "hospital.db")

def get_db_connection() -> sqlite3.Connection:
    """Creates and returns a connection to the SQLite database with Row factory."""
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initializes the database schema if tables do not exist."""
    conn = get_db_connection()
    cursor = conn.cursor()

    # 1. Departments Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS departments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE NOT NULL,
        code TEXT UNIQUE NOT NULL,
        floor_location TEXT NOT NULL,
        phone_extension TEXT,
        description TEXT,
        head_of_department TEXT
    );
    """)

    # 2. Doctors Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS doctors (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        department_id INTEGER NOT NULL,
        specialization TEXT NOT NULL,
        qualification TEXT NOT NULL,
        experience_years INTEGER NOT NULL,
        visiting_days TEXT NOT NULL,
        timings TEXT NOT NULL,
        consultation_fee INTEGER NOT NULL,
        room_no TEXT NOT NULL,
        is_available INTEGER DEFAULT 1,
        FOREIGN KEY (department_id) REFERENCES departments(id) ON DELETE CASCADE
    );
    """)

    # 3. Hospital Knowledge Table (For RAG knowledge retrieval)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS hospital_knowledge (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        category TEXT NOT NULL,
        title TEXT NOT NULL,
        content TEXT NOT NULL,
        keywords TEXT NOT NULL
    );
    """)

    # 4. Appointments Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS appointments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        patient_name TEXT NOT NULL,
        patient_phone TEXT NOT NULL,
        doctor_id INTEGER NOT NULL,
        doctor_name TEXT NOT NULL,
        department_name TEXT NOT NULL,
        appointment_date TEXT NOT NULL,
        appointment_time TEXT NOT NULL,
        reason TEXT,
        status TEXT DEFAULT 'Confirmed',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (doctor_id) REFERENCES doctors(id)
    );
    """)

    # 5. Chat History / Audit Logs
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS chat_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id TEXT NOT NULL,
        sender TEXT NOT NULL,
        message TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # 6. Users Table (Email-only login, strictly @gmail.com)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        salt TEXT NOT NULL,
        full_name TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # 7. User Sessions Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS user_sessions (
        token TEXT PRIMARY KEY,
        user_id INTEGER NOT NULL,
        email TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
    );
    """)

    # 8. Medical Reports Table (Stores uploaded report files & AI analysis)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS medical_reports (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        user_email TEXT,
        filename TEXT NOT NULL,
        file_type TEXT NOT NULL,
        extracted_text TEXT,
        analysis_result TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id)
    );
    """)

    conn.commit()
    conn.close()

# ----------------- User Authentication Helpers ----------------- #

def hash_password(password: str, salt: Optional[str] = None) -> (str, str):
    """Hashes password with SHA256 and unique salt."""
    if not salt:
        salt = uuid.uuid4().hex
    salted = f"{password}{salt}".encode('utf-8')
    pwd_hash = hashlib.sha256(salted).hexdigest()
    return pwd_hash, salt

def validate_gmail(email: str) -> str:
    """Validates that email strictly belongs to @gmail.com domain."""
    email_clean = email.strip().lower()
    if not email_clean.endswith("@gmail.com"):
        raise ValueError("Invalid email domain. Only @gmail.com addresses are permitted (e.g. yourname@gmail.com).")
    
    local_part = email_clean[:-10]
    if not local_part or len(local_part) < 2:
        raise ValueError("Invalid Gmail username. Please enter a valid Gmail address.")
    
    return email_clean

def register_user(email: str, password: str, full_name: Optional[str] = None) -> Dict[str, Any]:
    """
    Registers a new user with strict @gmail.com validation.
    Rejects registration if email already exists in DB.
    """
    email_clean = validate_gmail(email)

    if not password or len(password) < 4:
        raise ValueError("Password must be at least 4 characters long.")

    conn = get_db_connection()
    cursor = conn.cursor()

    # Check if user already exists
    existing = cursor.execute("SELECT id FROM users WHERE email = ?", (email_clean,)).fetchone()
    if existing:
        conn.close()
        raise ValueError("This Gmail address is already registered. Please login instead.")

    pwd_hash, salt = hash_password(password)
    display_name = full_name.strip() if full_name else email_clean.split('@')[0].capitalize()

    cursor.execute("""
        INSERT INTO users (email, password_hash, salt, full_name)
        VALUES (?, ?, ?, ?)
    """, (email_clean, pwd_hash, salt, display_name))
    
    user_id = cursor.lastrowid
    
    # Create initial session token
    token = str(uuid.uuid4())
    cursor.execute("""
        INSERT INTO user_sessions (token, user_id, email)
        VALUES (?, ?, ?)
    """, (token, user_id, email_clean))

    conn.commit()
    conn.close()

    return {
        "user_id": user_id,
        "email": email_clean,
        "full_name": display_name,
        "token": token
    }

def login_user(email: str, password: str) -> Dict[str, Any]:
    """
    Authenticates user strictly with @gmail.com email and password.
    """
    email_clean = validate_gmail(email)

    conn = get_db_connection()
    cursor = conn.cursor()

    user = cursor.execute("SELECT * FROM users WHERE email = ?", (email_clean,)).fetchone()
    if not user:
        conn.close()
        raise ValueError("No account found with this Gmail address. Please register first.")

    # Verify password hash
    expected_hash, _ = hash_password(password, user["salt"])
    if expected_hash != user["password_hash"]:
        conn.close()
        raise ValueError("Incorrect password. Please verify your credentials.")

    # Generate new session token
    token = str(uuid.uuid4())
    cursor.execute("""
        INSERT INTO user_sessions (token, user_id, email)
        VALUES (?, ?, ?)
    """, (token, user["id"], email_clean))

    conn.commit()
    conn.close()

    return {
        "user_id": user["id"],
        "email": user["email"],
        "full_name": user["full_name"],
        "token": token
    }

def get_user_by_token(token: str) -> Optional[Dict[str, Any]]:
    """Retrieves user profile associated with session token."""
    if not token:
        return None
    conn = get_db_connection()
    row = conn.execute("""
        SELECT u.id, u.email, u.full_name, u.created_at
        FROM users u
        JOIN user_sessions s ON u.id = s.user_id
        WHERE s.token = ?
    """, (token,)).fetchone()
    conn.close()
    return dict(row) if row else None

# ----------------- Medical Reports Helpers ----------------- #

def save_medical_report(user_email: Optional[str], filename: str, file_type: str, 
                        extracted_text: str, analysis_result: str) -> Dict[str, Any]:
    """Saves uploaded report text and AI analysis to DB."""
    conn = get_db_connection()
    cursor = conn.cursor()

    user_id = None
    if user_email:
        u = cursor.execute("SELECT id FROM users WHERE email = ?", (user_email,)).fetchone()
        if u:
            user_id = u["id"]

    cursor.execute("""
        INSERT INTO medical_reports (user_id, user_email, filename, file_type, extracted_text, analysis_result)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (user_id, user_email or "Guest", filename, file_type, extracted_text, analysis_result))

    report_id = cursor.lastrowid
    conn.commit()
    conn.close()

    return {
        "id": report_id,
        "filename": filename,
        "user_email": user_email,
        "analysis_result": analysis_result
    }

def get_user_medical_reports(user_email: str) -> List[Dict[str, Any]]:
    """Fetches past report analyses for a user."""
    conn = get_db_connection()
    rows = conn.execute("""
        SELECT id, filename, file_type, analysis_result, created_at
        FROM medical_reports
        WHERE user_email = ?
        ORDER BY created_at DESC
    """, (user_email,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]

# ----------------- Hospital Query Helpers ----------------- #

def get_all_departments() -> List[Dict[str, Any]]:
    conn = get_db_connection()
    rows = conn.execute("SELECT * FROM departments ORDER BY name ASC").fetchall()
    conn.close()
    return [dict(row) for row in rows]

def get_all_doctors() -> List[Dict[str, Any]]:
    conn = get_db_connection()
    query = """
    SELECT d.id, d.name, d.specialization, d.qualification, d.experience_years,
           d.visiting_days, d.timings, d.consultation_fee, d.room_no, d.is_available,
           dept.name as department_name, dept.floor_location
    FROM doctors d
    JOIN departments dept ON d.department_id = dept.id
    ORDER BY dept.name, d.name
    """
    rows = conn.execute(query).fetchall()
    conn.close()
    return [dict(row) for row in rows]

def search_doctors_by_department(dept_keyword: str) -> List[Dict[str, Any]]:
    """Searches doctors matching department name, specialization, or doctor name."""
    conn = get_db_connection()
    keyword = f"%{dept_keyword.strip()}%"
    query = """
    SELECT d.id, d.name, d.specialization, d.qualification, d.experience_years,
           d.visiting_days, d.timings, d.consultation_fee, d.room_no, d.is_available,
           dept.name as department_name, dept.floor_location
    FROM doctors d
    JOIN departments dept ON d.department_id = dept.id
    WHERE dept.name LIKE ? 
       OR d.specialization LIKE ? 
       OR d.name LIKE ?
    ORDER BY d.name
    """
    rows = conn.execute(query, (keyword, keyword, keyword)).fetchall()
    conn.close()
    return [dict(row) for row in rows]

def get_all_knowledge_chunks() -> List[Dict[str, Any]]:
    conn = get_db_connection()
    rows = conn.execute("SELECT * FROM hospital_knowledge").fetchall()
    conn.close()
    return [dict(row) for row in rows]

def create_appointment(patient_name: str, patient_phone: str, doctor_id: int, 
                       appointment_date: str, appointment_time: str, reason: str = "") -> Dict[str, Any]:
    conn = get_db_connection()
    doc = conn.execute("""
        SELECT d.name as doctor_name, dept.name as dept_name 
        FROM doctors d 
        JOIN departments dept ON d.department_id = dept.id 
        WHERE d.id = ?
    """, (doctor_id,)).fetchone()

    if not doc:
        conn.close()
        raise ValueError(f"Doctor with ID {doctor_id} not found")

    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO appointments (patient_name, patient_phone, doctor_id, doctor_name, department_name, appointment_date, appointment_time, reason)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (patient_name, patient_phone, doctor_id, doc["doctor_name"], doc["dept_name"], appointment_date, appointment_time, reason))
    
    app_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return {
        "id": app_id,
        "patient_name": patient_name,
        "doctor_name": doc["doctor_name"],
        "department": doc["dept_name"],
        "appointment_date": appointment_date,
        "appointment_time": appointment_time,
        "status": "Confirmed"
    }

def log_chat_message(session_id: str, sender: str, message: str):
    try:
        conn = get_db_connection()
        conn.execute("INSERT INTO chat_logs (session_id, sender, message) VALUES (?, ?, ?)",
                     (session_id, sender, message))
        conn.commit()
        conn.close()
    except Exception:
        pass
