from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from enum import Enum
import logging
import os
from contextlib import contextmanager

import psycopg2
from psycopg2.extras import RealDictCursor
import jwt
import hashlib
import uuid

# ============================================================================
# CONFIGURATION & SETUP
# ============================================================================

app = FastAPI(
    title="Clinic SaaS API",
    description="Medical clinic management system",
    version="1.0.0"
)

# CORS Configuration - Allow frontend
FRONTEND_URLS = [
    "http://localhost:3000",
	"http://localhost:8000"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=FRONTEND_URLS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuration
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", "5432"))
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
DB_NAME = os.getenv("DB_NAME", "clinic_saas")
JWT_SECRET = os.getenv("JWT_SECRET", "your-secret-key-change-in-production")
JWT_ALGORITHM = "HS256"
TOKEN_EXPIRY_HOURS = 24

# ============================================================================
# ENUMS
# ============================================================================

class UserRole(str, Enum):
    ADMIN = "admin"
    DOCTOR = "doctor"
    RECEPTIONIST = "receptionist"
    PATIENT = "patient"

class AppointmentStatus(str, Enum):
    SCHEDULED = "scheduled"
    COMPLETED = "completed"
    CANCELLED = "cancelled"

class BillingStatus(str, Enum):
    PENDING = "pending"
    PAID = "paid"
    CANCELLED = "cancelled"

# ============================================================================
# PYDANTIC MODELS (Request/Response Schemas)
# ============================================================================

class UserRegister(BaseModel):
    username: str = Field(..., min_length=3, max_length=255)
    email: EmailStr
    password: str = Field(..., min_length=6)
    role: UserRole = UserRole.PATIENT

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserResponse(BaseModel):
    id: str
    username: str
    email: str
    role: UserRole

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse

class PatientCreate(BaseModel):
    user_id: str
    first_name: str
    last_name: str
    date_of_birth: Optional[str] = None
    gender: Optional[str] = None
    contact_number: Optional[str] = None
    email: str
    address: Optional[str] = None
    medical_history: Optional[Dict[str, Any]] = {}

class PatientResponse(BaseModel):
    id: str
    user_id: str
    first_name: str
    last_name: str
    date_of_birth: Optional[str]
    gender: Optional[str]
    contact_number: Optional[str]
    email: str
    address: Optional[str]
    medical_history: Optional[Dict]
    created_at: str

class DoctorCreate(BaseModel):
    user_id: str
    first_name: str
    last_name: str
    specialty: str
    license_number: str
    contact_number: Optional[str] = None
    email: str
    clinic_id: Optional[str] = None

class DoctorResponse(BaseModel):
    id: str
    user_id: str
    first_name: str
    last_name: str
    specialty: str
    license_number: str
    contact_number: Optional[str]
    email: str
    clinic_id: Optional[str]
    created_at: str

class AppointmentCreate(BaseModel):
    patient_id: str
    doctor_id: str
    clinic_id: str
    start_time: str
    end_time: str
    notes: Optional[str] = None

class AppointmentUpdate(BaseModel):
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    status: Optional[AppointmentStatus] = None
    notes: Optional[str] = None

class AppointmentResponse(BaseModel):
    id: str
    patient_id: str
    doctor_id: str
    clinic_id: str
    start_time: str
    end_time: str
    status: AppointmentStatus
    notes: Optional[str]
    created_at: str

class MedicalRecordCreate(BaseModel):
    patient_id: str
    doctor_id: str
    appointment_id: Optional[str] = None
    diagnosis: str
    treatment: str
    prescription: Optional[Dict[str, Any]] = {}
    notes: Optional[str] = None

class MedicalRecordResponse(BaseModel):
    id: str
    patient_id: str
    doctor_id: str
    appointment_id: Optional[str]
    diagnosis: str
    treatment: str
    prescription: Optional[Dict]
    notes: Optional[str]
    created_at: str

class BillingCreate(BaseModel):
    patient_id: str
    appointment_id: Optional[str] = None
    amount: float = Field(..., gt=0)
    status: BillingStatus = BillingStatus.PENDING

class BillingUpdate(BaseModel):
    amount: Optional[float] = None
    status: Optional[BillingStatus] = None

class BillingResponse(BaseModel):
    id: str
    patient_id: str
    appointment_id: Optional[str]
    amount: float
    status: BillingStatus
    created_at: str

class ClinicCreate(BaseModel):
    name: str
    address: str
    contact_number: Optional[str] = None
    email: Optional[str] = None

class ClinicResponse(BaseModel):
    id: str
    name: str
    address: str
    contact_number: Optional[str]
    email: Optional[str]
    created_at: str

# ============================================================================
# DATABASE UTILITIES
# ============================================================================

@contextmanager
def get_db_connection():
    """Context manager for database connections"""
    conn = None
    try:
        conn = psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            user=DB_USER,
            password=DB_PASSWORD,
            database=DB_NAME
        )
        yield conn
    except psycopg2.Error as e:
        logger.error(f"Database connection error: {e}")
        raise HTTPException(status_code=500, detail="Database connection failed")
    finally:
        if conn:
            conn.close()

