# Tests

This directory contains test suites for the Alpha Clinical Agents system.

## Structure (Planned)

```
tests/
├── __init__.py
├── conftest.py                 # Pytest configuration
├── test_base_agent.py          # Base agent tests
├── test_agents/                # Individual agent tests
│   ├── test_protocol_analyzer.py
│   ├── test_section_writer.py
│   ├── test_statistical_validator.py
│   ├── test_compliance_checker.py
│   └── ...
├── test_integration/           # Integration tests
│   ├── test_2agent_workflow.py
│   ├── test_3agent_workflow.py
│   └── test_12agent_workflow.py
├── test_compliance/            # FDA compliance tests
│   └── test_21cfr11.py
└── fixtures/                   # Test data
    ├── sample_protocol.txt
    └── sample_csr.json
```

## Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=agents --cov=core

# Run specific test
pytest tests/test_agents/test_protocol_analyzer.py

# Run integration tests only
pytest tests/test_integration/
```

## Status

⚠️ **IN PROGRESS** - Test suite under development

Priority tests:
1. BaseAgent FDA compliance
2. ProtocolAnalyzer extraction accuracy
3. StatisticalValidator p-value detection
4. HallucinationDetector false positive rate
5. 12-agent end-to-end workflow
