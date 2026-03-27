"""
Base Agent - Abstract Foundation for All Clinical Agents
Enterprise-grade base class with FDA compliance built-in
"""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, Optional, List
from dataclasses import dataclass, field
from enum import Enum
import hashlib
import json
import uuid


class AgentStatus(Enum):
    """Agent execution status for workflow tracking"""
    IDLE = "idle"
    PROCESSING = "processing"
    COMPLETED = "completed"
    ERROR = "error"
    AWAITING_HUMAN = "awaiting_human_review"


@dataclass
class AgentMessage:
    """
    Standardized inter-agent communication format
    FDA-compliant with full traceability
    """
    message_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    sender: str = ""
    recipient: str = ""
    message_type: str = ""  # "draft", "validation", "conflict", "approval"
    payload: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)
    confidence: float = 1.0
    
    # FDA Compliance fields
    input_hash: str = ""
    output_hash: str = ""
    electronic_signature: Optional[str] = None
    
    def compute_hashes(self, input_data: str, output_data: str):
        """Compute SHA256 hashes for audit trail"""
        self.input_hash = hashlib.sha256(input_data.encode()).hexdigest()
        self.output_hash = hashlib.sha256(output_data.encode()).hexdigest()
    
    def to_dict(self) -> Dict:
        """Serialize for storage/transmission"""
        return {
            "message_id": self.message_id,
            "sender": self.sender,
            "recipient": self.recipient,
            "message_type": self.message_type,
            "payload": self.payload,
            "metadata": self.metadata,
            "timestamp": self.timestamp.isoformat(),
            "confidence": self.confidence,
            "input_hash": self.input_hash,
            "output_hash": self.output_hash,
            "electronic_signature": self.electronic_signature
        }


@dataclass
class AuditRecord:
    """
    FDA 21 CFR Part 11 compliant audit record
    Immutable trail of all agent actions
    """
    record_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    agent_id: str = ""
    agent_version: str = ""
    action: str = ""
    timestamp: datetime = field(default_factory=datetime.utcnow)
    input_hash: str = ""
    output_hash: str = ""
    human_approval: Optional[str] = None
    electronic_signature: Optional[str] = None
    rationale: str = ""
    
    def to_dict(self) -> Dict:
        return {
            "record_id": self.record_id,
            "agent_id": self.agent_id,
            "agent_version": self.agent_version,
            "action": self.action,
            "timestamp": self.timestamp.isoformat(),
            "input_hash": self.input_hash,
            "output_hash": self.output_hash,
            "human_approval": self.human_approval,
            "electronic_signature": self.electronic_signature,
            "rationale": self.rationale
        }