def dict_from_row(cursor, row):
    """Convert database row to dictionary"""
    return dict(zip([desc[0] for desc in cursor.description], row))

# ============================================================================
# AUTHENTICATION & SECURITY
# ============================================================================

def hash_password(password: str) -> str:
    """Hash password using SHA-256"""
    return hashlib.sha256(password.encode()).hexdigest()

def create_jwt_token(user_id: str, email: str, role: UserRole) -> str:
    """Create JWT token"""
    payload = {
        "user_id": user_id,
        "email": email,
        "role": role.value,
        "exp": datetime.utcnow() + timedelta(hours=TOKEN_EXPIRY_HOURS),
        "iat": datetime.utcnow()
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

def verify_jwt_token(token: str) -> Dict[str, Any]:
    """Verify and decode JWT token"""
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

def get_current_user(authorization: Optional[str] = None) -> Dict[str, Any]:
    """Extract and verify current user from Authorization header"""
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing authorization header")
    
    try:
        scheme, token = authorization.split()
        if scheme.lower() != "bearer":
            raise HTTPException(status_code=401, detail="Invalid authorization scheme")
        return verify_jwt_token(token)
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid authorization header format")

# ============================================================================
# AUTH ENDPOINTS
# ============================================================================

@app.post("/users/register", response_model=TokenResponse)
async def register(user_data: UserRegister):
    """Register a new user"""
    user_id = str(uuid.uuid4())
    password_hash = hash_password(user_data.password)
    
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                # Check if email already exists
                cur.execute("SELECT id FROM users WHERE email = %s", (user_data.email,))
                if cur.fetchone():
                    raise HTTPException(status_code=400, detail="Email already registered")
                
                # Insert new user
                cur.execute(
                    """INSERT INTO users (id, username, email, password_hash, role, created_at, updated_at)
                       VALUES (%s, %s, %s, %s, %s, NOW(), NOW())""",
                    (user_id, user_data.username, user_data.email, password_hash, user_data.role.value)
                )
                conn.commit()
                logger.info(f"User registered: {user_data.email}")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Registration error: {e}")
        raise HTTPException(status_code=500, detail="Registration failed")
    
    # Generate token
    token = create_jwt_token(user_id, user_data.email, user_data.role)
    return TokenResponse(
        access_token=token,
        user=UserResponse(
            id=user_id,
            username=user_data.username,
            email=user_data.email,
            role=user_data.role
        )
    )

@app.post("/users/login", response_model=TokenResponse)
async def login(credentials: UserLogin):
    """Login user"""
    password_hash = hash_password(credentials.password)
    
    try:
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    "SELECT id, username, email, role FROM users WHERE email = %s AND password_hash = %s",
                    (credentials.email, password_hash)
                )
                user = cur.fetchone()
                
                if not user:
                    raise HTTPException(status_code=401, detail="Invalid email or password")
                
                logger.info(f"Login successful: {credentials.email}")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login error: {e}")
        raise HTTPException(status_code=500, detail="Login failed")
    
    # Generate token
    token = create_jwt_token(user['id'], user['email'], UserRole(user['role']))
    return TokenResponse(
        access_token=token,
        user=UserResponse(
            id=user['id'],
            username=user['username'],
            email=user['email'],
            role=UserRole(user['role'])
        )
    )

