from typing import Optional, List, Any, Dict
from datetime import datetime
from pydantic import BaseModel, EmailStr
from models import RoleEnum, CaseStatusEnum, ModalityEnum, FieldTypeEnum, AuditActionEnum

# --- Token ---
class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    email: Optional[str] = None
    role: Optional[RoleEnum] = None
    site_id: Optional[int] = None

# --- User ---
class UserBase(BaseModel):
    email: EmailStr
    role: RoleEnum
    site_id: Optional[int] = None
    is_active: bool = True
    therapist_category: Optional[int] = None

class UserCreate(UserBase):
    password: str

class TherapistQuickCreate(BaseModel):
    email: EmailStr
    full_name: Optional[str] = None
    phone: Optional[str] = None
    site_id: Optional[int] = None # Coords don't need this, general coords do

class CoordinatorQuickCreate(BaseModel):
    email: EmailStr
    site_id: int
    full_name: Optional[str] = None
    phone: Optional[str] = None

class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    phone: Optional[str] = None
    is_active: Optional[bool] = None
    therapist_category: Optional[int] = None

class UserResponse(UserBase):
    id: int
    full_name: Optional[str] = None
    phone: Optional[str] = None

    class Config:
        from_attributes = True

# --- Site ---
class SiteBase(BaseModel):
    name: str

class SiteCreate(SiteBase):
    pass

class SiteResponse(SiteBase):
    id: int

    class Config:
        from_attributes = True

# --- Participant ---
class ParticipantBase(BaseModel):
    full_name: str
    student_account: str
    anonymous_folio: Optional[str] = None
    email: EmailStr
    phone: Optional[str] = None
    emergency_contact_name: Optional[str] = None
    emergency_contact_relation: Optional[str] = None
    emergency_contact_phone: Optional[str] = None
    faculty: Optional[str] = None
    career: Optional[str] = None
    site_id: int
    metadata_json: Optional[Dict[str, Any]] = None
    limesurvey_summary: Optional[str] = None

class ParticipantCreate(ParticipantBase):
    pass

class ParticipantUpdate(BaseModel):
    full_name: Optional[str] = None
    student_account: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    faculty: Optional[str] = None
    career: Optional[str] = None

class ParticipantResponse(ParticipantBase):
    id: int

    class Config:
        from_attributes = True

# --- Session ---
class SessionBase(BaseModel):
    session_date: datetime
    modality: Optional[ModalityEnum] = None
    therapist_notes: Optional[str] = None
    status: Optional[str] = "scheduled"
    worked_issues: Optional[Dict[str, Any]] = None

class SessionCreate(SessionBase):
    case_id: int

class SessionBiweeklyCreate(BaseModel):
    case_id: int
    start_date: datetime
    num_sessions: Optional[int] = 14

class SessionResponse(SessionBase):
    id: int
    case_id: int

    class Config:
        from_attributes = True

# --- Topics ---
class TopicBase(BaseModel):
    name: str
    is_active: bool = True

class TopicCreate(TopicBase):
    pass

class TopicResponse(TopicBase):
    id: int
    site_id: Optional[int] = None

    class Config:
        from_attributes = True

class AppointmentTopicCreate(BaseModel):
    topic_ids: List[int]

# --- Case ---
class CaseBase(BaseModel):
    participant_id: int
    site_id: int
    intake_source: str = "manual"

class CaseCreate(CaseBase):
    pass

class CaseUpdate(BaseModel):
    therapist_id: Optional[int] = None
    coordinator_id: Optional[int] = None
    status: Optional[CaseStatusEnum] = None
    closed_at: Optional[datetime] = None

class CaseResponse(CaseBase):
    id: int
    therapist_id: Optional[int] = None
    coordinator_id: Optional[int] = None
    status: CaseStatusEnum
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    closed_at: Optional[datetime] = None
    participant: ParticipantResponse
    sessions: List[SessionResponse] = []
    process_data: Optional[Any] = None

    class Config:
        from_attributes = True

# --- Dynamic Forms ---
class FormTemplateBase(BaseModel):
    name: str
    description: Optional[str] = None
    is_active: bool = True

class FormTemplateCreate(FormTemplateBase):
    pass

class FormTemplateResponse(FormTemplateBase):
    id: int

    class Config:
        from_attributes = True

class FormFieldBase(BaseModel):
    name: str
    label: str
    field_type: FieldTypeEnum
    options: Optional[Dict[str, Any]] = None
    is_required: bool = False

class FormFieldCreate(FormFieldBase):
    form_template_id: int

class FormFieldResponse(FormFieldBase):
    id: int
    form_template_id: int

    class Config:
        from_attributes = True

class FormFieldValueCreate(BaseModel):
    form_field_id: int
    value_text: Optional[str] = None

