"""
Unit tests for ConflictResolver Agent
Tests conflict detection and resolution strategies
"""
import pytest
from agents.conflict_resolver import ConflictResolver, ConflictType, ResolutionStrategy


class TestConflictResolver:
    """Test suite for ConflictResolver (Agent 8)"""
    
    def test_instantiation(self, conflict_resolver):
        """Test agent can be instantiated"""
        assert conflict_resolver.agent_id == "ConflictResolver"
        assert conflict_resolver.version == "1.0.0"
    
    def test_detect_numerical_conflict(self, conflict_resolver):
        """Test detection of numerical disagreements"""
        agent_opinions = [
            {"agent": "StatisticalValidator", "value": 600, "confidence": 0.95},
            {"agent": "SectionWriter", "value": 599, "confidence": 0.85}
        ]
        
        result = conflict_resolver._detect_conflict(
            topic="sample_size",
            opinions=agent_opinions
        )
        
        assert result is not None
        assert result["type"] == ConflictType.NUMERICAL_DISAGREEMENT.value
    
    def test_source_hierarchy_resolution(self, conflict_resolver):
        """Test resolution using source hierarchy"""
        conflict = {
            "type": ConflictType.NUMERICAL_DISAGREEMENT.value,
            "opinions": [
                {"agent": "ProtocolAnalyzer", "value": "Phase III", "source": "protocol", "confidence": 0.99},
                {"agent": "SectionWriter", "value": "Phase II", "source": "agent_inference", "confidence": 0.75}
            ]
        }
        
        result = conflict_resolver._resolve_by_hierarchy(conflict)
        
        assert result["resolved"] == True
        assert result["winning_value"] == "Phase III"  # Protocol source wins
    
    def test_confidence_weighted_resolution(self, conflict_resolver):
        """Test resolution using confidence weighting"""
        conflict = {
            "type": ConflictType.NUMERICAL_DISAGREEMENT.value,
            "opinions": [
                {"agent": "Agent1", "value": 100, "confidence": 0.95},
                {"agent": "Agent2", "value": 102, "confidence": 0.60},
                {"agent": "Agent3", "value": 99, "confidence": 0.80}
            ]
        }
        
        result = conflict_resolver._resolve_by_confidence(conflict)
        
        assert result["resolved"] == True
        assert result["winning_value"] == 100  # Highest confidence wins
    
    def test_statistical_consensus_resolution(self, conflict_resolver):
        """Test resolution using statistical consensus"""
        conflict = {
            "type": ConflictType.METHODOLOGY_DISAGREEMENT.value,
            "opinions": [
                {"agent": "Agent1", "value": "log-rank", "confidence": 0.9},
                {"agent": "Agent2", "value": "log-rank", "confidence": 0.85},
                {"agent": "Agent3", "value": "Cox regression", "confidence": 0.70}
            ]
        }
        
        result = conflict_resolver._resolve_by_consensus(conflict)
        
        assert result["resolved"] == True
        assert result["winning_value"] == "log-rank"  # Majority wins
    
    def test_human_escalation_for_critical(self, conflict_resolver):
        """Test escalation to human for critical conflicts"""
        conflict = {
            "type": ConflictType.METHODOLOGY_DISAGREEMENT.value,
            "severity": "critical",
            "opinions": [
                {"agent": "Agent1", "value": "Approach A", "confidence": 0.8},
                {"agent": "Agent2", "value": "Approach B", "confidence": 0.8}
            ]
        }
        
        result = conflict_resolver._resolve_conflict(conflict)
        
        assert result["requires_human_approval"] == True
    
    def test_full_resolution_workflow(self, conflict_resolver):
        """Test complete conflict resolution workflow"""
        input_data = {
            "conflict": {
                "type": "numerical_disagreement",
                "topic": "sample_size",
                "opinions": [
                    {"agent": "ProtocolAnalyzer", "value": 600, "source": "protocol", "confidence": 0.99},
                    {"agent": "StatisticalValidator", "value": 599, "source": "statistical_output", "confidence": 0.95}
                ]
            }
        }
        
        result = conflict_resolver.execute(input_data)
        
        assert "resolved" in result
        assert "resolution_strategy" in result
        assert result["resolved"] == True
    
    def test_audit_trail(self, conflict_resolver):
        """Test audit trail for conflict resolutions"""
        input_data = {
            "conflict": {
                "type": "numerical_disagreement",
                "topic": "test",
                "opinions": [
                    {"agent": "Agent1", "value": 100, "source": "protocol", "confidence": 0.9}
                ]
            }
        }
        
        conflict_resolver.execute(input_data)
        audit = conflict_resolver.get_audit_trail()
        
        assert len(audit) > 0