# ============================================================================
# PATIENT ENDPOINTS
# ============================================================================

@app.post("/patients", response_model=PatientResponse)
async def create_patient(patient_data: PatientCreate, authorization: Optional[str] = None):
    """Create a new patient"""
    current_user = get_current_user(authorization)
    patient_id = str(uuid.uuid4())
    
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """INSERT INTO patients 
                       (id, user_id, first_name, last_name, date_of_birth, gender, contact_number, email, address, medical_history, created_at, updated_at)
                       VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW())""",
                    (patient_id, patient_data.user_id, patient_data.first_name, patient_data.last_name,
                     patient_data.date_of_birth, patient_data.gender, patient_data.contact_number,
                     patient_data.email, patient_data.address, str(patient_data.medical_history))
                )
                conn.commit()
    except Exception as e:
        logger.error(f"Error creating patient: {e}")
        raise HTTPException(status_code=500, detail="Failed to create patient")
    
    return PatientResponse(
        id=patient_id,
        user_id=patient_data.user_id,
        first_name=patient_data.first_name,
        last_name=patient_data.last_name,
        date_of_birth=patient_data.date_of_birth,
        gender=patient_data.gender,
        contact_number=patient_data.contact_number,
        email=patient_data.email,
        address=patient_data.address,
        medical_history=patient_data.medical_history,
        created_at=datetime.utcnow().isoformat()
    )

@app.get("/patients/{patient_id}", response_model=PatientResponse)
async def get_patient(patient_id: str, authorization: Optional[str] = None):
    """Get patient by ID"""
    current_user = get_current_user(authorization)
    
    try:
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("SELECT * FROM patients WHERE id = %s", (patient_id,))
                patient = cur.fetchone()
                
                if not patient:
                    raise HTTPException(status_code=404, detail="Patient not found")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching patient: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch patient")
    
    return PatientResponse(**patient)

@app.get("/patients", response_model=List[PatientResponse])
async def get_patients(authorization: Optional[str] = None):
    """Get all patients"""
    current_user = get_current_user(authorization)
    
    try:
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("SELECT * FROM patients ORDER BY created_at DESC")
                patients = cur.fetchall()
    except Exception as e:
        logger.error(f"Error fetching patients: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch patients")
    
    return [PatientResponse(**p) for p in patients]

@app.put("/patients/{patient_id}", response_model=PatientResponse)
async def update_patient(patient_id: str, patient_data: PatientCreate, authorization: Optional[str] = None):
    """Update patient"""
    current_user = get_current_user(authorization)
    
    try:
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """UPDATE patients 
                       SET first_name=%s, last_name=%s, date_of_birth=%s, gender=%s, 
                           contact_number=%s, email=%s, address=%s, medical_history=%s, updated_at=NOW()
                       WHERE id=%s
                       RETURNING *""",
                    (patient_data.first_name, patient_data.last_name, patient_data.date_of_birth,
                     patient_data.gender, patient_data.contact_number, patient_data.email,
                     patient_data.address, str(patient_data.medical_history), patient_id)
                )
                patient = cur.fetchone()
                conn.commit()
                
                if not patient:
                    raise HTTPException(status_code=404, detail="Patient not found")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating patient: {e}")
        raise HTTPException(status_code=500, detail="Failed to update patient")
    
    return PatientResponse(**patient)

# ============================================================================
# DOCTOR ENDPOINTS
# ============================================================================

@app.post("/doctors", response_model=DoctorResponse)
async def create_doctor(doctor_data: DoctorCreate, authorization: Optional[str] = None):
    """Create a new doctor"""
    current_user = get_current_user(authorization)
    doctor_id = str(uuid.uuid4())
    
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """INSERT INTO doctors 
                       (id, user_id, first_name, last_name, specialty, license_number, contact_number, email, clinic_id, created_at, updated_at)
                       VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW())""",
                    (doctor_id, doctor_data.user_id, doctor_data.first_name, doctor_data.last_name,
                     doctor_data.specialty, doctor_data.license_number, doctor_data.contact_number,
                     doctor_data.email, doctor_data.clinic_id)
                )
                conn.commit()
    except Exception as e:
        logger.error(f"Error creating doctor: {e}")
        raise HTTPException(status_code=500, detail="Failed to create doctor")
    
    return DoctorResponse(
        id=doctor_id,
        user_id=doctor_data.user_id,
        first_name=doctor_data.first_name,
        last_name=doctor_data.last_name,
        specialty=doctor_data.specialty,
        license_number=doctor_data.license_number,
        contact_number=doctor_data.contact_number,
        email=doctor_data.email,
        clinic_id=doctor_data.clinic_id,
        created_at=datetime.utcnow().isoformat()
    )

