"""
Database models and persistence layer for Alpha Clinical Agents
PostgreSQL with SQLAlchemy for FDA-compliant audit trail storage
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from uuid import uuid4

from sqlalchemy import (
    create_engine, Column, String, DateTime, Integer, 
    Float, JSON, ForeignKey, Index, Text
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship, Session
from sqlalchemy.dialects.postgresql import UUID

Base = declarative_base()


class DocumentModel(Base):
    """Clinical document (CSR, Protocol, etc.)"""
    __tablename__ = "documents"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    document_type = Column(String(50), nullable=False)  # "CSR", "Protocol", etc.
    study_id = Column(String(100), nullable=False, index=True)
    status = Column(String(50), default="draft")  # draft, in_review, approved, submitted
    
    # Document metadata
    title = Column(Text)
    version = Column(String(20), default="1.0")
    sponsor = Column(String(200))
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    submitted_at = Column(DateTime, nullable=True)
    
    # Relationships
    sections = relationship("SectionModel", back_populates="document")
    audit_records = relationship("AuditRecordModel", back_populates="document")
    validation_results = relationship("ValidationResultModel", back_populates="document")
    
    # FDA 21 CFR Part 11
    electronic_signature = Column(String(500), nullable=True)
    signed_by = Column(String(200), nullable=True)
    signed_at = Column(DateTime, nullable=True)


class SectionModel(Base):
    """Document section (Methods, Results, Safety, etc.)"""
    __tablename__ = "sections"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    document_id = Column(String(36), ForeignKey("documents.id"), nullable=False)
    section_name = Column(String(100), nullable=False)  # "Methods", "Results", etc.
    
    # Content
    draft_text = Column(Text)
    final_text = Column(Text)
    
    # Status
    status = Column(String(50), default="pending")  # pending, draft, review, approved
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    document = relationship("DocumentModel", back_populates="sections")
    citations = relationship("CitationModel", back_populates="section")


class AuditRecordModel(Base):
    """
    FDA 21 CFR Part 11 compliant audit record
    Immutable trail of all agent actions
    """
    __tablename__ = "audit_records"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    document_id = Column(String(36), ForeignKey("documents.id"), nullable=True, index=True)
    
    # Agent info
    agent_id = Column(String(100), nullable=False, index=True)
    agent_version = Column(String(50), nullable=False)
    action = Column(String(100), nullable=False)  # "process", "validate", "error", etc.
    
    # Data integrity (FDA 21 CFR Part 11)
    input_hash = Column(String(64), nullable=False)
    output_hash = Column(String(64), nullable=False)
    
    # Content
    input_data = Column(JSON, nullable=True)
    output_data = Column(JSON, nullable=True)
    rationale = Column(Text)
    
    # Timestamps (UTC for compliance)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    
    # Human approval (if applicable)
    human_approval = Column(String(200), nullable=True)
    electronic_signature = Column(String(500), nullable=True)
    
    # Relationships
    document = relationship("DocumentModel", back_populates="audit_records")
    
    # Indexes for FDA queries
    __table_args__ = (
        Index('idx_audit_agent_time', 'agent_id', 'timestamp'),
        Index('idx_audit_document_time', 'document_id', 'timestamp'),
    )


class ValidationResultModel(Base):
    """Validation results from various agents"""
    __tablename__ = "validation_results"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    document_id = Column(String(36), ForeignKey("documents.id"), nullable=False)
    agent_id = Column(String(100), nullable=False)
    
    # Validation type
    validation_type = Column(String(100))  # "statistical", "compliance", "cross_ref"
    
    # Results
    score = Column(Float)
    findings = Column(JSON)  # List of findings
    critical_issues = Column(JSON)  # List of critical issues
    warnings = Column(JSON)
    
    # Status
    passed = Column(String(10))  # "true", "false", "partial"
    
    # Timestamp
    timestamp = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    document = relationship("DocumentModel", back_populates="validation_results")


class CitationModel(Base):
    """Citations linking generated content to source documents"""
    __tablename__ = "citations"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    section_id = Column(String(36), ForeignKey("sections.id"), nullable=False)
    
    # Claim being cited
    claim_text = Column(Text, nullable=False)
    
    # Source information
    source_doc = Column(String(200))
    source_section = Column(String(200))
    source_page = Column(Integer)
    
    # Verification
    confidence = Column(Float)
    verified = Column(String(10), default="unknown")  # "true", "false", "unknown"
    
    # Relationship
    section = relationship("SectionModel", back_populates="citations")


class DatabaseManager:
    """
    Manager for database operations
    Handles connection pooling and session management
    """
    
    def __init__(self, database_url: str = "postgresql://localhost/alpha_clinical"):
        self.engine = create_engine(database_url, pool_size=10, max_overflow=20)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
    
    def create_tables(self):
        """Create all tables"""
        Base.metadata.create_all(bind=self.engine)
    
    def get_session(self) -> Session:
        """Get database session"""
        return self.SessionLocal()
    
    def close(self):
        """Close database connection"""
        self.engine.dispose()


class AuditPersistence:
    """
    Handles persistence of audit records to database
    Maintains FDA 21 CFR Part 11 compliance
    """
    
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
    
    def save_audit_record(
        self,
        agent_id: str,
        agent_version: str,
        action: str,
        input_hash: str,
        output_hash: str,
        input_data: Optional[Dict] = None,
        output_data: Optional[Dict] = None,
        rationale: str = "",
        document_id: Optional[str] = None,
        human_approval: Optional[str] = None,
        electronic_signature: Optional[str] = None
    ) -> str:
        """
        Save audit record to database
        Returns record_id
        """
        session = self.db.get_session()
        try:
            record = AuditRecordModel(
                document_id=document_id,
                agent_id=agent_id,
                agent_version=agent_version,
                action=action,
                input_hash=input_hash,
                output_hash=output_hash,
                input_data=input_data,
                output_data=output_data,
                rationale=rationale,
                human_approval=human_approval,
                electronic_signature=electronic_signature
            )
            
            session.add(record)
            session.commit()
            
            return record.id
        finally:
            session.close()
    
    def get_audit_trail(
        self,
        document_id: Optional[str] = None,
        agent_id: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """
        Retrieve audit trail for FDA inspection
        Supports filtering by document, agent, and time range
        """
        session = self.db.get_session()
        try:
            query = session.query(AuditRecordModel)
            
            if document_id:
                query = query.filter(AuditRecordModel.document_id == document_id)
            if agent_id:
                query = query.filter(AuditRecordModel.agent_id == agent_id)
            if start_time:
                query = query.filter(AuditRecordModel.timestamp >= start_time)
            if end_time:
                query = query.filter(AuditRecordModel.timestamp <= end_time)
            
            records = query.order_by(AuditRecordModel.timestamp).all()
            
            return [
                {
                    "record_id": r.id,
                    "document_id": r.document_id,
                    "agent_id": r.agent_id,
                    "agent_version": r.agent_version,
                    "action": r.action,
                    "input_hash": r.input_hash,
                    "output_hash": r.output_hash,
                    "timestamp": r.timestamp.isoformat(),
                    "rationale": r.rationale,
                    "human_approval": r.human_approval,
                    "electronic_signature": r.electronic_signature
                }
                for r in records
            ]
        finally:
            session.close()
    
    def verify_data_integrity(self, record_id: str) -> bool:
        """
        Verify data integrity by recomputing hashes
        Returns True if data is intact
        """
        session = self.db.get_session()
        try:
            record = session.query(AuditRecordModel).filter(
                AuditRecordModel.id == record_id
            ).first()
            
            if not record:
                return False
            
            # Recompute hashes
            import hashlib
            import json
            
            input_str = json.dumps(record.input_data, sort_keys=True, default=str)
            output_str = json.dumps(record.output_data, sort_keys=True, default=str)
            
            input_hash_computed = hashlib.sha256(input_str.encode()).hexdigest()
            output_hash_computed = hashlib.sha256(output_str.encode()).hexdigest()
            
            return (
                input_hash_computed == record.input_hash and
                output_hash_computed == record.output_hash
            )
        finally:
            session.close()


# Global instance
db_manager = DatabaseManager()


def init_database(database_url: str = "postgresql://localhost/alpha_clinical"):
    """Initialize database with tables"""
    global db_manager
    db_manager = DatabaseManager(database_url)
    db_manager.create_tables()
    return db_manager
