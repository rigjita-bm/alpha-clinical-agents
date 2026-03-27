"""
Structured logging for Alpha Clinical Agents
JSON-formatted logs with correlation IDs for observability
"""

import json
import logging
import sys
from datetime import datetime
from typing import Any, Dict, Optional
from contextvars import ContextVar
import uuid

# Context variable for correlation ID
correlation_id_var: ContextVar[str] = ContextVar('correlation_id', default='')


class JSONFormatter(logging.Formatter):
    """JSON formatter for structured logging"""
    
    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "correlation_id": correlation_id_var.get() or getattr(record, 'correlation_id', ''),
            "agent_id": getattr(record, 'agent_id', ''),
            "document_id": getattr(record, 'document_id', ''),
        }
        
        # Add extra fields if present
        if hasattr(record, 'extra'):
            log_data.update(record.extra)
        
        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        
        return json.dumps(log_data, default=str)


def setup_logging(log_level: str = "INFO", log_format: str = "json") -> logging.Logger:
    """
    Setup structured logging
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR)
        log_format: Format type (json, text)
    """
    logger = logging.getLogger("alpha_clinical")
    logger.setLevel(getattr(logging, log_level.upper()))
    
    # Clear existing handlers
    logger.handlers = []
    
    # Console handler
    handler = logging.StreamHandler(sys.stdout)
    
    if log_format == "json":
        handler.setFormatter(JSONFormatter())
    else:
        handler.setFormatter(logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        ))
    
    logger.addHandler(handler)
    
    return logger


class AgentLogger:
    """
    Logger wrapper for agent-specific logging
    Automatically adds agent context to all logs
    """
    
    def __init__(self, agent_id: str, logger: Optional[logging.Logger] = None):
        self.agent_id = agent_id
        self.logger = logger or logging.getLogger("alpha_clinical")
    
    def _log(self, level: str, message: str, **kwargs):
        """Internal log method with context"""
        extra = {
            'agent_id': self.agent_id,
            'extra': kwargs
        }
        
        # Add correlation ID if available
        corr_id = correlation_id_var.get()
        if corr_id:
            extra['correlation_id'] = corr_id
        
        getattr(self.logger, level)(message, extra=extra)
    
    def debug(self, message: str, **kwargs):
        self._log('debug', message, **kwargs)
    
    def info(self, message: str, **kwargs):
        self._log('info', message, **kwargs)
    
    def warning(self, message: str, **kwargs):
        self._log('warning', message, **kwargs)
    
    def error(self, message: str, **kwargs):
        self._log('error', message, **kwargs)
    
    def agent_execution_started(self, document_id: str, input_size: int):
        """Log agent execution start"""
        self.info(
            "agent_execution_started",
            document_id=document_id,
            input_size_bytes=input_size,
            timestamp_utc=datetime.utcnow().isoformat()
        )
    
    def agent_execution_completed(self, document_id: str, output_size: int, duration_ms: float):
        """Log agent execution completion"""
        self.info(
            "agent_execution_completed",
            document_id=document_id,
            output_size_bytes=output_size,
            duration_ms=duration_ms,
            timestamp_utc=datetime.utcnow().isoformat()
        )
    
    def agent_error(self, document_id: str, error: str, error_type: str):
        """Log agent error"""
        self.error(
            "agent_execution_failed",
            document_id=document_id,
            error=error,
            error_type=error_type,
            timestamp_utc=datetime.utcnow().isoformat()
        )
    
    def validation_finding(self, document_id: str, finding_type: str, severity: str, details: Dict):
        """Log validation finding"""
        self.info(
            "validation_finding",
            document_id=document_id,
            finding_type=finding_type,
            severity=severity,
            details=details
        )
    
    def hallucination_detected(self, document_id: str, claim: str, confidence: float):
        """Log hallucination detection"""
        self.warning(
            "hallucination_detected",
            document_id=document_id,
            claim=claim,
            confidence=confidence,
            action_required="human_review"
        )


def set_correlation_id(correlation_id: Optional[str] = None) -> str:
    """
    Set correlation ID for request tracing
    Returns the correlation ID
    """
    if correlation_id is None:
        correlation_id = str(uuid.uuid4())
    correlation_id_var.set(correlation_id)
    return correlation_id


def get_correlation_id() -> str:
    """Get current correlation ID"""
    return correlation_id_var.get()


class LogContext:
    """Context manager for correlation ID scoping"""
    
    def __init__(self, correlation_id: Optional[str] = None):
        self.correlation_id = correlation_id or str(uuid.uuid4())
        self.token = None
    
    def __enter__(self):
        self.token = correlation_id_var.set(self.correlation_id)
        return self.correlation_id
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.token:
            correlation_id_var.reset(self.token)


# Initialize logging on module import
logger = setup_logging()
