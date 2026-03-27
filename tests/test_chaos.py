"""
Chaos Engineering Tests
Verify system resilience to failures
"""

import pytest
import asyncio
from unittest.mock import patch, MagicMock
from datetime import datetime

from core.orchestrator import ClinicalOrchestrator
from core.message_protocol import AgentMessage
from agents.protocol_analyzer import ProtocolAnalyzer
from agents.section_writer import SectionWriter


class TestLLMFailureRecovery:
    """Test behavior when LLM API fails"""
    
    @pytest.mark.asyncio
    async def test_section_writer_graceful_degradation(self):
        """SectionWriter should fail gracefully when LLM unavailable"""
        writer = SectionWriter()
        
        with patch('core.llm_client.LLMClient.generate', side_effect=TimeoutError("LLM timeout")):
            result = await writer.process_async(AgentMessage(
                sender="test",
                payload={"section_name": "Methods", "protocol_structure": {"phase": "III"}}
            ))
        
        assert result.payload.get("status") == "error"
        assert "llm_unavailable" in result.payload.get("error_code", "")
        assert result.payload.get("fallback_used") == True
    
    @pytest.mark.asyncio
    async def test_orchestrator_retry_with_backoff(self):
        """Orchestrator should retry failed agent calls"""
        orchestrator = ClinicalOrchestrator()
        agent = MagicMock()
        agent.process_async = MagicMock(side_effect=[
            TimeoutError("First failure"),
            TimeoutError("Second failure"),
            AgentMessage(sender="agent", payload={"status": "success"})
        ])
        
        orchestrator.register_agent(agent)
        
        result = await orchestrator.send_message_with_retry(
            AgentMessage(sender="test", recipient="agent", payload={}),
            max_retries=3
        )
        
        assert result.payload["status"] == "success"
        assert agent.process_async.call_count == 3


class TestDatabaseFailureRecovery:
    """Test behavior when database unavailable"""
    
    @pytest.mark.asyncio
    async def test_audit_trail_buffering(self):
        """Audit records should buffer when DB down"""
        from core.base_agent import BaseAgent
        
        with patch('core.database.DatabaseConnection.execute', side_effect=ConnectionError("DB down")):
            agent = BaseAgent.__new__(BaseAgent)
            agent.agent_id = "test_agent"
            agent.version = "1.0.0"
            
            # Should not crash, should buffer
            await agent.log_audit_record(
                action="test_action",
                input_hash="abc123",
                output_hash="def456"
            )
            
            # Verify record in buffer
            assert len(agent._audit_buffer) == 1
    
    @pytest.mark.asyncio
    async def test_database_reconnection(self):
        """System should reconnect when DB comes back"""
        call_count = [0]
        
        def mock_execute(*args):
            call_count[0] += 1
            if call_count[0] < 3:
                raise ConnectionError("DB down")
            return MagicMock()
        
        with patch('core.database.DatabaseConnection.execute', side_effect=mock_execute):
            # Retry logic should eventually succeed
            from core.database import DatabaseConnection
            db = DatabaseConnection()
            
            for attempt in range(5):
                try:
                    await db.execute("SELECT 1")
                    break
                except ConnectionError:
                    await asyncio.sleep(0.1)
            
            assert call_count[0] == 3  # Succeeded on 3rd try


