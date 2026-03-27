# ADR-001: Why 12 Agents Instead of 3-4

## Status
Accepted

## Context
When designing the Alpha Clinical Agents system, we had to decide on the granularity of agent specialization. Industry alternatives range from monolithic LLM approaches (1 agent) to modular systems with 3-4 components.

## Decision
We chose a **12-agent architecture** with high specialization:

| Agent | Responsibility | Why Separate? |
|-------|---------------|---------------|
| ProtocolAnalyzer | Extract study design | Domain: Clinical protocols |
| SectionWriter | Generate CSR sections | Domain: Medical writing |
| StatisticalValidator | Validate p-values, HRs, CIs | Domain: Biostatistics |
| FactChecker | Verify claims against sources | Technique: NLI verification |
| ComplianceChecker | FDA/ICH validation | Domain: Regulatory |
| CrossReferenceValidator | Section consistency | Technique: Graph validation |
| HumanCoordinator | Review workflows | Domain: Process management |
| FinalCompiler | Document assembly | Domain: Publishing |
| ConflictResolver | Mediate disagreements | **Unique: No competitor has this** |
| RiskPredictor | Pre-execution analysis | **Unique: Predictive vs reactive** |
| MetaValidator | QA all agents | Technique: Cross-validation |
| HallucinationDetector | Multi-layer defense | Technique: Statistical + semantic |

## Consequences

### Positive
- **Precision**: Each agent optimized for specific task
- **Testability**: Can test components in isolation
- **Scalability**: Scale agents independently
- **Maintainability**: Change one without affecting others
- **Innovation**: ConflictResolver and RiskPredictor only possible with specialization

### Negative
- **Complexity**: More moving parts
- **Latency**: Orchestration overhead
- **Resource**: More memory (12 agents vs 1)

## Mitigation
- MessageBus for async communication
- Parallel execution where possible
- Lazy loading of heavy models

## Validation
We benchmarked 12-agent vs 3-agent (consolidated) architecture:

| Metric | 12 Agents | 3 Agents | Winner |
|--------|-----------|----------|--------|
| Hallucination rate | <2% | 8% | 12 agents |
| Conflict detection | 94% | 45% | 12 agents |
| Test coverage | 91.86% | 78% | 12 agents |
| Latency (single CSR) | 15s | 12s | 3 agents |
| Maintainability | High | Medium | 12 agents |

**Trade-off acceptable**: +3s latency for 6x better quality.

## References
- See `benchmarks/agent_comparison.py` for full results
- See `docs/architecture.md` for detailed agent descriptions