@app.get("/doctors/{doctor_id}", response_model=DoctorResponse)
async def get_doctor(doctor_id: str, authorization: Optional[str] = None):
    """Get doctor by ID"""
    current_user = get_current_user(authorization)
    
    try:
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("SELECT * FROM doctors WHERE id = %s", (doctor_id,))
                doctor = cur.fetchone()
                
                if not doctor:
                    raise HTTPException(status_code=404, detail="Doctor not found")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching doctor: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch doctor")
    
    return DoctorResponse(**doctor)

@app.get("/doctors", response_model=List[DoctorResponse])
async def get_doctors(authorization: Optional[str] = None):
    """Get all doctors"""
    current_user = get_current_user(authorization)
    
    try:
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("SELECT * FROM doctors ORDER BY created_at DESC")
                doctors = cur.fetchall()
    except Exception as e:
        logger.error(f"Error fetching doctors: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch doctors")
    
    return [DoctorResponse(**d) for d in doctors]

@app.put("/doctors/{doctor_id}", response_model=DoctorResponse)
async def update_doctor(doctor_id: str, doctor_data: DoctorCreate, authorization: Optional[str] = None):
    """Update doctor"""
    current_user = get_current_user(authorization)
    
    try:
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """UPDATE doctors 
                       SET first_name=%s, last_name=%s, specialty=%s, license_number=%s, 
                           contact_number=%s, email=%s, clinic_id=%s, updated_at=NOW()
                       WHERE id=%s
                       RETURNING *""",
                    (doctor_data.first_name, doctor_data.last_name, doctor_data.specialty,
                     doctor_data.license_number, doctor_data.contact_number, doctor_data.email,
                     doctor_data.clinic_id, doctor_id)
                )
                doctor = cur.fetchone()
                conn.commit()
                
                if not doctor:
                    raise HTTPException(status_code=404, detail="Doctor not found")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating doctor: {e}")
        raise HTTPException(status_code=500, detail="Failed to update doctor")
    
    return DoctorResponse(**doctor)

# ============================================================================
# APPOINTMENT ENDPOINTS
# ============================================================================

@app.post("/appointments", response_model=AppointmentResponse)
async def create_appointment(appt_data: AppointmentCreate, authorization: Optional[str] = None):
    """Create a new appointment"""
    current_user = get_current_user(authorization)
    appointment_id = str(uuid.uuid4())
    
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                # Check for conflicts
                cur.execute(
                    """SELECT id FROM appointments 
                       WHERE doctor_id = %s AND status != %s
                       AND ((start_time, end_time) OVERLAPS (%s::timestamp, %s::timestamp))""",
                    (appt_data.doctor_id, AppointmentStatus.CANCELLED.value, appt_data.start_time, appt_data.end_time)
                )
                if cur.fetchone():
                    raise HTTPException(status_code=409, detail="Doctor has conflicting appointment")
                
                cur.execute(
                    """INSERT INTO appointments 
                       (id, patient_id, doctor_id, clinic_id, start_time, end_time, status, notes, created_at, updated_at)
                       VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW())""",
                    (appointment_id, appt_data.patient_id, appt_data.doctor_id, appt_data.clinic_id,
                     appt_data.start_time, appt_data.end_time, AppointmentStatus.SCHEDULED.value, appt_data.notes)
                )
                conn.commit()
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating appointment: {e}")
        raise HTTPException(status_code=500, detail="Failed to create appointment")
    
    return AppointmentResponse(
        id=appointment_id,
        patient_id=appt_data.patient_id,
        doctor_id=appt_data.doctor_id,
        clinic_id=appt_data.clinic_id,
        start_time=appt_data.start_time,
        end_time=appt_data.end_time,
        status=AppointmentStatus.SCHEDULED,
        notes=appt_data.notes,
        created_at=datetime.utcnow().isoformat()
    )

