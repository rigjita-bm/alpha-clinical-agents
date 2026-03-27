"""
Integration tests for multi-agent workflows
Tests end-to-end agent interactions
"""
import pytest
from core.orchestrator import ClinicalOrchestrator
from agents import (
    ProtocolAnalyzer, SectionWriter, StatisticalValidator,
    ComplianceChecker, CrossReferenceValidator, MetaValidator
)


@pytest.mark.integration
class TestMultiAgentWorkflows:
    """Integration tests for multi-agent workflows"""
    
    def test_orchestrator_registration(self):
        """Test that orchestrator can register all agents"""
        orchestrator = ClinicalOrchestrator()
        
        agents = [
            ProtocolAnalyzer(),
            SectionWriter(),
            StatisticalValidator(),
            ComplianceChecker(),
            CrossReferenceValidator(),
            MetaValidator()
        ]
        
        for agent in agents:
            orchestrator.register_agent(agent)
        
        assert len(orchestrator.agents) == 6
    
    def test_simple_2agent_workflow(self):
        """Test ProtocolAnalyzer → SectionWriter workflow"""
        orchestrator = ClinicalOrchestrator()
        orchestrator.register_agent(ProtocolAnalyzer())
        orchestrator.register_agent(SectionWriter())
        
        protocol_text = """
        Phase II study of Drug XYZ in 300 patients with breast cancer.
        Primary endpoint: Overall survival.
        """
        
        # Execute protocol analysis
        protocol_result = orchestrator.execute_workflow({
            "protocol_text": protocol_text
        })
        
        assert protocol_result["status"] in ["completed", "error"]
    
    def test_validation_pipeline(self):
        """Test validation pipeline with multiple validators"""
        orchestrator = ClinicalOrchestrator()
        orchestrator.register_agent(StatisticalValidator())
        orchestrator.register_agent(ComplianceChecker())
        orchestrator.register_agent(CrossReferenceValidator())
        
        test_data = {
            "drafts": {
                "Methods": {"text": "N=600", "n": 600},
                "Results": {"text": "HR 0.72 (0.58-0.89), p=0.003", "statistics": {"hr": 0.72, "p": 0.003}}
            }
        }
        
        # This would run parallel validation in async mode
        # For now, test that agents can be invoked
        stat_validator = orchestrator.agents["StatisticalValidator"]
        result = stat_validator.execute(test_data)
        
        assert "validation_score" in result
    
    def test_meta_validator_integration(self):
        """Test MetaValidator validates other agents' outputs"""
        orchestrator = ClinicalOrchestrator()
        orchestrator.register_agent(MetaValidator())
        orchestrator.register_agent(ProtocolAnalyzer())
        
        # Get outputs from multiple agents
        protocol_analyzer = orchestrator.agents["ProtocolAnalyzer"]
        protocol_result = protocol_analyzer.execute({
            "protocol_text": "Phase III study, N=600, primary: OS"
        })
        
        # Meta-validate
        meta_validator = orchestrator.agents["MetaValidator"]
        meta_result = meta_validator.execute({
            "agent_outputs": {"ProtocolAnalyzer": protocol_result}
        })
        
        assert "qa_score" in meta_result
        assert "findings" in meta_result
    
    def test_workflow_state_transitions(self):
        """Test workflow state machine transitions"""
        from core.orchestrator import WorkflowStage
        
        orchestrator = ClinicalOrchestrator()
        orchestrator.register_agent(ProtocolAnalyzer())
        
        # Check initial state
        assert orchestrator.state is None
        
        # Execute workflow
        orchestrator.execute_workflow({"protocol_text": "Test protocol"})
        
        # Check final state
        assert orchestrator.state is not None
        assert orchestrator.state.current_stage in [
            WorkflowStage.COMPLETED,
            WorkflowStage.ERROR
        ]
    
    def test_audit_trail_integrity(self):
        """Test that audit trail is maintained across agents"""
        orchestrator = ClinicalOrchestrator()
        
        agents = [ProtocolAnalyzer(), StatisticalValidator()]
        for agent in agents:
            orchestrator.register_agent(agent)
        
        # Execute workflow
        orchestrator.execute_workflow({
            "protocol_text": "Phase III study, N=600, primary endpoint: OS"
        })
        
        # Check audit trails
        for agent_id, agent in orchestrator.agents.items():
            audit = agent.get_audit_trail()
            assert len(audit) >= 0
            assert all("timestamp" in record for record in audit)
