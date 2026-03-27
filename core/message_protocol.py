"""
Message Protocol - Standardized Inter-Agent Communication
Ensures consistent, traceable, and type-safe messaging across all 10 agents
"""

from typing import Any, Dict, List, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import uuid
import json


class MessagePriority(Enum):
    """Message priority for queue management"""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


class MessageType(Enum):
    """Standardized message types across the ecosystem"""
    # Core workflow messages
    PROTOCOL_ANALYZED = "protocol_analyzed"
    SECTION_DRAFT = "section_draft"
    VALIDATION_RESULT = "validation_result"
    COMPLIANCE_CHECK = "compliance_check"
    CROSSREF_CHECK = "crossref_check"
    
    # Human interaction
    HUMAN_REVIEW_REQUEST = "human_review_request"
    HUMAN_APPROVAL = "human_approval"
    HUMAN_REJECTION = "human_rejection"
    
    # System messages
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"
    
    # Meta messages
    CONFLICT_DETECTED = "conflict_detected"
    CONFLICT_RESOLVED = "conflict_resolved"
    RISK_PREDICTION = "risk_prediction"
    AUTO_CORRECTION = "auto_correction"


@dataclass
class MessageHeader:
    """Message metadata and routing information"""
    message_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    correlation_id: str = ""  # Links related messages
    sender: str = ""
    recipient: str = ""  # "broadcast" for all agents
    message_type: MessageType = MessageType.INFO
    priority: MessagePriority = MessagePriority.NORMAL
    timestamp: datetime = field(default_factory=datetime.utcnow)
    ttl: int = 3600  # Time to live in seconds
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "message_id": self.message_id,
            "correlation_id": self.correlation_id,
            "sender": self.sender,
            "recipient": self.recipient,
            "message_type": self.message_type.value,
            "priority": self.priority.value,
            "timestamp": self.timestamp.isoformat(),
            "ttl": self.ttl
        }


@dataclass
class MessagePayload:
    """Message content with type safety"""
    data: Dict[str, Any] = field(default_factory=dict)
    attachments: List[Dict[str, Any]] = field(default_factory=list)
    context: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "data": self.data,
            "attachments": self.attachments,
            "context": self.context
        }


@dataclass
class ProtocolMessage:
    """Message containing protocol analysis results"""
    study_design: Dict[str, Any] = field(default_factory=dict)
    endpoints: Dict[str, Any] = field(default_factory=dict)
    population: Dict[str, Any] = field(default_factory=dict)
    schedule: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "study_design": self.study_design,
            "endpoints": self.endpoints,
            "population": self.population,
            "schedule": self.schedule
        }


@dataclass
class ValidationMessage:
    """Message containing validation results"""
    is_valid: bool = False
    score: float = 0.0  # 0.0-1.0
    issues: List[Dict[str, Any]] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    confidence: float = 1.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "is_valid": self.is_valid,
            "score": self.score,
            "issues": self.issues,
            "recommendations": self.recommendations,
            "confidence": self.confidence
        }


@dataclass  
class ConflictMessage:
    """Message for conflict detection and resolution"""
    conflict_type: str = ""  # "data_mismatch", "logic_error", "regulatory_violation"
    severity: str = "medium"  # "low", "medium", "high", "critical"
    agents_involved: List[str] = field(default_factory=list)
    description: str = ""
    proposed_resolution: Optional[str] = None
    requires_human: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "conflict_type": self.conflict_type,
            "severity": self.severity,
            "agents_involved": self.agents_involved,
            "description": self.description,
            "proposed_resolution": self.proposed_resolution,
            "requires_human": self.requires_human
        }


class ClinicalMessage:
    """
    Complete message structure for inter-agent communication
    Combines header, payload, and type-specific content
    """
    
    def __init__(self,
                 sender: str,
                 recipient: str,
                 message_type: MessageType,
                 payload_data: Dict[str, Any],
                 priority: MessagePriority = MessagePriority.NORMAL,
                 correlation_id: str = ""):
        
        self.header = MessageHeader(
            sender=sender,
            recipient=recipient,
            message_type=message_type,
            priority=priority,
            correlation_id=correlation_id or str(uuid.uuid4())
        )
        
        self.payload = MessagePayload(data=payload_data)
        
    def to_dict(self) -> Dict[str, Any]:
        return {
            "header": self.header.to_dict(),
            "payload": self.payload.to_dict()
        }
    
    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ClinicalMessage':
        """Reconstruct message from dictionary"""
        header_data = data.get("header", {})
        payload_data = data.get("payload", {})
        
        msg = cls(
            sender=header_data.get("sender", ""),
            recipient=header_data.get("recipient", ""),
            message_type=MessageType(header_data.get("message_type", "info")),
            payload_data=payload_data.get("data", {}),
            priority=MessagePriority(header_data.get("priority", "normal")),
            correlation_id=header_data.get("correlation_id", "")
        )
        
        msg.header.message_id = header_data.get("message_id", str(uuid.uuid4()))
        msg.header.timestamp = datetime.fromisoformat(header_data.get("timestamp"))
        
        return msg


