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
    email: EmailStr
    phone: Optional[str] = None
    emergency_contact_name: Optional[str] = None
    emergency_contact_relation: Optional[str] = None
    emergency_contact_phone: Optional[str] = None
    faculty: Optional[str] = None
    career: Optional[str] = None
    site_id: int
    metadata_json: Optional[Dict[str, Any]] = None

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

    class Config:
        from_attributes = True

# --- Dynamic Fields ---
class FieldDefinitionBase(BaseModel):
    name: str
    label: str
    field_type: FieldTypeEnum
    is_active: bool = True

class FieldDefinitionCreate(FieldDefinitionBase):
    pass

class FieldDefinitionResponse(FieldDefinitionBase):
    id: int

    class Config:
        from_attributes = True

class FieldValueResponse(BaseModel):
    id: int
    participant_id: int
    field_definition_id: int
    value: Optional[str] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class FieldValueUpdateBatch(BaseModel):
    fields: Dict[str, Optional[Any]]


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