class FormFieldValueResponse(FormFieldValueCreate):
    id: int
    form_submission_id: int
    field: Optional[FormFieldResponse] = None

    class Config:
        from_attributes = True

class AttachmentCreate(BaseModel):
    filename: str
    content_type: Optional[str] = None
    file_data: str # Base64 encoded string

class AttachmentResponse(AttachmentCreate):
    id: int

    class Config:
        from_attributes = True

class FormSubmissionCreate(BaseModel):
    form_template_id: int
    participant_id: Optional[int] = None
    case_id: Optional[int] = None
    session_id: Optional[int] = None
    fields: List[FormFieldValueCreate]
    attachments: Optional[List[AttachmentCreate]] = []

class FormSubmissionResponse(BaseModel):
    id: int
    form_template_id: int
    participant_id: Optional[int] = None
    case_id: Optional[int] = None
    session_id: Optional[int] = None
    submitted_by_id: Optional[int] = None
    submitted_at: datetime
    field_values: List[FormFieldValueResponse] = []
    attachments: List[AttachmentResponse] = []
    template: Optional[FormTemplateResponse] = None

    class Config:
        from_attributes = True


# --- Alerts ---
class AlertSettingBase(BaseModel):
    metric_name: str
    operator: str
    threshold_value: int
    site_id: Optional[int] = None
    is_active: bool = True

class AlertSettingCreate(AlertSettingBase):
    pass

class AlertSettingResponse(AlertSettingBase):
    id: int
    created_by_id: int
    created_at: datetime

    class Config:
        from_attributes = True

class NotificationResponse(BaseModel):
    id: int
    message: str
    is_read: bool
    site_id: Optional[int] = None
    user_id: int
    created_at: datetime

    class Config:
        from_attributes = True
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional

class AppointmentBase(BaseModel):
    case_id: Optional[int] = None
    start_time: datetime
    end_time: datetime
    status: str = "scheduled"
    notes: Optional[str] = None

class AppointmentCreate(AppointmentBase):
    therapist_id: int

class AppointmentUpdate(BaseModel):
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    status: Optional[str] = None
    notes: Optional[str] = None

class AppointmentResponse(AppointmentBase):
    id: int
    therapist_id: int
    topics: List["TopicResponse"] = []

    class Config:
        from_attributes = True

class CaseProcessDataBase(BaseModel):
    fecha_solicitud: Optional[datetime] = None
    fecha_inicio: Optional[datetime] = None
    semestre_inicio: Optional[str] = None
    edad: Optional[int] = None
    sexo: Optional[str] = None
    ano_cursa: Optional[int] = None
    sesiones_totales: Optional[int] = None
    inasistencias: Optional[int] = None
    horas_padres: Optional[int] = None
    horas_clinicas_actual: Optional[int] = None
    horas_clinicas_anterior: Optional[int] = None
    sesiones_seguimiento: Optional[int] = None
    estatus_proceso: Optional[str] = None
    motivo_interrupcion: Optional[str] = None
    observaciones_abandono: Optional[str] = None
    fecha_finalizacion: Optional[datetime] = None
    semestre_finalizacion: Optional[str] = None
    tuvo_intervencion_api: Optional[bool] = None
    sesiones_api: Optional[int] = None
    impresion_diagnostica: Optional[str] = None
    internamientos_previos: Optional[bool] = None
    internamientos_previos_cant: Optional[int] = None
    internamientos_durante: Optional[bool] = None
    internamientos_durante_cant: Optional[int] = None
    canalizacion_psiquiatria: Optional[bool] = None
    dx_psiquiatria: Optional[str] = None
    fecha_canalizacion: Optional[datetime] = None
    canalizacion_otra: Optional[bool] = None
    canalizacion_otra_cual: Optional[str] = None
    referido_externo: Optional[bool] = None
    intervencion_espora_comunitaria: Optional[bool] = None
    intervencion_espora_comunitaria_cual: Optional[str] = None

class CaseProcessDataUpdate(CaseProcessDataBase):
    pass

class CaseProcessDataResponse(CaseProcessDataBase):
    case_id: int

    class Config:
        from_attributes = True

# --- Therapist Feedback ---
class TherapistFeedbackCreate(BaseModel):
    q1_score: int = Field(..., ge=1, le=10)
    q2_score: int = Field(..., ge=1, le=10)

class TherapistFeedbackResponse(BaseModel):
    id: int
    therapist_id: int
    year: int
    week: int
    q1_score: int
    q2_score: int
    submitted_at: datetime

    class Config:
        from_attributes = True

# --- Email Request ---
class CaseSendEmailRequest(BaseModel):
    subject: str
    body: str
    email_type: Optional[str] = "custom"
    recipient_email: Optional[EmailStr] = None

