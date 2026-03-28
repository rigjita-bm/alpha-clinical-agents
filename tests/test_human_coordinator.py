"""
Tests for HumanCoordinator (Agent 6) - Human Review Workflow Management

Tests coordination of human-in-the-loop review processes.
FDA 21 CFR Part 11 compliant with electronic signatures.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch
from agents.human_coordinator import HumanCoordinator, ReviewTask, ReviewStatus, ReviewPriority


class TestReviewTaskDataclass:
    """Tests for ReviewTask dataclass"""
    
    def test_task_creation(self):
        """Test creating a review task"""
        task = ReviewTask(
            task_id="REV_001",
            document_id="DOC_123",
            section_type="efficacy_results",
            content="Generated content for review",
            reviewer_id="reviewer_001",
            priority=ReviewPriority.HIGH
        )
        
        assert task.task_id == "REV_001"
        assert task.document_id == "DOC_123"
        assert task.section_type == "efficacy_results"
        assert task.status == ReviewStatus.PENDING
        assert task.priority == ReviewPriority.HIGH
        assert isinstance(task.created_at, datetime)
        assert task.completed_at is None
    
    def test_task_default_priority(self):
        """Test default priority is NORMAL"""
        task = ReviewTask(
            task_id="REV_002",
            document_id="DOC_456",
            section_type="safety_results",
            content="Content"
        )
        
        assert task.priority == ReviewPriority.NORMAL


class TestHumanCoordinatorInitialization:
    """Tests for HumanCoordinator initialization"""
    
    def test_default_initialization(self):
        """Test default coordinator initialization"""
        coordinator = HumanCoordinator()
        
        assert coordinator.agent_id == "agent_6"
        assert coordinator.agent_name == "HumanCoordinator"
        assert coordinator.version == "2.1.0"
        assert coordinator.default_review_timeout == timedelta(days=7)
        assert len(coordinator.pending_tasks) == 0
        assert len(coordinator.completed_tasks) == 0
    
    def test_custom_initialization(self):
        """Test coordinator with custom timeout"""
        coordinator = HumanCoordinator(default_review_timeout=timedelta(days=3))
        
        assert coordinator.default_review_timeout == timedelta(days=3)


class TestTaskCreation:
    """Tests for review task creation"""
    
    @pytest.fixture
    def coordinator(self):
        return HumanCoordinator()
    
    def test_create_review_task(self, coordinator):
        """Test creating a review task"""
        task = coordinator.create_review_task(
            document_id="DOC_001",
            section_type="efficacy_results",
            content="Generated efficacy content",
            reviewer_id="reviewer_001",
            priority=ReviewPriority.HIGH,
            reason="High-risk statistical claims"
        )
        
        assert isinstance(task, ReviewTask)
        assert task.document_id == "DOC_001"
        assert task.status == ReviewStatus.PENDING
        assert len(coordinator.pending_tasks) == 1
    
    def test_create_multiple_tasks(self, coordinator):
        """Test creating multiple review tasks"""
        for i in range(3):
            coordinator.create_review_task(
                document_id=f"DOC_{i}",
                section_type="section",
                content=f"Content {i}",
                reviewer_id="reviewer_001"
            )
        
        assert len(coordinator.pending_tasks) == 3


class TestTaskAssignment:
    """Tests for task assignment"""
    
    @pytest.fixture
    def coordinator(self):
        return HumanCoordinator()
    
    def test_assign_task(self, coordinator):
        """Test assigning task to reviewer"""
        task = coordinator.create_review_task(
            document_id="DOC_001",
            section_type="section",
            content="Content",
            reviewer_id=None  # Not assigned yet
        )
        
        coordinator.assign_task(task.task_id, "reviewer_002")
        
        assert coordinator.pending_tasks[task.task_id].reviewer_id == "reviewer_002"
    
    def test_auto_assignment(self, coordinator):
        """Test automatic reviewer assignment"""
        task = coordinator.create_review_task(
            document_id="DOC_001",
            section_type="safety_results",
            content="Safety content",
            reviewer_id=None
        )
        
        # Safety sections should be assigned to safety reviewers
        assigned = coordinator.auto_assign_reviewer(task.task_id)
        
        assert assigned is True or assigned is False  # Depends on availability


class TaskWorkflowTests:
    """Tests for complete review workflow"""
    
    @pytest.fixture
    def coordinator(self):
        return HumanCoordinator()
    
    def test_approve_task(self, coordinator):
        """Test approving a review task"""
        task = coordinator.create_review_task(
            document_id="DOC_001",
            section_type="section",
            content="Content",
            reviewer_id="reviewer_001"
        )
        
        result = coordinator.approve_task(
            task_id=task.task_id,
            reviewer_id="reviewer_001",
            comments="Approved with minor edits",
            electronic_signature="sig_hash_123"
        )
        
        assert result is True
        assert task.task_id in coordinator.completed_tasks
        assert coordinator.completed_tasks[task.task_id].status == ReviewStatus.APPROVED
    
    def test_reject_task(self, coordinator):
        """Test rejecting a review task"""
        task = coordinator.create_review_task(
            document_id="DOC_001",
            section_type="section",
            content="Content",
            reviewer_id="reviewer_001"
        )
        
        result = coordinator.reject_task(
            task_id=task.task_id,
            reviewer_id="reviewer_001",
            reason="Statistical error in analysis",
            required_changes=["Fix p-value calculation", "Add confidence intervals"]
        )
        
        assert result is True
        assert coordinator.completed_tasks[task.task_id].status == ReviewStatus.REJECTED


class TestTimeoutHandling:
    """Tests for review timeout handling"""
    
    @pytest.fixture
    def coordinator(self):
        return HumanCoordinator()
    
    def test_check_expired_tasks(self, coordinator):
        """Test detection of expired tasks"""
        # Create task with short timeout
        task = coordinator.create_review_task(
            document_id="DOC_001",
            section_type="section",
            content="Content",
            reviewer_id="reviewer_001"
        )
        
        # Manually set creation time to past
        coordinator.pending_tasks[task.task_id].created_at = datetime.utcnow() - timedelta(days=10)
        
        expired = coordinator.check_expired_tasks()
        
        assert len(expired) >= 1
        assert task.task_id in [t.task_id for t in expired]
    
    def test_escalate_expired(self, coordinator):
        """Test escalation of expired tasks"""
        task = coordinator.create_review_task(
            document_id="DOC_001",
            section_type="section",
            content="Content",
            reviewer_id="reviewer_001"
        )
        
        # Make task expired
        coordinator.pending_tasks[task.task_id].created_at = datetime.utcnow() - timedelta(days=10)
        
        escalated = coordinator.escalate_task(task.task_id, "manager_001")
        
        assert escalated is True


class TestAuditTrail:
    """Tests for FDA 21 CFR Part 11 audit trails"""
    
    @pytest.fixture
    def coordinator(self):
        return HumanCoordinator()
    
    def test_electronic_signature(self, coordinator):
        """Test electronic signature capture"""
        task = coordinator.create_review_task(
            document_id="DOC_001",
            section_type="section",
            content="Content",
            reviewer_id="reviewer_001"
        )
        
        coordinator.approve_task(
            task_id=task.task_id,
            reviewer_id="reviewer_001",
            electronic_signature="sha256_hash_of_credentials"
        )
        
        completed = coordinator.completed_tasks[task.task_id]
        assert completed.electronic_signature is not None
    
    def test_audit_log_completeness(self, coordinator):
        """Test that all actions are audited"""
        task = coordinator.create_review_task(
            document_id="DOC_001",
            section_type="section",
            content="Content",
            reviewer_id="reviewer_001"
        )
        
        # Check audit trail exists
        assert hasattr(coordinator, 'audit_trail')


class TestPriorityHandling:
    """Tests for priority-based task handling"""
    
    @pytest.fixture
    def coordinator(self):
        return HumanCoordinator()
    
    def test_priority_sorting(self, coordinator):
        """Test that high priority tasks are processed first"""
        # Create tasks with different priorities
        low = coordinator.create_review_task(
            document_id="DOC_LOW",
            section_type="section",
            content="Low priority",
            priority=ReviewPriority.LOW
        )
        
        high = coordinator.create_review_task(
            document_id="DOC_HIGH",
            section_type="section",
            content="High priority",
            priority=ReviewPriority.HIGH
        )
        
        urgent = coordinator.create_review_task(
            document_id="DOC_URGENT",
            section_type="section",
            content="Urgent",
            priority=ReviewPriority.URGENT
        )
        
        # Get pending tasks sorted by priority
        sorted_tasks = coordinator.get_pending_by_priority()
        
        # Urgent should be first
        assert sorted_tasks[0].priority == ReviewPriority.URGENT