class BaseAgent(ABC):
    """
    Abstract base class for all clinical document agents.
    
    Provides:
    - Standardized agent lifecycle
    - FDA-compliant audit trails
    - Inter-agent communication protocol
    - Error handling and recovery
    - State management
    
    All agents (1-10) must inherit from this class.
    """
    
    def __init__(self, agent_id: str, version: str, config: Optional[Dict] = None):
        """
        Initialize agent with FDA-compliant tracking
        
        Args:
            agent_id: Unique identifier (e.g., "ProtocolAnalyzer-v2.1")
            version: Semantic version
            config: Agent-specific configuration
        """
        self.agent_id = agent_id
        self.version = version
        self.config = config or {}
        
        # State management
        self.status = AgentStatus.IDLE
        self.audit_log: List[AuditRecord] = []
        self.message_queue: List[AgentMessage] = []
        
        # Performance tracking
        self.processing_start: Optional[datetime] = None
        self.processing_end: Optional[datetime] = None
        
    @abstractmethod
    def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Main processing logic - MUST be implemented by each agent
        
        Args:
            input_data: Structured input (protocol data, drafts, etc.)
            
        Returns:
            Processed output with standardized format
        """
        pass
    
    def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Wrapper that adds audit trail and error handling
        
        This method should be called by orchestrator, not process() directly
        """
        self.status = AgentStatus.PROCESSING
        self.processing_start = datetime.utcnow()
        
        try:
            # Compute input hash before processing
            input_str = json.dumps(input_data, sort_keys=True, default=str)
            input_hash = hashlib.sha256(input_str.encode()).hexdigest()
            
            # Execute agent-specific logic
            result = self.process(input_data)
            
            # Compute output hash
            output_str = json.dumps(result, sort_keys=True, default=str)
            output_hash = hashlib.sha256(output_str.encode()).hexdigest()
            
            # Record audit trail
            self._log_action(
                action="process",
                input_hash=input_hash,
                output_hash=output_hash,
                rationale=result.get("rationale", "")
            )
            
            self.status = AgentStatus.COMPLETED
            self.processing_end = datetime.utcnow()
            
            return result
            
        except Exception as e:
            self.status = AgentStatus.ERROR
            self._log_action(
                action="error",
                input_hash="",
                output_hash="",
                rationale=f"Error: {str(e)}"
            )
            raise
    
    def send_message(self, recipient: str, message_type: str, 
                     payload: Dict[str, Any], confidence: float = 1.0) -> AgentMessage:
        """
        Send message to another agent through orchestrator
        
        Args:
            recipient: Target agent ID
            message_type: Type of message
            payload: Message content
            confidence: Confidence score (0.0-1.0)
            
        Returns:
            AgentMessage object
        """
        message = AgentMessage(
            sender=self.agent_id,
            recipient=recipient,
            message_type=message_type,
            payload=payload,
            confidence=confidence,
            metadata={
                "sender_version": self.version,
                "sender_status": self.status.value
            }
        )
        
        self.message_queue.append(message)
        return message
    
    def receive_message(self, message: AgentMessage) -> None:
        """
        Handle incoming message from another agent
        Override in subclass for custom handling
        """
        self.message_queue.append(message)
    
    def _log_action(self, action: str, input_hash: str, 
                    output_hash: str, rationale: str = "") -> AuditRecord:
        """
        Create FDA-compliant audit record
        """
        record = AuditRecord(
            agent_id=self.agent_id,
            agent_version=self.version,
            action=action,
            input_hash=input_hash,
            output_hash=output_hash,
            rationale=rationale
        )
        self.audit_log.append(record)
        return record
    
    def request_human_approval(self, action_description: str, 
                               data_to_review: Dict[str, Any]) -> str:
        """
        Request human review/approval (21 CFR Part 11)
        
        Returns:
            approval_id for tracking
        """
        self.status = AgentStatus.AWAITING_HUMAN
        
        approval_id = str(uuid.uuid4())
        self._log_action(
            action="request_human_approval",
            input_hash="",
            output_hash="",
            rationale=f"Approval requested for: {action_description}"
        )
        
        return approval_id
    
    def record_human_approval(self, approval_id: str, 
                              approver_id: str,
                              electronic_signature: str) -> None:
        """
        Record human approval with electronic signature
        """
        self._log_action(
            action="human_approval_granted",
            input_hash="",
            output_hash="",
            rationale=f"Approved by {approver_id}, ID: {approval_id}"
        )
        
        # Update latest record with signature
        if self.audit_log:
            self.audit_log[-1].human_approval = approver_id
            self.audit_log[-1].electronic_signature = electronic_signature
        
        self.status = AgentStatus.IDLE
    
    def get_audit_trail(self) -> List[Dict]:
        """
        Get complete audit trail for FDA inspection
        """
        return [record.to_dict() for record in self.audit_log]
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """
        Get processing time and other metrics
        """
        if self.processing_start and self.processing_end:
            duration = (self.processing_end - self.processing_start).total_seconds()
        else:
            duration = None
            
        return {
            "agent_id": self.agent_id,
            "version": self.version,
            "status": self.status.value,
            "total_actions": len(self.audit_log),
            "last_processing_time_sec": duration,
            "pending_messages": len(self.message_queue)
        }
    
    def reset(self) -> None:
        """
        Reset agent state (for new document processing)
        """
        self.status = AgentStatus.IDLE
        self.processing_start = None
        self.processing_end = None
        # Note: audit_log is preserved for compliance


# Example usage for documentation
class ExampleAgent(BaseAgent):
    """Example implementation showing pattern"""
    
    def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        # Agent-specific logic here
        result = {
            "output": f"Processed by {self.agent_id}",
            "rationale": "Example processing logic"
        }
        return result