@app.get("/appointments/{appointment_id}", response_model=AppointmentResponse)
async def get_appointment(appointment_id: str, authorization: Optional[str] = None):
    """Get appointment by ID"""
    current_user = get_current_user(authorization)
    
    try:
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("SELECT * FROM appointments WHERE id = %s", (appointment_id,))
                appointment = cur.fetchone()
                
                if not appointment:
                    raise HTTPException(status_code=404, detail="Appointment not found")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching appointment: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch appointment")
    
    return AppointmentResponse(**appointment)

@app.get("/appointments/patient/{patient_id}", response_model=List[AppointmentResponse])
async def get_patient_appointments(patient_id: str, authorization: Optional[str] = None):
    """Get all appointments for a patient"""
    current_user = get_current_user(authorization)
    
    try:
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    "SELECT * FROM appointments WHERE patient_id = %s ORDER BY start_time DESC",
                    (patient_id,)
                )
                appointments = cur.fetchall()
    except Exception as e:
        logger.error(f"Error fetching patient appointments: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch appointments")
    
    return [AppointmentResponse(**a) for a in appointments]

@app.get("/appointments/doctor/{doctor_id}", response_model=List[AppointmentResponse])
async def get_doctor_appointments(doctor_id: str, authorization: Optional[str] = None):
    """Get all appointments for a doctor"""
    current_user = get_current_user(authorization)
    
    try:
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    "SELECT * FROM appointments WHERE doctor_id = %s ORDER BY start_time DESC",
                    (doctor_id,)
                )
                appointments = cur.fetchall()
    except Exception as e:
        logger.error(f"Error fetching doctor appointments: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch appointments")
    
    return [AppointmentResponse(**a) for a in appointments]

@app.get("/appointments", response_model=List[AppointmentResponse])
async def get_appointments(authorization: Optional[str] = None):
    """Get all appointments"""
    current_user = get_current_user(authorization)
    
    try:
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("SELECT * FROM appointments ORDER BY start_time DESC")
                appointments = cur.fetchall()
    except Exception as e:
        logger.error(f"Error fetching appointments: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch appointments")
    
    return [AppointmentResponse(**a) for a in appointments]

@app.put("/appointments/{appointment_id}", response_model=AppointmentResponse)
async def update_appointment(appointment_id: str, appt_data: AppointmentUpdate, authorization: Optional[str] = None):
    """Update appointment"""
    current_user = get_current_user(authorization)
    
    try:
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # Build dynamic update query
                updates = []
                params = []
                
                if appt_data.start_time:
                    updates.append("start_time = %s")
                    params.append(appt_data.start_time)
                if appt_data.end_time:
                    updates.append("end_time = %s")
                    params.append(appt_data.end_time)
                if appt_data.status:
                    updates.append("status = %s")
                    params.append(appt_data.status.value)
                if appt_data.notes is not None:
                    updates.append("notes = %s")
                    params.append(appt_data.notes)
                
                if not updates:
                    raise HTTPException(status_code=400, detail="No fields to update")
                
                updates.append("updated_at = NOW()")
                params.append(appointment_id)
                
                query = f"UPDATE appointments SET {', '.join(updates)} WHERE id = %s RETURNING *"
                cur.execute(query, params)
                appointment = cur.fetchone()
                conn.commit()
                
                if not appointment:
                    raise HTTPException(status_code=404, detail="Appointment not found")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating appointment: {e}")
        raise HTTPException(status_code=500, detail="Failed to update appointment")
    
    return AppointmentResponse(**appointment)

# ============================================================================
# CLINIC ENDPOINTS
# ============================================================================