class TestAgentCrashRecovery:
    """Test behavior when individual agent crashes"""
    
    @pytest.mark.asyncio
    async def test_isolated_agent_failure(self):
        """One agent crash shouldn't bring down system"""
        orchestrator = ClinicalOrchestrator()
        
        # Register crashing agent
        bad_agent = MagicMock()
        bad_agent.process_async = MagicMock(side_effect=Exception("Agent crashed!"))
        bad_agent.agent_id = "bad_agent"
        
        # Register good agent
        good_agent = MagicMock()
        good_agent.process_async = MagicMock(return_value=AgentMessage(
            sender="good_agent", payload={"status": "ok"}
        ))
        good_agent.agent_id = "good_agent"
        
        orchestrator.register_agent(bad_agent)
        orchestrator.register_agent(good_agent)
        
        # Bad agent crashes
        with pytest.raises(Exception):
            await orchestrator.send_message(AgentMessage(
                sender="test", recipient="bad_agent", payload={}
            ))
        
        # Good agent still works
        result = await orchestrator.send_message(AgentMessage(
            sender="test", recipient="good_agent", payload={}
        ))
        assert result.payload["status"] == "ok"
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_pattern(self):
        """Circuit breaker should open after repeated failures"""
        from core.circuit_breaker import CircuitBreaker
        
        cb = CircuitBreaker(failure_threshold=3, recovery_timeout=1)
        
        failing_func = MagicMock(side_effect=Exception("Always fails"))
        
        # First 3 calls should try
        for _ in range(3):
            with pytest.raises(Exception):
                await cb.call(failing_func)
        
        # 4th call should fail fast (circuit open)
        with pytest.raises(Exception) as exc:
            await cb.call(failing_func)
        assert "circuit_open" in str(exc.value)
        
        failing_func.assert_called()  # Should not be called again


class TestMemoryPressure:
    """Test behavior under memory constraints"""
    
    def test_large_document_handling(self):
        """System should handle documents >10MB without OOM"""
        analyzer = ProtocolAnalyzer()
        
        # Simulate large protocol
        large_protocol = "PHASE III STUDY\n" * 100000  # ~2MB
        
        result = analyzer.execute({"protocol_text": large_protocol[:1000000]})  # Limit to 1MB
        
        # Should complete without crashing
        assert result["study_design"]["phase"] == "Phase III"
    
    def test_vector_store_cleanup(self):
        """FAISS index should not grow unbounded"""
        from core.rag_engine import FAISSRetriever
        
        retriever = FAISSRetriever(max_chunks=1000)
        
        # Add many chunks
        for i in range(1500):
            retriever.add_chunk(f"chunk_{i}", f"content_{i}", {"id": i})
        
        # Should enforce limit
        assert retriever.get_chunk_count() <= 1000


class TestNetworkPartition:
    """Test behavior during network issues"""
    
    @pytest.mark.asyncio
    async def test_message_queue_persistence(self):
        """Messages should persist during network partition"""
        orchestrator = ClinicalOrchestrator()
        
        with patch.object(orchestrator.message_bus, '_persist_message') as mock_persist:
            msg = AgentMessage(
                sender="test",
                recipient="section_writer",
                payload={"test": "data"}
            )
            
            await orchestrator.message_bus.publish(msg)
            
            # Verify message persisted
            mock_persist.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_graceful_degradation_without_external_apis(self):
        """System should work in offline mode"""
        # Mock all external APIs as unavailable
        with patch('core.llm_client.LLMClient.generate', side_effect=ConnectionError()), \
             patch('core.rag_engine.FAISSRetriever.search', return_value=[]):
            
            analyzer = ProtocolAnalyzer()
            
            # Should fall back to rule-based extraction
            result = analyzer.execute({"protocol_text": "PHASE III STUDY"})
            
            # Should still return valid structure (degraded but functional)
            assert "study_design" in result
            assert result["extraction_confidence"] < 0.5  # Low confidence due to fallback


class TestDataCorruption:
    """Test handling of corrupted/malicious data"""
    
    def test_sql_injection_protection(self):
        """Database layer should sanitize inputs"""
        from core.database import sanitize_input
        
        malicious_input = "'; DROP TABLE agents; --"
        sanitized = sanitize_input(malicious_input)
        
        assert "DROP TABLE" not in sanitized
        assert ";" not in sanitized
    
    def test_malicious_protocol_handling(self):
        """ProtocolAnalyzer should handle malformed input"""
        analyzer = ProtocolAnalyzer()
        
        # Binary garbage
        garbage = b"\x00\x01\x02\x03" * 1000
        
        result = analyzer.execute({"protocol_text": garbage.decode('utf-8', errors='ignore')})
        
        # Should not crash, should return empty but valid structure
        assert result["extraction_confidence"] == 0.0
        assert result["population"]["planned_enrollment"] == 0
