import enum
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime, Enum, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy import inspect, event

from database import Base

class RoleEnum(str, enum.Enum):
    ADMIN = "admin"
    COORDINATOR = "coordinator"
    THERAPIST = "therapist"
    GENERAL_COORDINATOR = "general_coordinator"
    API_THERAPIST = "api_therapist"

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
    anonymous_folio = Column(String(50), unique=True, index=True, nullable=True)
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
    limesurvey_summary = Column(Text, nullable=True)

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
    process_data = relationship("CaseProcessData", uselist=False, back_populates="case_ref", cascade="all, delete-orphan")

class Session(Base):
    __tablename__ = "sessions"

    id = Column(Integer, primary_key=True, index=True)
    case_id = Column(Integer, ForeignKey("cases.id"), nullable=False)
    session_date = Column(DateTime(timezone=True), nullable=False)
    modality = Column(Enum(ModalityEnum), nullable=True)
    therapist_notes = Column(Text, nullable=True)
    status = Column(String, default="scheduled")
    worked_issues = Column(JSONB, nullable=True)

    case_ref = relationship("Case", back_populates="sessions")

class Topic(Base):
    __tablename__ = "topics"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    site_id = Column(Integer, ForeignKey("sites.id"), nullable=True)
    is_active = Column(Boolean, default=True)

    appointments = relationship("Appointment", secondary="appointment_topics", back_populates="topics")

class AppointmentTopic(Base):
    __tablename__ = "appointment_topics"

    id = Column(Integer, primary_key=True, index=True)
    appointment_id = Column(Integer, ForeignKey("appointments.id"), nullable=False)
    topic_id = Column(Integer, ForeignKey("topics.id"), nullable=False)

class Appointment(Base):
    __tablename__ = "appointments"

    id = Column(Integer, primary_key=True, index=True)
    therapist_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    case_id = Column(Integer, ForeignKey("cases.id"), nullable=True) # Optional: can block time without case
    start_time = Column(DateTime(timezone=True), nullable=False)
    end_time = Column(DateTime(timezone=True), nullable=False)
    status = Column(String(50), default="scheduled") # scheduled, cancelled, completed
    notes = Column(Text, nullable=True)
    
    therapist = relationship("User", foreign_keys=[therapist_id])
    case_ref = relationship("Case")
    topics = relationship("Topic", secondary="appointment_topics", back_populates="appointments")

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

class FormTemplate(Base):
    __tablename__ = "form_templates"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, index=True, nullable=False)
    description = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=True)

    fields = relationship("FormField", back_populates="template", cascade="all, delete-orphan")
    submissions = relationship("FormSubmission", back_populates="template")

class FormField(Base):
    __tablename__ = "form_fields"

    id = Column(Integer, primary_key=True, index=True)
    form_template_id = Column(Integer, ForeignKey("form_templates.id"), nullable=False)
    name = Column(String(100), nullable=False)
    label = Column(String(255), nullable=False)
    field_type = Column(Enum(FieldTypeEnum), nullable=False)
    options = Column(JSONB, nullable=True)
    is_required = Column(Boolean, default=False)

    template = relationship("FormTemplate", back_populates="fields")
    values = relationship("FormFieldValue", back_populates="field")

class FormSubmission(Base):
    __tablename__ = "form_submissions"

    id = Column(Integer, primary_key=True, index=True)
    form_template_id = Column(Integer, ForeignKey("form_templates.id"), nullable=False)
    participant_id = Column(Integer, ForeignKey("participants.id"), nullable=True)
    case_id = Column(Integer, ForeignKey("cases.id"), nullable=True)
    session_id = Column(Integer, ForeignKey("sessions.id"), nullable=True)
    
    submitted_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    submitted_at = Column(DateTime(timezone=True), server_default=func.now())

    template = relationship("FormTemplate", back_populates="submissions")
    participant = relationship("Participant")
    case_ref = relationship("Case")
    session_ref = relationship("Session")
    submitted_by = relationship("User")
    field_values = relationship("FormFieldValue", back_populates="submission", cascade="all, delete-orphan")
    attachments = relationship("FormSubmissionAttachment", back_populates="submission", cascade="all, delete-orphan")

class FormFieldValue(Base):
    __tablename__ = "form_field_values"

    id = Column(Integer, primary_key=True, index=True)
    form_submission_id = Column(Integer, ForeignKey("form_submissions.id"), nullable=False)
    form_field_id = Column(Integer, ForeignKey("form_fields.id"), nullable=False)
    value_text = Column(Text, nullable=True)

    submission = relationship("FormSubmission", back_populates="field_values")
    field = relationship("FormField", back_populates="values")

class FormSubmissionAttachment(Base):
    __tablename__ = "form_submission_attachments"

    id = Column(Integer, primary_key=True, index=True)
    form_submission_id = Column(Integer, ForeignKey("form_submissions.id", ondelete="CASCADE"), nullable=False)
    filename = Column(String(255), nullable=False)
    content_type = Column(String(100), nullable=True)
    file_data = Column(Text, nullable=False) # Base64 encoded string

    submission = relationship("FormSubmission", back_populates="attachments")

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

