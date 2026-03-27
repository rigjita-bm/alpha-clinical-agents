"""
Alpha Clinical Agents - Core Foundation Module

This module provides the foundational infrastructure for the 10-agent
clinical document automation system.

Components:
- BaseAgent: Abstract base class for all agents with FDA compliance
- MessageProtocol: Inter-agent communication standard
- Orchestrator: Central workflow engine

Usage:
    from core import BaseAgent, ClinicalOrchestrator, MessageBus
"""

from .base_agent import BaseAgent, AgentStatus, AgentMessage, AuditRecord
from .message_protocol import (
    ClinicalMessage, MessageBus, MessageType, 
    MessagePriority, MessageTemplates
)
from .orchestrator import ClinicalOrchestrator, WorkflowState, WorkflowStage

__all__ = [
    # Base
    'BaseAgent',
    'AgentStatus',
    'AgentMessage',
    'AuditRecord',
    # Messaging
    'ClinicalMessage',
    'MessageBus',
    'MessageType',
    'MessagePriority',
    'MessageTemplates',
    # Orchestration
    'ClinicalOrchestrator',
    'WorkflowState',
    'WorkflowStage'
]

__version__ = "1.0.0"
