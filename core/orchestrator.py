"""
Clinical Orchestrator - Central Workflow Engine
Coordinates all 10 agents through the complete CSR generation pipeline
Implements state machine for workflow management with FDA compliance
"""

from typing import Any, Dict, List, Optional, Type
from datetime import datetime
from enum import Enum
import uuid
import json

from .base_agent import BaseAgent, AgentStatus
from .message_protocol import (
    ClinicalMessage, MessageBus, MessageType, 
    MessagePriority, MessageTemplates
)


class WorkflowStage(Enum):
    """Stages of CSR generation workflow"""
    IDLE = "idle"
    PROTOCOL_ANALYSIS = "protocol_analysis"
    RISK_PREDICTION = "risk_prediction"
    SECTION_WRITING = "section_writing"
    PARALLEL_VALIDATION = "parallel_validation"
    CONFLICT_RESOLUTION = "conflict_resolution"
    HUMAN_REVIEW = "human_review"
    META_VALIDATION = "meta_validation"
    FINAL_COMPILATION = "final_compilation"
    COMPLETED = "completed"
    ERROR = "error"


class WorkflowState:
    """
    Global state management for workflow
    Tracks progress across all agents and stages
    """
    
    def __init__(self, document_id: str):
        self.document_id = document_id
        self.current_stage = WorkflowStage.IDLE
        self.stage_history: List[Dict] = []
        
        # Agent states
        self.agent_states: Dict[str, Dict] = {}
        
        # Document sections
        self.sections: Dict[str, Dict] = {
            "Methods": {"status": "pending", "draft": None, "approved": False},
            "Results": {"status": "pending", "draft": None, "approved": False},
            "Safety": {"status": "pending", "draft": None, "approved": False},
            "Discussion": {"status": "pending", "draft": None, "approved": False},
            "Abstract": {"status": "pending", "draft": None, "approved": False}
        }
        
        # Validation results
        self.validation_results: List[Dict] = []
        self.pending_conflicts: List[Dict] = []
        
        # Human review tracking
        self.pending_human_reviews: List[str] = []
        self.completed_human_reviews: List[Dict] = []
        
        # Audit trail
        self.start_time: Optional[datetime] = None
        self.end_time: Optional[datetime] = None
        
    def transition_to(self, new_stage: WorkflowStage, rationale: str = ""):
        """Record stage transition with timestamp"""
        transition = {
            "from": self.current_stage.value,
            "to": new_stage.value,
            "timestamp": datetime.utcnow().isoformat(),
            "rationale": rationale
        }
        self.stage_history.append(transition)
        self.current_stage = new_stage
        
        if new_stage == WorkflowStage.PROTOCOL_ANALYSIS:
            self.start_time = datetime.utcnow()
        elif new_stage in [WorkflowStage.COMPLETED, WorkflowStage.ERROR]:
            self.end_time = datetime.utcnow()
    
    def update_section(self, section_name: str, status: str, 
                      draft: Optional[str] = None):
        """Update status of a document section"""
        if section_name in self.sections:
            self.sections[section_name]["status"] = status
            if draft:
                self.sections[section_name]["draft"] = draft
    
    def approve_section(self, section_name: str, approver: str):
        """Mark section as approved with electronic signature"""
        if section_name in self.sections:
            self.sections[section_name]["approved"] = True
            self.sections[section_name]["approved_by"] = approver
            self.sections[section_name]["approved_at"] = datetime.utcnow().isoformat()
    
    def add_validation_result(self, agent_id: str, result: Dict):
        """Add validation result from any agent"""
        self.validation_results.append({
            "agent_id": agent_id,
            "timestamp": datetime.utcnow().isoformat(),
            "result": result
        })
    
    def get_progress(self) -> Dict[str, Any]:
        """Get current workflow progress summary"""
        total_sections = len(self.sections)
        completed_sections = sum(1 for s in self.sections.values() if s["approved"])
        
        return {
            "document_id": self.document_id,
            "current_stage": self.current_stage.value,
            "progress_percentage": (completed_sections / total_sections) * 100,
            "sections_status": self.sections,
            "pending_conflicts": len(self.pending_conflicts),
            "pending_human_reviews": len(self.pending_human_reviews),
            "elapsed_time_minutes": self._get_elapsed_time()
        }
    
    def _get_elapsed_time(self) -> Optional[float]:
        """Calculate elapsed time in minutes"""
        if self.start_time:
            end = self.end_time or datetime.utcnow()
            return (end - self.start_time).total_seconds() / 60
        return None
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize state for storage/audit"""
        return {
            "document_id": self.document_id,
            "current_stage": self.current_stage.value,
            "stage_history": self.stage_history,
            "agent_states": self.agent_states,
            "sections": self.sections,
            "validation_results": self.validation_results,
            "pending_conflicts": self.pending_conflicts,
            "completed_human_reviews": self.completed_human_reviews,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None
        }


class ClinicalOrchestrator:
    """
    Central orchestrator for the 10-agent clinical document system.
    
    Responsibilities:
    1. Manage workflow state machine
    2. Route tasks to appropriate agents
    3. Handle parallel execution
    4. Coordinate human review checkpoints
    5. Maintain audit trail
    6. Handle errors and recovery
    
    Usage:
        orchestrator = ClinicalOrchestrator()
        orchestrator.register_agent(ProtocolAnalyzer())
        orchestrator.register_agent(SectionWriter())
        # ... register all 10 agents
        
        result = orchestrator.execute_workflow(protocol_path="/path/to/protocol.pdf")
    """
    
    def __init__(self):
        self.agents: Dict[str, BaseAgent] = {}
        self.message_bus = MessageBus()
        self.state: Optional[WorkflowState] = None
        
        # Agent ordering for sequential stages
        self.agent_execution_order = [
            "RiskPredictor",      # Agent 9: Predict before starting
            "ProtocolAnalyzer",   # Agent 1: Extract structure
            "SectionWriter",      # Agent 2: Generate drafts
            "StatisticalValidator", # Agent 3: Check numbers
            "ComplianceChecker",  # Agent 4: Check FDA/ICH
            "CrossRefValidator",  # Agent 5: Check consistency
            "MetaValidator",      # Agent 10: QA all agents
            "ConflictResolver",   # Agent 8: Resolve conflicts
            "HumanCoordinator",   # Agent 6: Human review
            "FinalCompiler"       # Agent 7: Assemble final
        ]
    
    def register_agent(self, agent: BaseAgent) -> None:
        """Register agent with orchestrator and message bus"""
        self.agents[agent.agent_id] = agent
        self.message_bus.subscribe(agent.agent_id, self._route_message)
    
    def _route_message(self, message: ClinicalMessage) -> None:
        """Route incoming message to appropriate agent"""
        recipient = message.header.recipient
        if recipient in self.agents:
            self.agents[recipient].receive_message(message)
    
    def execute_workflow(self, protocol_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute complete CSR generation workflow
        
        Args:
            protocol_data: Structured protocol information
            
        Returns:
            Final CSR package with audit trail
        """
        # Initialize workflow
        document_id = str(uuid.uuid4())
        self.state = WorkflowState(document_id)
        
        try:
            # Stage 1: Risk Prediction (pre-execution analysis)
            self._execute_stage_risk_prediction(protocol_data)
            
            # Stage 2: Protocol Analysis
            protocol_structure = self._execute_stage_protocol_analysis(protocol_data)
            
            # Stage 3: Parallel Section Writing
            drafts = self._execute_stage_section_writing(protocol_structure)
            
            # Stage 4: Parallel Validation
            validation_results = self._execute_stage_parallel_validation(drafts)
            
            # Stage 5: Meta-Validation
            meta_result = self._execute_stage_meta_validation(validation_results)
            
            # Stage 6: Conflict Resolution (if needed)
            if self.state.pending_conflicts:
                self._execute_stage_conflict_resolution()
            
            # Stage 7: Human Review Checkpoints
            self._execute_stage_human_review()
            
            # Stage 8: Final Compilation
            final_package = self._execute_stage_final_compilation()
            
            return final_package
            
        except Exception as e:
            self.state.transition_to(WorkflowStage.ERROR, str(e))
            return {
                "status": "error",
                "error": str(e),
                "state": self.state.to_dict()
            }
    
    def _execute_stage_risk_prediction(self, protocol_data: Dict) -> None:
        """Stage 1: Predict complexity and risks before execution"""
        self.state.transition_to(WorkflowStage.RISK_PREDICTION)
        
        if "RiskPredictor" in self.agents:
            predictor = self.agents["RiskPredictor"]
            result = predictor.execute(protocol_data)
            
            # Store prediction in state
            self.state.agent_states["RiskPredictor"] = result
            
            # Broadcast to all agents
            message = MessageTemplates.protocol_analyzed(
                sender="RiskPredictor",
                protocol_data={"risk_prediction": result}
            )
            self.message_bus.publish(message)
    
    def _execute_stage_protocol_analysis(self, protocol_data: Dict) -> Dict:
        """Stage 2: Extract study structure from protocol"""
        self.state.transition_to(WorkflowStage.PROTOCOL_ANALYSIS)
        
        analyzer = self.agents.get("ProtocolAnalyzer")
        if not analyzer:
            raise ValueError("ProtocolAnalyzer not registered")
        
        result = analyzer.execute(protocol_data)
        
        # Store and broadcast
        self.state.agent_states["ProtocolAnalyzer"] = result
        
        message = MessageTemplates.protocol_analyzed(
            sender="ProtocolAnalyzer",
            protocol_data=result
        )
        self.message_bus.publish(message)
        
        return result
    
    def _execute_stage_section_writing(self, protocol_structure: Dict) -> Dict[str, str]:
        """Stage 3: Write document sections (parallel where possible)"""
        self.state.transition_to(WorkflowStage.SECTION_WRITING)
        
        writer = self.agents.get("SectionWriter")
        if not writer:
            raise ValueError("SectionWriter not registered")
        
        # For MVP: sequential writing
        # For production: parallel execution with ThreadPoolExecutor
        sections = ["Methods", "Results", "Safety"]
        drafts = {}
        
        for section in sections:
            result = writer.execute({
                "protocol_structure": protocol_structure,
                "section_name": section
            })
            
            drafts[section] = result.get("draft", "")
            self.state.update_section(section, "draft_complete", drafts[section])
            
            # Send to MetaValidator
            message = MessageTemplates.section_draft(
                sender="SectionWriter",
                section_name=section,
                draft_text=drafts[section],
                confidence=result.get("confidence", 0.9)
            )
            self.message_bus.publish(message)
        
        return drafts
    
    def _execute_stage_parallel_validation(self, drafts: Dict[str, str]) -> List[Dict]:
        """Stage 4: Run all validators in parallel"""
        self.state.transition_to(WorkflowStage.PARALLEL_VALIDATION)
        
        results = []
        
        # Statistical validation
        if "StatisticalValidator" in self.agents:
            stat_result = self.agents["StatisticalValidator"].execute({
                "drafts": drafts
            })
            results.append({"agent": "StatisticalValidator", "result": stat_result})
            self.state.add_validation_result("StatisticalValidator", stat_result)
        
        # Compliance validation
        if "ComplianceChecker" in self.agents:
            compliance_result = self.agents["ComplianceChecker"].execute({
                "drafts": drafts
            })
            results.append({"agent": "ComplianceChecker", "result": compliance_result})
            self.state.add_validation_result("ComplianceChecker", compliance_result)
        
        # Cross-reference validation
        if "CrossRefValidator" in self.agents:
            crossref_result = self.agents["CrossRefValidator"].execute({
                "drafts": drafts
            })
            results.append({"agent": "CrossRefValidator", "result": crossref_result})
            self.state.add_validation_result("CrossRefValidator", crossref_result)
        
        return results
    
    def _execute_stage_meta_validation(self, validation_results: List[Dict]) -> Dict:
        """Stage 5: Meta-Validator QA check"""
        self.state.transition_to(WorkflowStage.META_VALIDATION)
        
        if "MetaValidator" in self.agents:
            meta_result = self.agents["MetaValidator"].execute({
                "validation_results": validation_results,
                "sections": self.state.sections
            })
            
            # Check for conflicts
            if meta_result.get("conflicts_detected"):
                self.state.pending_conflicts = meta_result.get("conflicts", [])
            
            return meta_result
        
        return {"status": "skipped", "reason": "MetaValidator not registered"}
    
    def _execute_stage_conflict_resolution(self) -> None:
        """Stage 6: Resolve inter-agent conflicts"""
        self.state.transition_to(WorkflowStage.CONFLICT_RESOLUTION)
        
        if "ConflictResolver" in self.agents and self.state.pending_conflicts:
            resolver = self.agents["ConflictResolver"]
            
            for conflict in self.state.pending_conflicts:
                result = resolver.execute({
                    "conflict": conflict,
                    "agent_outputs": self.state.agent_states
                })
                
                # If auto-resolved, update state
                if result.get("resolved"):
                    self.state.pending_conflicts.remove(conflict)
    
    def _execute_stage_human_review(self) -> None:
        """Stage 7: Human review checkpoints"""
        self.state.transition_to(WorkflowStage.HUMAN_REVIEW)
        
        if "HumanCoordinator" in self.agents:
            coordinator = self.agents["HumanCoordinator"]
            
            # Request review for each section
            for section_name, section_data in self.state.sections.items():
                if section_data["status"] == "draft_complete":
                    review_id = coordinator.execute({
                        "section_name": section_name,
                        "draft": section_data["draft"],
                        "validation_issues": self._get_section_issues(section_name)
                    })
                    
                    self.state.pending_human_reviews.append(review_id)
    
    def _execute_stage_final_compilation(self) -> Dict[str, Any]:
        """Stage 8: Compile final CSR package"""
        self.state.transition_to(WorkflowStage.FINAL_COMPILATION)
        
        compiler = self.agents.get("FinalCompiler")
        if not compiler:
            # Fallback: simple aggregation
            final_package = {
                "document_id": self.state.document_id,
                "sections": self.state.sections,
                "audit_trail": self._compile_audit_trail()
            }
        else:
            final_package = compiler.execute({
                "sections": self.state.sections,
                "validation_results": self.state.validation_results
            })
        
        self.state.transition_to(WorkflowStage.COMPLETED)
        
        return {
            "status": "completed",
            "package": final_package,
            "state": self.state.to_dict(),
            "performance": self._get_performance_metrics()
        }
    
    def _get_section_issues(self, section_name: str) -> List[Dict]:
        """Get validation issues for specific section"""
        issues = []
        for result in self.state.validation_results:
            section_issues = result["result"].get("section_issues", {})
            if section_name in section_issues:
                issues.extend(section_issues[section_name])
        return issues
    
    def _compile_audit_trail(self) -> Dict[str, List]:
        """Compile complete audit trail from all agents"""
        audit_trail = {}
        for agent_id, agent in self.agents.items():
            audit_trail[agent_id] = agent.get_audit_trail()
        return audit_trail
    
    def _get_performance_metrics(self) -> Dict[str, Any]:
        """Get performance metrics from all agents"""
        metrics = {}
        for agent_id, agent in self.agents.items():
            metrics[agent_id] = agent.get_performance_metrics()
        return metrics
    
    def get_workflow_status(self) -> Dict[str, Any]:
        """Get current workflow status"""
        if not self.state:
            return {"status": "no_active_workflow"}
        return self.state.get_progress()
    
    def pause_workflow(self) -> None:
        """Pause workflow (e.g., for manual intervention)"""
        if self.state:
            # Implementation would save state and pause execution
            pass
    
    def resume_workflow(self) -> None:
        """Resume paused workflow"""
        if self.state:
            # Implementation would restore state and continue
            pass
