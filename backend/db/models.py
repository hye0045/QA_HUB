from sqlalchemy import Column, String, Boolean, Integer, DateTime, Enum, ForeignKey, Table
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
from db.database import Base
import enum

class UserRole(enum.Enum):
    intern = "intern"
    tester = "tester"
    qa_lead = "qa_lead"
    admin = "admin"

class DocStatus(enum.Enum):
    draft = "draft"
    pending_mentor = "pending_mentor" # New intermediate state from requirements
    pending_qa_lead = "pending_qa_lead"
    locked = "locked"

class InternStatus(enum.Enum):
    in_progress = "in_progress"
    ready = "ready"

class ChatMode(enum.Enum):
    qa = "qa"
    translate = "translate"
    suggest = "suggest"

class User(Base):
    __tablename__ = "users"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    role = Column(Enum(UserRole), nullable=False, default=UserRole.intern)
    is_mentor = Column(Boolean, nullable=False, default=False)
    email = Column(String, unique=True, nullable=False)
    full_name = Column(String, nullable=False)
    password_hash = Column(String, nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

class Specification(Base):
    __tablename__ = "specification"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String, nullable=False)
    language = Column(String, nullable=False)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    versions = relationship("SpecVersion", back_populates="specification")

class SpecVersion(Base):
    __tablename__ = "spec_version"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    specification_id = Column(UUID(as_uuid=True), ForeignKey("specification.id", ondelete="CASCADE"))
    version_number = Column(Integer, nullable=False)
    content = Column(String, nullable=False)
    embedding = Column(JSONB) # Stored as JSON array for local similarity usage
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    specification = relationship("Specification", back_populates="versions")

class Testcase(Base):
    __tablename__ = "testcase"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String, nullable=False)
    description = Column(String)
    steps = Column(String)
    expected_result = Column(String)
    status = Column(String, default="Draft") # New field from Phase 2
    model_id = Column(String) # New field
    test_type = Column(String) # New field
    precondition = Column(String) # New field
    is_affected = Column(Boolean, nullable=False, default=False)
    embedding = Column(JSONB)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

testcase_spec_link = Table(
    "testcase_spec_link", Base.metadata,
    Column("testcase_id", UUID(as_uuid=True), ForeignKey("testcase.id", ondelete="CASCADE"), primary_key=True),
    Column("specification_id", UUID(as_uuid=True), ForeignKey("specification.id", ondelete="CASCADE"), primary_key=True)
)

class Defect(Base):
    __tablename__ = "defect"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    redmine_id = Column(Integer, unique=True, nullable=False)
    title = Column(String, nullable=False)
    status = Column(String, nullable=False)
    severity = Column(String, nullable=False)
    model_id = Column(String)
    synced_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

class DeliveryDocument(Base):
    __tablename__ = "delivery_document"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String, nullable=False)
    status = Column(Enum(DocStatus), nullable=False, default=DocStatus.draft)
    mentor_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

class ChatHistory(Base):
    __tablename__ = "chat_history"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"))
    mode = Column(Enum(ChatMode), nullable=False)
    prompt = Column(String, nullable=False)
    response = Column(String, nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

class MentorAssignment(Base):
    """
    [UC_F2] Bảng lưu trữ liên kết giữa Mentor (QA Lead / Tester) và Intern.
    """
    __tablename__ = "mentor_assignments"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    mentor_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    intern_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True) # Assuming an intern only has 1 active mentor
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
