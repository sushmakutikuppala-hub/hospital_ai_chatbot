import os
import sys

# Ensure parent directory is in sys.path when run directly
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from database.db import get_db_connection, init_db

def seed_database():
    """Populates the database with initial hospital data if empty."""
    init_db()
    conn = get_db_connection()
    cursor = conn.cursor()

    # Check if already seeded
    existing_depts = cursor.execute("SELECT COUNT(*) FROM departments").fetchone()[0]
    if existing_depts > 0:
        conn.close()
        return

    # 1. Insert Departments
    departments = [
        ("General Medicine", "GENMED", "Ground Floor, Wing A", "Ext. 101", 
         "Comprehensive adult primary healthcare, fever, diabetes, hypertension, infectious diseases, and general health evaluations.", 
         "Dr. Rajesh Sharma"),
        
        ("Cardiology", "CARDIO", "1st Floor, Wing B", "Ext. 102", 
         "Complete cardiac care, ECG, Echo, TMT, angiography, heart failure management, and preventive heart clinics.", 
         "Dr. Sanjay Mehta"),
        
        ("Orthopedics", "ORTHO", "1st Floor, Wing C", "Ext. 103", 
         "Joint replacements, fracture management, spine care, sports injuries, and arthritis management.", 
         "Dr. Vivek Verma"),
        
        ("Pediatrics & Child Care", "PEDIA", "2nd Floor, Wing A", "Ext. 104", 
         "Newborn care, vaccinations, childhood infections, growth monitoring, and pediatric emergency care.", 
         "Dr. Pooja Sen"),
        
        ("Neurology", "NEURO", "2nd Floor, Wing B", "Ext. 105", 
         "Stroke care, epilepsy, migraine management, Parkinson's disease, and neuro-rehabilitation.", 
         "Dr. Sandeep Kulkarni"),
        
        ("Gynecology & Obstetrics", "GYNEC", "3rd Floor, Wing A", "Ext. 106", 
         "Antenatal care, high-risk pregnancy, normal & cesarean delivery, infertility, and women's wellness.", 
         "Dr. Meenakshi Sundaram"),
        
        ("Dermatology", "DERMA", "Ground Floor, Wing C", "Ext. 107", 
         "Skin conditions, acne, eczema, psoriasis, hair fall treatments, and allergy testing.", 
         "Dr. Sneha Kapoor"),
         
        ("Emergency & Trauma Care", "EMERG", "Ground Floor, Wing E (Dedicated Entrance)", "Ext. 999", 
         "24/7 Level 1 Trauma Care, Resuscitation, Cardiac Emergency, Stroke unit, and Emergency OT.", 
         "Dr. Arvind Menon")
    ]

    cursor.executemany("""
        INSERT INTO departments (name, code, floor_location, phone_extension, description, head_of_department)
        VALUES (?, ?, ?, ?, ?, ?)
    """, departments)
    conn.commit()

    # Fetch Department IDs
    dept_map = {row["name"]: row["id"] for row in cursor.execute("SELECT id, name FROM departments").fetchall()}

    # 2. Insert Doctors (Multiple General Physicians and other specialists)
    doctors = [
        # General Physicians / General Medicine
        ("Dr. Rajesh Sharma", dept_map["General Medicine"], 
         "General Physician / Internal Medicine", "MBBS, MD (General Medicine)", 16, 
         "Monday to Saturday", "09:00 AM - 01:00 PM & 05:00 PM - 08:00 PM", 600, "OPD Room 101", 1),
        
        ("Dr. Priya Nair", dept_map["General Medicine"], 
         "General Physician & Diabetologist", "MBBS, DNB (Internal Medicine), Fellowship in Diabetology", 12, 
         "Monday to Friday", "10:00 AM - 02:00 PM & 04:00 PM - 07:00 PM", 550, "OPD Room 102", 1),
         
        ("Dr. Arun Kumar", dept_map["General Medicine"], 
         "Consultant General Physician", "MBBS, MD (Medicine)", 9, 
         "Tuesday to Sunday", "08:30 AM - 12:30 PM & 03:30 PM - 06:30 PM", 500, "OPD Room 103", 1),

        ("Dr. Ananya Roy", dept_map["General Medicine"], 
         "General Physician & Infectious Disease Specialist", "MBBS, MD (Internal Medicine)", 11, 
         "Monday, Wednesday, Friday, Saturday", "01:00 PM - 05:00 PM", 600, "OPD Room 104", 1),

        # Cardiology
        ("Dr. Sanjay Mehta", dept_map["Cardiology"], 
         "Senior Interventional Cardiologist", "MBBS, MD, DM (Cardiology), FACC", 20, 
         "Monday to Friday", "10:00 AM - 02:00 PM", 1000, "OPD Room 201", 1),

        ("Dr. Kavita Rao", dept_map["Cardiology"], 
         "Consultant Cardiologist & Electrophysiologist", "MBBS, MD, DNB (Cardiology)", 14, 
         "Monday, Tuesday, Thursday, Saturday", "02:00 PM - 06:00 PM", 900, "OPD Room 202", 1),

        # Orthopedics
        ("Dr. Vivek Verma", dept_map["Orthopedics"], 
         "Senior Orthopedic & Joint Replacement Surgeon", "MBBS, MS (Orthopedics), MCh", 18, 
         "Monday to Saturday", "09:30 AM - 01:30 PM", 800, "OPD Room 205", 1),

        ("Dr. Sunita Patil", dept_map["Orthopedics"], 
         "Spine & Arthroscopy Specialist", "MBBS, DNB (Ortho), Fellowship in Spine", 10, 
         "Tuesday, Thursday, Saturday", "02:00 PM - 06:00 PM", 750, "OPD Room 206", 1),

        # Pediatrics
        ("Dr. Pooja Sen", dept_map["Pediatrics & Child Care"], 
         "Chief Pediatrician & Neonatologist", "MBBS, MD (Pediatrics), DCH", 15, 
         "Monday to Saturday", "09:00 AM - 01:00 PM & 05:00 PM - 07:30 PM", 650, "OPD Room 301", 1),

        ("Dr. Ramesh Iyer", dept_map["Pediatrics & Child Care"], 
         "Pediatrician & Child Allergy Specialist", "MBBS, DNB (Pediatrics)", 8, 
         "Monday to Friday", "02:00 PM - 06:00 PM", 500, "OPD Room 302", 1),

        # Neurology
        ("Dr. Sandeep Kulkarni", dept_map["Neurology"], 
         "Senior Neurologist & Stroke Specialist", "MBBS, MD, DM (Neurology)", 17, 
         "Monday, Wednesday, Friday", "10:00 AM - 02:00 PM", 1000, "OPD Room 305", 1),

        # Gynecology
        ("Dr. Meenakshi Sundaram", dept_map["Gynecology & Obstetrics"], 
         "Obstetrician & Senior Gynecological Surgeon", "MBBS, MS (OBG), DGO", 19, 
         "Monday to Saturday", "09:30 AM - 01:30 PM & 04:30 PM - 07:00 PM", 800, "OPD Room 401", 1),

        # Dermatology
        ("Dr. Sneha Kapoor", dept_map["Dermatology"], 
         "Consultant Dermatologist & Cosmetologist", "MBBS, MD (DVL)", 7, 
         "Monday to Friday", "11:00 AM - 03:00 PM", 600, "OPD Room 108", 1),

        # Emergency
        ("Dr. Arvind Menon", dept_map["Emergency & Trauma Care"], 
         "Head of Emergency Medicine & Trauma", "MBBS, FEM, MRCEM", 13, 
         "Available 24/7 on Rotational Shifts", "24 Hours Duty", 500, "Emergency Triage", 1)
    ]

    cursor.executemany("""
        INSERT INTO doctors (name, department_id, specialization, qualification, experience_years, visiting_days, timings, consultation_fee, room_no, is_available)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, doctors)
    conn.commit()

    # 3. Hospital Knowledge Chunks for RAG (Visiting hours, ICU, Emergency, Insurance, Pharmacy, Lab, Policies)
    knowledge_chunks = [
        ("Visiting Hours", "ICU & Critical Care Visiting Hours and Guidelines",
         "The Intensive Care Unit (ICU, ICCU, and NICU) visiting hours are strictly scheduled to minimize patient infection risk and ensure critical rest. "
         "Visiting Hours for ICU: "
         "- Morning Visiting Slot: 11:00 AM to 01:00 PM "
         "- Evening Visiting Slot: 05:00 PM to 07:00 PM "
         "ICU Rules: Only one visitor is permitted by the patient's bedside at a time using an authorized ICU Visitor Pass. "
         "Visitors must sanitize hands, wear provided shoe covers and mask before entering. "
         "Children under 12 years are not permitted inside the ICU for health safety reasons. "
         "Doctor ICU briefing to immediate family occurs daily at 12:30 PM and 06:30 PM.",
         "icu visiting hours, icu timings, visiting patient in icu, critical care timings, see icu patient, intensive care hours"),

        ("Visiting Hours", "General Ward and Private Room Visiting Timings",
         "Visiting hours for In-Patient General Wards and Private Rooms: "
         "- Evening Visiting Hours: 04:00 PM to 07:00 PM daily. "
         "- Morning Visiting Hours: 10:00 AM to 12:00 PM (Sundays & Public Holidays only). "
         "Rules: One permanent Attendant Pass is issued per admitted patient, allowing 24/7 stay beside the patient. "
         "Up to 2 additional visitors are permitted during the visiting hours. Outside cooked food and cut fruits are strictly restricted.",
         "general ward visiting hours, visiting timings, patient visiting hours, room visiting timings, visiting time"),

        ("Emergency & Ambulance", "24/7 Emergency, Trauma and Ambulance Contact",
         "CareWell Hospital operates a 24/7 Level-1 Emergency & Trauma Care Department with dedicated resuscitation bays, cardiac care, and stroke rapid response. "
         "- Emergency Helpline & 24/7 Trauma Desk: +91-98765-43210 "
         "- Dedicated Ambulance Dispatch: +91-98765-43299 or Toll-Free 108 / 1800-200-CARE "
         "- Emergency Location: Ground Floor, Wing E with direct separate ambulance ramp and emergency drop-off. "
         "No prior appointment or registration delay is required for acute emergency cases.",
         "emergency, ambulance, urgent, accident, trauma, casualty, 24/7, emergency phone number, ambulance contact, heart attack"),

        ("Pharmacy", "24-Hour Hospital Pharmacy and Medicine Dispensary",
         "The CareWell 24/7 In-House Pharmacy is located on the Ground Floor near the Main Reception. "
         "- Working Hours: Open 24 Hours, 365 Days a year. "
         "- Services: Prescription medicines, critical care injectables, medical surgical supplies, orthopedic braces, and baby care essentials. "
         "- Home Delivery Service: Free delivery within a 5 km radius for orders above ₹500 (Call Ext. 109 or WhatsApp +91-98765-43220). "
         "- Discounts: Senior citizens receive a flat 10% discount on regular prescription medicines.",
         "pharmacy, medical store, medicines, chemist, pharmacy timings, buy medicines, 24 hour pharmacy"),

        ("Diagnostics & Lab", "Diagnostic Laboratory, Pathology and Radiology Timings",
         "CareWell Central Diagnostic & Radiology Center offers NABL-accredited diagnostic services. "
         "- Blood Collection & Pathology Lab: 07:00 AM to 09:00 PM (Emergency testing 24/7). "
         "  Fasting blood sugar and lipid profiles should ideally be given between 07:00 AM and 09:30 AM after 10-12 hours of fasting. "
         "- Radiology (Digital X-Ray, CT Scan, 3T MRI, Ultrasound): Routine OPD scans run from 08:00 AM to 08:00 PM. Emergency trauma scans run 24/7. "
         "- Reports: Test reports are delivered via SMS link, WhatsApp, and can also be downloaded from the hospital portal within 4 to 24 hours.",
         "lab timings, blood test, pathology, mri, ct scan, x-ray, ultrasound, test reports, fasting blood test, diagnostics"),

        ("Insurance & Billing", "Cashless Mediclaim, TPA and Health Insurance Partners",
         "CareWell Hospital has tie-ups with leading health insurance providers and Third-Party Administrators (TPAs) for cashless hospitalization. "
         "- Network Insurance Partners: Star Health, HDFC ERGO, Care Health Insurance, Niva Bupa (Max Bupa), ICICI Lombard, Bajaj Allianz, New India Assurance, Oriental Insurance, United India, National Insurance. "
         "- Government Schemes: Ayushman Bharat (PM-JAY), CGHS, and State Government Health Schemes. "
         "- Cashless TPA Desk: Located on Ground Floor, Counter 5 (Open 08:00 AM to 08:00 PM daily). For emergency admissions, cashless pre-authorization is available 24/7. "
         "- Documents Required: Patient Health Card/Policy Copy, Aadhaar/Govt Photo ID, Doctor's Admission Slip.",
         "insurance, cashless, mediclaim, tpa, star health, hdfc ergo, ayushman bharat, policy, billing, cashless desk"),

        ("Appointments", "Doctor Consultation and Appointment Booking Guidelines",
         "Out-Patient Department (OPD) consultations are scheduled between 08:30 AM and 08:00 PM from Monday to Saturday. "
         "- You can book appointments directly with our Virtual Receptionist chatbot, or call our Reception Desk at +91-98765-43211. "
         "- Walk-in consultations are welcome, subject to token availability. "
         "- General Physician consultation fee is ₹500 - ₹600. Super-specialist consultation fee ranges from ₹800 - ₹1000. "
         "- Follow-up consultations within 7 days with the same doctor are free of charge.",
         "book appointment, consultation fee, doctor appointment, opd timings, walk in consultation, follow up"),

        ("Hospital Address & Location", "Hospital Location, Parking and Campus Facilities",
         "CareWell Multi-Specialty Hospital Campus: "
         "- Address: 45 Healthcare Boulevard, Medical Enclave, Tech City - 560001 (Near City Central Metro Station, Exit 2). "
         "- Parking: 3-level basement parking with 300+ car parking slots. Free valet parking available for Senior Citizens, Disabled Patients, and Emergency Arrivals. "
         "- Cafeteria (NutriDine): Located on 3rd Floor, serving healthy, dietitian-approved meals from 07:00 AM to 10:00 PM. "
         "- ATM & Banking: 24/7 SBI and HDFC ATMs located at Main Entrance.",
         "hospital address, location, how to reach, directions, parking, cafeteria, atm, floor, metro station"),

        ("Admission & Discharge", "In-Patient Admission and Discharge Protocol",
         "Admission Procedure: "
         "- Report to Admission Counter 3 on Ground Floor with the doctor's admission recommendation form. "
         "- Options: General Ward, Semi-Private, Single Deluxe, and Super Deluxe suites. "
         "Discharge Protocol: "
         "- Routine discharge processing starts at 10:00 AM and concludes by 01:00 PM. "
         "- Summary sheets, follow-up medication instructions, and bills are finalized at Counter 4.",
         "admission process, discharge timings, hospital rooms, general ward, deluxe room, discharge summary")
    ]

    cursor.executemany("""
        INSERT INTO hospital_knowledge (category, title, content, keywords)
        VALUES (?, ?, ?, ?)
    """, knowledge_chunks)
    conn.commit()

    conn.close()
    print("Hospital database successfully seeded with departments, doctors, and knowledge chunks.")

if __name__ == "__main__":
    seed_database()