class CaseProcessData(Base):
    __tablename__ = "case_process_data"

    case_id = Column(Integer, ForeignKey("cases.id", ondelete="CASCADE"), primary_key=True)
    fecha_solicitud = Column(DateTime(timezone=True), nullable=True)
    fecha_inicio = Column(DateTime(timezone=True), nullable=True)
    semestre_inicio = Column(String(50), nullable=True)
    edad = Column(Integer, nullable=True)
    sexo = Column(String(50), nullable=True)
    ano_cursa = Column(Integer, nullable=True)
    sesiones_totales = Column(Integer, nullable=True)
    inasistencias = Column(Integer, nullable=True)
    horas_padres = Column(Integer, nullable=True)
    horas_clinicas_actual = Column(Integer, nullable=True)
    horas_clinicas_anterior = Column(Integer, nullable=True)
    sesiones_seguimiento = Column(Integer, nullable=True)
    estatus_proceso = Column(String(100), nullable=True)
    motivo_interrupcion = Column(Text, nullable=True)
    observaciones_abandono = Column(Text, nullable=True)
    fecha_finalizacion = Column(DateTime(timezone=True), nullable=True)
    semestre_finalizacion = Column(String(50), nullable=True)
    tuvo_intervencion_api = Column(Boolean, nullable=True)
    sesiones_api = Column(Integer, nullable=True)
    impresion_diagnostica = Column(Text, nullable=True)
    internamientos_previos = Column(Boolean, nullable=True)
    internamientos_previos_cant = Column(Integer, nullable=True)
    internamientos_durante = Column(Boolean, nullable=True)
    internamientos_durante_cant = Column(Integer, nullable=True)
    canalizacion_psiquiatria = Column(Boolean, nullable=True)
    dx_psiquiatria = Column(Text, nullable=True)
    fecha_canalizacion = Column(DateTime(timezone=True), nullable=True)
    canalizacion_otra = Column(Boolean, nullable=True)
    canalizacion_otra_cual = Column(String(255), nullable=True)
    referido_externo = Column(Boolean, nullable=True)
    intervencion_espora_comunitaria = Column(Boolean, nullable=True)
    intervencion_espora_comunitaria_cual = Column(Text, nullable=True)

    case_ref = relationship("Case", back_populates="process_data")

class TherapistFeedback(Base):
    __tablename__ = "therapist_feedback"

    id = Column(Integer, primary_key=True, index=True)
    therapist_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    year = Column(Integer, nullable=False)
    week = Column(Integer, nullable=False)
    q1_score = Column(Integer, nullable=False)
    q2_score = Column(Integer, nullable=False)
    submitted_at = Column(DateTime(timezone=True), server_default=func.now())

    therapist = relationship("User")

def log_audit_event(mapper, connection, target, action):
    table_name = target.__tablename__
    state = inspect(target)
    
    pk_attrs = state.mapper.primary_key
    pk_name = pk_attrs[0].name if pk_attrs else "id"
    record_id = getattr(target, pk_name, None)
    
    user_id = getattr(target, 'updated_by_id', None) or getattr(target, 'submitted_by_id', None)
    
    old_value = None
    new_value = None
    
    if action == AuditActionEnum.UPDATE:
        changes = {}
        for attr in state.attrs:
            hist = getattr(state.attrs, attr.key).history
            if hist.has_changes():
                changes[attr.key] = {
                    'old': hist.deleted[0] if hist.deleted else None,
                    'new': hist.added[0] if hist.added else None
                }
        if changes:
            new_value = {k: str(v['new']) for k, v in changes.items()}
            old_value = {k: str(v['old']) for k, v in changes.items()}
    elif action == AuditActionEnum.CREATE:
        new_value = {pk_name: record_id}
    elif action == AuditActionEnum.DELETE:
        old_value = {pk_name: record_id}

    connection.execute(
        AuditLog.__table__.insert().values(
            table_name=table_name,
            record_id=record_id,
            action=action,
            old_value=old_value,
            new_value=new_value,
            user_id=user_id
        )
    )

def register_audit_listeners(model):
    @event.listens_for(model, 'after_insert')
    def receive_after_insert(mapper, connection, target):
        log_audit_event(mapper, connection, target, AuditActionEnum.CREATE)

    @event.listens_for(model, 'after_update')
    def receive_after_update(mapper, connection, target):
        log_audit_event(mapper, connection, target, AuditActionEnum.UPDATE)

    @event.listens_for(model, 'after_delete')
    def receive_after_delete(mapper, connection, target):
        log_audit_event(mapper, connection, target, AuditActionEnum.DELETE)

register_audit_listeners(Participant)
register_audit_listeners(Case)
register_audit_listeners(FormSubmission)
register_audit_listeners(FormFieldValue)
register_audit_listeners(Appointment)
register_audit_listeners(Session)
register_audit_listeners(CaseProcessData)
register_audit_listeners(FormSubmissionAttachment)