class MessageBus:
    """
    Central message bus for agent communication
    Implements publish-subscribe pattern with routing
    """
    
    def __init__(self):
        self.subscribers: Dict[str, List[Callable]] = {}  # agent_id -> callbacks
        self.message_queue: List[ClinicalMessage] = []
        self.message_history: List[Dict] = []
        
    def subscribe(self, agent_id: str, callback: Callable) -> None:
        """Register agent to receive messages"""
        if agent_id not in self.subscribers:
            self.subscribers[agent_id] = []
        self.subscribers[agent_id].append(callback)
    
    def unsubscribe(self, agent_id: str, callback: Callable) -> None:
        """Remove agent subscription"""
        if agent_id in self.subscribers:
            self.subscribers[agent_id].remove(callback)
    
    def publish(self, message: ClinicalMessage) -> None:
        """
        Publish message to recipient(s)
        Supports broadcast (all agents) or specific recipient
        """
        # Store in history
        self.message_history.append(message.to_dict())
        
        # Route to recipient(s)
        if message.header.recipient == "broadcast":
            # Send to all subscribers except sender
            for agent_id, callbacks in self.subscribers.items():
                if agent_id != message.header.sender:
                    for callback in callbacks:
                        callback(message)
        else:
            # Send to specific recipient
            if message.header.recipient in self.subscribers:
                for callback in self.subscribers[message.header.recipient]:
                    callback(message)
        
        # Also add to queue for async processing
        self.message_queue.append(message)
    
    def get_message_history(self, 
                           sender: Optional[str] = None,
                           recipient: Optional[str] = None,
                           message_type: Optional[MessageType] = None) -> List[Dict]:
        """Query message history with filters"""
        results = self.message_history
        
        if sender:
            results = [m for m in results if m["header"]["sender"] == sender]
        
        if recipient:
            results = [m for m in results if m["header"]["recipient"] == recipient]
            
        if message_type:
            results = [m for m in results if m["header"]["message_type"] == message_type.value]
        
        return results
    
    def clear_history(self) -> None:
        """Clear message history (use with caution - affects audit trail)"""
        self.message_history.clear()


# Pre-defined message templates for common scenarios
class MessageTemplates:
    """Factory for common message patterns"""
    
    @staticmethod
    def protocol_analyzed(sender: str, protocol_data: Dict) -> ClinicalMessage:
        return ClinicalMessage(
            sender=sender,
            recipient="broadcast",
            message_type=MessageType.PROTOCOL_ANALYZED,
            payload_data=protocol_data,
            priority=MessagePriority.HIGH
        )
    
    @staticmethod
    def section_draft(sender: str, section_name: str, 
                     draft_text: str, confidence: float) -> ClinicalMessage:
        return ClinicalMessage(
            sender=sender,
            recipient="MetaValidator",
            message_type=MessageType.SECTION_DRAFT,
            payload_data={
                "section_name": section_name,
                "draft_text": draft_text,
                "confidence": confidence
            },
            priority=MessagePriority.NORMAL
        )
    
    @staticmethod
    def validation_failed(sender: str, target_agent: str, 
                         issues: List[Dict]) -> ClinicalMessage:
        return ClinicalMessage(
            sender=sender,
            recipient=target_agent,
            message_type=MessageType.VALIDATION_RESULT,
            payload_data={
                "is_valid": False,
                "issues": issues
            },
            priority=MessagePriority.HIGH
        )
    
    @staticmethod
    def conflict_detected(sender: str, agents_involved: List[str],
                         conflict_type: str, description: str) -> ClinicalMessage:
        return ClinicalMessage(
            sender=sender,
            recipient="ConflictResolver",
            message_type=MessageType.CONFLICT_DETECTED,
            payload_data={
                "agents_involved": agents_involved,
                "conflict_type": conflict_type,
                "description": description
            },
            priority=MessagePriority.CRITICAL
        )
    
    @staticmethod
    def human_review_required(sender: str, approver_role: str,
                            description: str, data: Dict) -> ClinicalMessage:
        return ClinicalMessage(
            sender=sender,
            recipient="HumanCoordinator",
            message_type=MessageType.HUMAN_REVIEW_REQUEST,
            payload_data={
                "approver_role": approver_role,
                "description": description,
                "data": data
            },
            priority=MessagePriority.HIGH
        )