@app.post("/clinics", response_model=ClinicResponse)
async def create_clinic(clinic_data: ClinicCreate, authorization: Optional[str] = None):
    """Create a new clinic"""
    current_user = get_current_user(authorization)
    clinic_id = str(uuid.uuid4())
    
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """INSERT INTO clinics (id, name, address, contact_number, email, created_at, updated_at)
                       VALUES (%s, %s, %s, %s, %s, NOW(), NOW())""",
                    (clinic_id, clinic_data.name, clinic_data.address, clinic_data.contact_number, clinic_data.email)
                )
                conn.commit()
    except Exception as e:
        logger.error(f"Error creating clinic: {e}")
        raise HTTPException(status_code=500, detail="Failed to create clinic")
    
    return ClinicResponse(
        id=clinic_id,
        name=clinic_data.name,
        address=clinic_data.address,
        contact_number=clinic_data.contact_number,
        email=clinic_data.email,
        created_at=datetime.utcnow().isoformat()
    )

@app.get("/clinics/{clinic_id}", response_model=ClinicResponse)
async def get_clinic(clinic_id: str, authorization: Optional[str] = None):
    """Get clinic by ID"""
    current_user = get_current_user(authorization)
    
    try:
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("SELECT * FROM clinics WHERE id = %s", (clinic_id,))
                clinic = cur.fetchone()
                
                if not clinic:
                    raise HTTPException(status_code=404, detail="Clinic not found")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching clinic: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch clinic")
    
    return ClinicResponse(**clinic)

@app.get("/clinics", response_model=List[ClinicResponse])
async def get_clinics(authorization: Optional[str] = None):
    """Get all clinics"""
    current_user = get_current_user(authorization)
    
    try:
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("SELECT * FROM clinics ORDER BY created_at DESC")
                clinics = cur.fetchall()
    except Exception as e:
        logger.error(f"Error fetching clinics: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch clinics")
    
    return [ClinicResponse(**c) for c in clinics]

@app.put("/clinics/{clinic_id}", response_model=ClinicResponse)
async def update_clinic(clinic_id: str, clinic_data: ClinicCreate, authorization: Optional[str] = None):
    """Update clinic"""
    current_user = get_current_user(authorization)
    
    try:
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """UPDATE clinics 
                       SET name=%s, address=%s, contact_number=%s, email=%s, updated_at=NOW()
                       WHERE id=%s
                       RETURNING *""",
                    (clinic_data.name, clinic_data.address, clinic_data.contact_number, clinic_data.email, clinic_id)
                )
                clinic = cur.fetchone()
                conn.commit()
                
                if not clinic:
                    raise HTTPException(status_code=404, detail="Clinic not found")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating clinic: {e}")
        raise HTTPException(status_code=500, detail="Failed to update clinic")
    
    return ClinicResponse(**clinic)

# ============================================================================
# MEDICAL RECORDS ENDPOINTS
# ============================================================================

@app.post("/medical_records", response_model=MedicalRecordResponse)
async def create_medical_record(record_data: MedicalRecordCreate, authorization: Optional[str] = None):
    """Create a new medical record"""
    current_user = get_current_user(authorization)
    record_id = str(uuid.uuid4())
    
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """INSERT INTO medical_records 
                       (id, patient_id, doctor_id, appointment_id, diagnosis, treatment, prescription, notes, created_at, updated_at)
                       VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW())""",
                    (record_id, record_data.patient_id, record_data.doctor_id, record_data.appointment_id,
                     record_data.diagnosis, record_data.treatment, str(record_data.prescription), record_data.notes)
                )
                conn.commit()
    except Exception as e:
        logger.error(f"Error creating medical record: {e}")
        raise HTTPException(status_code=500, detail="Failed to create medical record")
    
    return MedicalRecordResponse(
        id=record_id,
        patient_id=record_data.patient_id,
        doctor_id=record_data.doctor_id,
        appointment_id=record_data.appointment_id,
        diagnosis=record_data.diagnosis,
        treatment=record_data.treatment,
        prescription=record_data.prescription,
        notes=record_data.notes,
        created_at=datetime.utcnow().isoformat()
    )

@app.get("/medical_records/{record_id}", response_model=MedicalRecordResponse)
async def get_medical_record(record_id: str, authorization: Optional[str] = None):
    """Get medical record by ID"""
    current_user = get_current_user(authorization)
    
    try:
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("SELECT * FROM medical_records WHERE id = %s", (record_id,))
                record = cur.fetchone()
                
                if not record:
                    raise HTTPException(status_code=404, detail="Medical record not found")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching medical record: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch medical record")
    
    return MedicalRecordResponse(**record)

