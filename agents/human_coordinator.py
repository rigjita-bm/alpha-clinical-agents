"""
Human Coordinator - Agent 6
Manages human-in-the-loop review workflows
"""

import uuid
from typing import Any, Dict, List, Optional, Set
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime

import sys
sys.path.append('/root/.openclaw/workspace/alpha-clinical-agents')

from core import BaseAgent


class ReviewType(Enum):
    MEDICAL_REVIEW = "medical_review"
    STATISTICAL_REVIEW = "statistical_review"
    REGULATORY_REVIEW = "regulatory_review"
    SAFETY_REVIEW = "safety_review"
    CLINICAL_REVIEW = "clinical_review"
    QUALITY_CHECK = "quality_check"


class ReviewPriority(Enum):
    CRITICAL = "critical"  # Blocks submission
    HIGH = "high"  # Should address before submission
    MEDIUM = "medium"  # Address if time permits
    LOW = "low"  # Nice to have


class ReviewStatus(Enum):
    PENDING = "pending"
    ASSIGNED = "assigned"
    IN_REVIEW = "in_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    ESCALATED = "escalated"
    OVERDUE = "overdue"


@dataclass
class ReviewTask:
    """A review task for human reviewer"""
    task_id: str
    review_type: ReviewType
    priority: ReviewPriority
    status: ReviewStatus
    section: str
    description: str
    findings: List[Dict]
    assigned_to: Optional[str] = None
    due_date: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    completed_at: Optional[str] = None
    reviewer_notes: str = ""
    resolution: str = ""
    
    def to_dict(self) -> Dict:
        return {
            "task_id": self.task_id,
            "type": self.review_type.value,
            "priority": self.priority.value,
            "status": self.status.value,
            "section": self.section,
            "description": self.description,
            "findings": self.findings,
            "assigned_to": self.assigned_to,
            "due_date": self.due_date,
            "created_at": self.created_at,
            "completed_at": self.completed_at,
            "reviewer_notes": self.reviewer_notes,
            "resolution": self.resolution
        }


