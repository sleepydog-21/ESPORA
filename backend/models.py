import enum
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime, Enum, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import JSONB

from database import Base

class RoleEnum(str, enum.Enum):
    ADMIN = "admin"
    COORDINATOR = "coordinator"
    THERAPIST = "therapist"
    GENERAL_COORDINATOR = "general_coordinator"

class CaseStatusEnum(str, enum.Enum):
    WAITING = "waiting"
    ASSIGNED = "assigned"
    ACTIVE = "active"
    CLOSED = "closed"
    CANCELLED = "cancelled"

class ModalityEnum(str, enum.Enum):
    ONLINE = "online"
    IN_PERSON = "in_person"

class Site(Base):
    __tablename__ = "sites"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), unique=True, index=True, nullable=False)

    users = relationship("User", back_populates="site")
    participants = relationship("Participant", back_populates="site")
    cases = relationship("Case", back_populates="site")

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    role = Column(Enum(RoleEnum), nullable=False)
    site_id = Column(Integer, ForeignKey("sites.id"), nullable=True)
    is_active = Column(Boolean, default=True)
    
    # Optional contact info for therapists/coordinators
    full_name = Column(String, nullable=True)
    phone = Column(String, nullable=True)
    therapist_category = Column(Integer, nullable=True)
    
    site = relationship("Site", back_populates="users")
    cases_as_therapist = relationship("Case", foreign_keys="[Case.therapist_id]", back_populates="therapist")
    cases_as_coordinator = relationship("Case", foreign_keys="[Case.coordinator_id]", back_populates="coordinator")

class Participant(Base):
    __tablename__ = "participants"

    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String(255), index=True, nullable=False)
    student_account = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(255), nullable=False)
    phone = Column(String(50), nullable=True)
    gender = Column(String(50), nullable=True) # Added for demographics
    
    emergency_contact_name = Column(String(255), nullable=True)
    emergency_contact_relation = Column(String(100), nullable=True)
    emergency_contact_phone = Column(String(50), nullable=True)
    
    faculty = Column(String(255), nullable=True)
    career = Column(String(255), nullable=True)
    
    site_id = Column(Integer, ForeignKey("sites.id"), nullable=False)
    site = relationship("Site", back_populates="participants")
    
    metadata_json = Column(JSONB, nullable=True)

    cases = relationship("Case", back_populates="participant")

class Case(Base):
    __tablename__ = "cases"

    id = Column(Integer, primary_key=True, index=True)
    participant_id = Column(Integer, ForeignKey("participants.id"), nullable=False)
    site_id = Column(Integer, ForeignKey("sites.id"), nullable=False)
    therapist_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    coordinator_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    
    status = Column(Enum(CaseStatusEnum), default=CaseStatusEnum.WAITING, nullable=False)
    intake_source = Column(String(50), default="manual")
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    closed_at = Column(DateTime(timezone=True), nullable=True)

    participant = relationship("Participant", back_populates="cases")
    site = relationship("Site", back_populates="cases")
    therapist = relationship("User", foreign_keys=[therapist_id], back_populates="cases_as_therapist")
    coordinator = relationship("User", foreign_keys=[coordinator_id], back_populates="cases_as_coordinator")
    sessions = relationship("Session", back_populates="case_ref")

class Session(Base):
    __tablename__ = "sessions"

    id = Column(Integer, primary_key=True, index=True)
    case_id = Column(Integer, ForeignKey("cases.id"), nullable=False)
    session_date = Column(DateTime(timezone=True), nullable=False)
    modality = Column(Enum(ModalityEnum), nullable=True)
    therapist_notes = Column(Text, nullable=True)
    status = Column(String, default="scheduled")

    case_ref = relationship("Case", back_populates="sessions")

class FieldTypeEnum(str, enum.Enum):
    STRING = "string"
    INTEGER = "integer"
    TEXT = "text"
    BOOLEAN = "boolean"
    DATE = "date"

class AuditActionEnum(str, enum.Enum):
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"

class FieldDefinition(Base):
    __tablename__ = "field_definitions"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, index=True, nullable=False)
    label = Column(String(255), nullable=False)
    field_type = Column(Enum(FieldTypeEnum), nullable=False)
    is_active = Column(Boolean, default=True)

class FieldValue(Base):
    __tablename__ = "field_values"

    id = Column(Integer, primary_key=True, index=True)
    participant_id = Column(Integer, ForeignKey("participants.id"), nullable=False, index=True)
    field_definition_id = Column(Integer, ForeignKey("field_definitions.id"), nullable=False)
    value = Column(Text, nullable=True)
    
    updated_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    participant = relationship("Participant")
    field_definition = relationship("FieldDefinition")
    updated_by = relationship("User")

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    table_name = Column(String(50), nullable=False, index=True)
    record_id = Column(Integer, nullable=False, index=True)
    action = Column(Enum(AuditActionEnum), nullable=False)
    
    old_value = Column(JSONB, nullable=True)
    new_value = Column(JSONB, nullable=True)
    
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User")

class AlertSetting(Base):
    __tablename__ = "alert_settings"

    id = Column(Integer, primary_key=True, index=True)
    metric_name = Column(String(100), nullable=False) # e.g. 'waitlist_size'
    operator = Column(String(5), nullable=False) # e.g. '>'
    threshold_value = Column(Integer, nullable=False)
    site_id = Column(Integer, ForeignKey("sites.id"), nullable=True) # If None, applies globally
    is_active = Column(Boolean, default=True)
    created_by_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    site = relationship("Site")
    created_by = relationship("User")

class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    message = Column(String(255), nullable=False)
    is_read = Column(Boolean, default=False)
    site_id = Column(Integer, ForeignKey("sites.id"), nullable=True) # To link the problem to a specific site
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False) # Target user to notify (Usually General Coord)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    site = relationship("Site")
    user = relationship("User")