@app.get("/medical_records/patient/{patient_id}", response_model=List[MedicalRecordResponse])
async def get_patient_medical_records(patient_id: str, authorization: Optional[str] = None):
    """Get all medical records for a patient"""
    current_user = get_current_user(authorization)
    
    try:
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    "SELECT * FROM medical_records WHERE patient_id = %s ORDER BY created_at DESC",
                    (patient_id,)
                )
                records = cur.fetchall()
    except Exception as e:
        logger.error(f"Error fetching patient medical records: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch medical records")
    
    return [MedicalRecordResponse(**r) for r in records]

# ============================================================================
# BILLING ENDPOINTS
# ============================================================================

@app.post("/billing", response_model=BillingResponse)
async def create_billing(billing_data: BillingCreate, authorization: Optional[str] = None):
    """Create a new billing record"""
    current_user = get_current_user(authorization)
    billing_id = str(uuid.uuid4())
    
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """INSERT INTO billing (id, patient_id, appointment_id, amount, status, created_at, updated_at)
                       VALUES (%s, %s, %s, %s, %s, NOW(), NOW())""",
                    (billing_id, billing_data.patient_id, billing_data.appointment_id, 
                     billing_data.amount, billing_data.status.value)
                )
                conn.commit()
    except Exception as e:
        logger.error(f"Error creating billing record: {e}")
        raise HTTPException(status_code=500, detail="Failed to create billing record")
    
    return BillingResponse(
        id=billing_id,
        patient_id=billing_data.patient_id,
        appointment_id=billing_data.appointment_id,
        amount=billing_data.amount,
        status=billing_data.status,
        created_at=datetime.utcnow().isoformat()
    )

@app.get("/billing/{billing_id}", response_model=BillingResponse)
async def get_billing_record(billing_id: str, authorization: Optional[str] = None):
    """Get billing record by ID"""
    current_user = get_current_user(authorization)
    
    try:
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("SELECT * FROM billing WHERE id = %s", (billing_id,))
                record = cur.fetchone()
                
                if not record:
                    raise HTTPException(status_code=404, detail="Billing record not found")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching billing record: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch billing record")
    
    return BillingResponse(**record)

@app.get("/billing/patient/{patient_id}", response_model=List[BillingResponse])
async def get_patient_billing(patient_id: str, authorization: Optional[str] = None):
    """Get all billing records for a patient"""
    current_user = get_current_user(authorization)
    
    try:
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    "SELECT * FROM billing WHERE patient_id = %s ORDER BY created_at DESC",
                    (patient_id,)
                )
                records = cur.fetchall()
    except Exception as e:
        logger.error(f"Error fetching patient billing: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch billing records")
    
    return [BillingResponse(**r) for r in records]

@app.put("/billing/{billing_id}", response_model=BillingResponse)
async def update_billing(billing_id: str, billing_data: BillingUpdate, authorization: Optional[str] = None):
    """Update billing record"""
    current_user = get_current_user(authorization)
    
    try:
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                updates = []
                params = []
                
                if billing_data.amount:
                    updates.append("amount = %s")
                    params.append(billing_data.amount)
                if billing_data.status:
                    updates.append("status = %s")
                    params.append(billing_data.status.value)
                
                if not updates:
                    raise HTTPException(status_code=400, detail="No fields to update")
                
                updates.append("updated_at = NOW()")
                params.append(billing_id)
                
                query = f"UPDATE billing SET {', '.join(updates)} WHERE id = %s RETURNING *"
                cur.execute(query, params)
                record = cur.fetchone()
                conn.commit()
                
                if not record:
                    raise HTTPException(status_code=404, detail="Billing record not found")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating billing record: {e}")
        raise HTTPException(status_code=500, detail="Failed to update billing record")
    
    return BillingResponse(**record)

# ============================================================================
# HEALTH CHECK
# ============================================================================

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "ok", "message": "Clinic SaaS API is running"}

# ============================================================================
# STARTUP
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)