class HumanCoordinator(BaseAgent):
    """
    Agent 6: Human Coordinator
    
    Manages human-in-the-loop workflows:
    - Creates review tasks based on agent findings
    - Assigns tasks to appropriate reviewers
    - Tracks review status and deadlines
    - Escalates overdue tasks
    - Compiles reviewer feedback
    - Determines when document is ready for submission
    
    Output: Review workflow status and task assignments
    """
    
    def __init__(self, config: Optional[Dict] = None):
        super().__init__(
            agent_id="HumanCoordinator",
            version="1.0.0",
            config=config
        )
        
        self.tasks: List[ReviewTask] = []
        self.reviewer_roles = {
            ReviewType.MEDICAL_REVIEW: "Medical Director",
            ReviewType.STATISTICAL_REVIEW: "Biostatistician",
            ReviewType.REGULATORY_REVIEW: "Regulatory Affairs",
            ReviewType.SAFETY_REVIEW: "Safety Physician",
            ReviewType.CLINICAL_REVIEW: "Clinical Lead",
            ReviewType.QUALITY_CHECK: "Quality Assurance"
        }
        
        self.review_deadlines = {
            ReviewPriority.CRITICAL: 1,  # 1 day
            ReviewPriority.HIGH: 3,  # 3 days
            ReviewPriority.MEDIUM: 7,  # 1 week
            ReviewPriority.LOW: 14  # 2 weeks
        }
    
    def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Main coordination logic
        
        Args:
            input_data: {
                "validation_results": Dict[str, Any],  # From MetaValidator, StatValidator, etc.
                "section_name": str,
                "auto_approve_threshold": float,  # Score threshold for auto-approval
                "force_review": bool  # Force human review even if score is high
            }
        """
        validation_results = input_data.get("validation_results", {})
        section_name = input_data.get("section_name", "")
        auto_approve_threshold = input_data.get("auto_approve_threshold", 90)
        force_review = input_data.get("force_review", False)
        
        # Create review tasks based on validation findings
        new_tasks = self._create_review_tasks(validation_results, section_name)
        self.tasks.extend(new_tasks)
        
        # Assign tasks
        for task in new_tasks:
            self._assign_task(task)
        
        # Calculate workflow status
        workflow_status = self._calculate_workflow_status()
        
        # Determine if ready for next stage
        ready_for_submission = self._check_submission_readiness(
            workflow_status, auto_approve_threshold, force_review
        )
        
        return {
            "section_name": section_name,
            "workflow_status": workflow_status,
            "total_tasks": len(self.tasks),
            "pending": len([t for t in self.tasks if t.status == ReviewStatus.PENDING]),
            "in_review": len([t for t in self.tasks if t.status == ReviewStatus.IN_REVIEW]),
            "approved": len([t for t in self.tasks if t.status == ReviewStatus.APPROVED]),
            "rejected": len([t for t in self.tasks if t.status == ReviewStatus.REJECTED]),
            "overdue": len([t for t in self.tasks if t.status == ReviewStatus.OVERDUE]),
            "new_tasks": [t.to_dict() for t in new_tasks],
            "all_tasks": [t.to_dict() for t in self.tasks],
            "ready_for_submission": ready_for_submission,
            "estimated_completion": self._estimate_completion(),
            "requires_escalation": workflow_status["critical_pending"] > 0
        }
    
    def _create_review_tasks(self, validation_results: Dict[str, Any],
                            section_name: str) -> List[ReviewTask]:
        """Create review tasks based on validation results"""
        tasks = []
        
        # Process findings from different validators
        validators = [
            ("MetaValidator", validation_results.get("meta_validator", {})),
            ("StatisticalValidator", validation_results.get("statistical_validator", {})),
            ("ComplianceChecker", validation_results.get("compliance_checker", {})),
            ("CrossReferenceValidator", validation_results.get("cross_reference_validator", {})),
            ("HallucinationDetector", validation_results.get("hallucination_detector", {}))
        ]
        
        for validator_name, results in validators:
            if not results:
                continue
            
            findings = results.get("findings", [])
            
            for finding in findings:
                severity = finding.get("severity", "low")
                
                # Map severity to priority
                priority_map = {
                    "critical": ReviewPriority.CRITICAL,
                    "high": ReviewPriority.HIGH,
                    "major": ReviewPriority.HIGH,
                    "medium": ReviewPriority.MEDIUM,
                    "minor": ReviewPriority.LOW
                }
                priority = priority_map.get(severity, ReviewPriority.LOW)
                
                # Determine review type
                review_type = self._determine_review_type(finding, validator_name)
                
                # Create task
                task = ReviewTask(
                    task_id=str(uuid.uuid4())[:8],
                    review_type=review_type,
                    priority=priority,
                    status=ReviewStatus.PENDING,
                    section=section_name,
                    description=f"[{validator_name}] {finding.get('type', 'Issue')}: {finding.get('explanation', '')}",
                    findings=[finding]
                )
                
                # Only create tasks for medium+ priority
                if priority in [ReviewPriority.CRITICAL, ReviewPriority.HIGH, ReviewPriority.MEDIUM]:
                    tasks.append(task)
        
        return tasks
    
    def _determine_review_type(self, finding: Dict, validator_name: str) -> ReviewType:
        """Determine appropriate review type for a finding"""
        finding_type = finding.get("type", "").lower()
        
        # Statistical findings
        if validator_name == "StatisticalValidator" or "p_value" in finding_type or "hazard" in finding_type:
            return ReviewType.STATISTICAL_REVIEW
        
        # Compliance findings
        if validator_name == "ComplianceChecker":
            return ReviewType.REGULATORY_REVIEW
        
        # Safety findings
        if "safety" in finding_type or "adverse" in finding_type or "death" in finding_type:
            return ReviewType.SAFETY_REVIEW
        
        # Medical/clinical findings
        if "endpoint" in finding_type or "efficacy" in finding_type:
            return ReviewType.MEDICAL_REVIEW
        
        # Cross-reference findings
        if validator_name == "CrossReferenceValidator":
            return ReviewType.QUALITY_CHECK
        
        # Hallucination findings
        if validator_name == "HallucinationDetector":
            if finding.get("severity") == "critical":
                return ReviewType.MEDICAL_REVIEW
            return ReviewType.QUALITY_CHECK
        
        return ReviewType.CLINICAL_REVIEW
    
    def _assign_task(self, task: ReviewTask) -> None:
        """Assign task to appropriate reviewer"""
        role = self.reviewer_roles.get(task.review_type, "Clinical Lead")
        task.assigned_to = role
        
        # Set due date
        days = self.review_deadlines.get(task.priority, 7)
        from datetime import timedelta
        due = datetime.now() + timedelta(days=days)
        task.due_date = due.isoformat()
        
        task.status = ReviewStatus.ASSIGNED
    
    def _calculate_workflow_status(self) -> Dict:
        """Calculate overall workflow status"""
        return {
            "critical_pending": len([t for t in self.tasks 
                                    if t.priority == ReviewPriority.CRITICAL 
                                    and t.status in [ReviewStatus.PENDING, ReviewStatus.ASSIGNED]]),
            "high_pending": len([t for t in self.tasks 
                               if t.priority == ReviewPriority.HIGH 
                               and t.status in [ReviewStatus.PENDING, ReviewStatus.ASSIGNED]]),
            "completion_percentage": len([t for t in self.tasks if t.status == ReviewStatus.APPROVED]) / max(len(self.tasks), 1) * 100,
            "blocked": len([t for t in self.tasks if t.status == ReviewStatus.REJECTED]) > 0
        }
    
    def _check_submission_readiness(self, workflow_status: Dict,
                                   threshold: float,
                                   force_review: bool) -> bool:
        """Check if document is ready for submission"""
        # Blocked if critical issues pending
        if workflow_status["critical_pending"] > 0:
            return False
        
        # Blocked if any rejected
        if workflow_status["blocked"]:
            return False
        
        # Force review overrides auto-approval
        if force_review:
            return all(t.status == ReviewStatus.APPROVED for t in self.tasks)
        
        # Auto-approve if score high and no critical/high issues
        if workflow_status["high_pending"] == 0:
            return True
        
        return False
    
    def _estimate_completion(self) -> str:
        """Estimate completion date"""
        pending_tasks = [t for t in self.tasks 
                        if t.status in [ReviewStatus.PENDING, ReviewStatus.ASSIGNED, ReviewStatus.IN_REVIEW]]
        
        if not pending_tasks:
            return "Ready now"
        
        # Find latest due date
        latest = None
        for task in pending_tasks:
            if task.due_date:
                task_due = datetime.fromisoformat(task.due_date)
                if latest is None or task_due > latest:
                    latest = task_due
        
        if latest:
            return latest.strftime("%Y-%m-%d")
        
        return "Unknown"
    
    # API methods for external integration
    def submit_review(self, task_id: str, reviewer: str, 
                     decision: str, notes: str) -> bool:
        """Submit review decision for a task"""
        for task in self.tasks:
            if task.task_id == task_id:
                task.reviewer_notes = notes
                task.completed_at = datetime.now().isoformat()
                
                if decision.lower() == "approve":
                    task.status = ReviewStatus.APPROVED
                    task.resolution = "Approved"
                elif decision.lower() == "reject":
                    task.status = ReviewStatus.REJECTED
                    task.resolution = "Rejected"
                elif decision.lower() == "escalate":
                    task.status = ReviewStatus.ESCALATED
                    task.resolution = "Escalated"
                
                return True
        
        return False
    
    def get_reviewer_workload(self, reviewer: str) -> Dict:
        """Get workload for a specific reviewer"""
        reviewer_tasks = [t for t in self.tasks if t.assigned_to == reviewer]
        
        return {
            "total_assigned": len(reviewer_tasks),
            "pending": len([t for t in reviewer_tasks if t.status == ReviewStatus.PENDING]),
            "in_review": len([t for t in reviewer_tasks if t.status == ReviewStatus.IN_REVIEW]),
            "overdue": len([t for t in reviewer_tasks if t.status == ReviewStatus.OVERDUE]),
            "completed": len([t for t in reviewer_tasks if t.status in [ReviewStatus.APPROVED, ReviewStatus.REJECTED]])
        }
    
    def escalate_overdue_tasks(self) -> List[ReviewTask]:
        """Escalate tasks past due date"""
        escalated = []
        now = datetime.now()
        
        for task in self.tasks:
            if task.due_date and task.status in [ReviewStatus.PENDING, ReviewStatus.ASSIGNED]:
                due = datetime.fromisoformat(task.due_date)
                if now > due:
                    task.status = ReviewStatus.OVERDUE
                    task.priority = ReviewPriority.CRITICAL
                    escalated.append(task)
        
        return escalated


# Demo
if __name__ == "__main__":
    # Sample validation results
    validation_results = {
        "statistical_validator": {
            "findings": [
                {
                    "type": "invalid_p_value",
                    "severity": "critical",
                    "explanation": "P-value outside valid range",
                    "claim": "p=1.5"
                },
                {
                    "type": "sample_size_mismatch",
                    "severity": "high",
                    "explanation": "Sample size differs between sections",
                    "claim": "n=599 vs n=600"
                }
            ]
        },
        "compliance_checker": {
            "findings": [
                {
                    "type": "missing_section",
                    "severity": "major",
                    "explanation": "Safety section missing required element",
                    "claim": "Deaths not reported"
                }
            ]
        },
        "hallucination_detector": {
            "findings": [
                {
                    "type": "fabricated_number",
                    "severity": "high",
                    "explanation": "Response rate not found in source data",
                    "claim": "145% response rate"
                }
            ]
        }
    }
    
    # Run coordinator
    coordinator = HumanCoordinator()
    result = coordinator.execute({
        "validation_results": validation_results,
        "section_name": "Results",
        "auto_approve_threshold": 90,
        "force_review": False
    })
    
    # Display results
    print("=" * 70)
    print("HUMAN COORDINATOR - AGENT 6")
    print("=" * 70)
    
    print(f"\n📋 Section: {result['section_name']}")
    print(f"\n📊 Workflow Status:")
    print(f"   Critical Pending: {result['workflow_status']['critical_pending']}")
    print(f"   High Pending: {result['workflow_status']['high_pending']}")
    print(f"   Completion: {result['workflow_status']['completion_percentage']:.0f}%")
    print(f"   Blocked: {'YES' if result['workflow_status']['blocked'] else 'NO'}")
    
    print(f"\n📈 Tasks Summary:")
    print(f"   Total: {result['total_tasks']}")
    print(f"   Pending: {result['pending']}")
    print(f"   In Review: {result['in_review']}")
    print(f"   Approved: {result['approved']}")
    print(f"   Rejected: {result['rejected']}")
    print(f"   Overdue: {result['overdue']}")
    
    print(f"\n✅ Ready for Submission: {'YES' if result['ready_for_submission'] else 'NO'}")
    print(f"📅 Estimated Completion: {result['estimated_completion']}")
    print(f"🚨 Requires Escalation: {'YES' if result['requires_escalation'] else 'NO'}")
    
    print("\n" + "=" * 70)
    print("NEW REVIEW TASKS CREATED:")
    print("=" * 70)
    
    for task in result['new_tasks']:
        priority_icon = {
            "critical": "🔴",
            "high": "🟠",
            "medium": "🟡",
            "low": "🔵"
        }.get(task['priority'], "⚪")
        
        print(f"\n{priority_icon} [{task['priority'].upper()}] {task['type']}")
        print(f"   Task ID: {task['task_id']}")
        print(f"   Assigned to: {task['assigned_to']}")
        print(f"   Due: {task['due_date'][:10] if task['due_date'] else 'TBD'}")
        print(f"   Description: {task['description'][:60]}...")
        
        if task['findings']:
            print(f"   Findings: {len(task['findings'])} issue(s)")
    
    print("\n" + "=" * 70)
    print("REVIEWER WORKLOADS:")
    print("=" * 70)
    
    for reviewer in set(coordinator.reviewer_roles.values()):
        workload = coordinator.get_reviewer_workload(reviewer)
        if workload['total_assigned'] > 0:
            print(f"\n👤 {reviewer}:")
            print(f"   Assigned: {workload['total_assigned']}")
            print(f"   Pending: {workload['pending']}")
            print(f"   Overdue: {workload['overdue']}")
    
    print("\n" + "=" * 70)
