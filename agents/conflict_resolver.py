"""
Conflict Resolver - Agent 8
Mediates disagreements between agents and resolves conflicting outputs
"""

from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
from collections import defaultdict

from core.base_agent import BaseAgent


class ConflictType(Enum):
    NUMERICAL_DISAGREEMENT = "numerical_disagreement"
    METHODOLOGY_DISAGREEMENT = "methodology_disagreement"
    INTERPRETATION_DISAGREEMENT = "interpretation_disagreement"
    TERMINOLOGY_DISAGREEMENT = "terminology_disagreement"
    PRIORITY_DISAGREEMENT = "priority_disagreement"


class ResolutionStrategy(Enum):
    HIGHER_AUTHORITY = "higher_authority"
    STATISTICAL_CONSENSUS = "statistical_consensus"
    SOURCE_HIERARCHY = "source_hierarchy"
    HUMAN_ARBITRATION = "human_arbitration"
    CONFIDENCE_WEIGHTED = "confidence_weighted"


class ConflictSeverity(Enum):
    CRITICAL = "critical"  # Blocks submission
    HIGH = "high"  # Must resolve
    MEDIUM = "medium"  # Should resolve
    LOW = "low"  # Minor inconsistency


@dataclass
class AgentOpinion:
    """Opinion from a single agent"""
    agent_id: str
    agent_type: str
    value: Any
    confidence: float
    reasoning: str
    source: str  # e.g., "protocol", "statistical_output", "regulation"


@dataclass
class Conflict:
    """A conflict between agents"""
    conflict_id: str
    conflict_type: ConflictType
    severity: ConflictSeverity
    topic: str
    opinions: List[AgentOpinion]
    affected_sections: List[str]
    description: str


@dataclass
class Resolution:
    """Resolution for a conflict"""
    conflict_id: str
    resolution_strategy: ResolutionStrategy
    winning_agent: Optional[str]
    resolved_value: Any
    explanation: str
    confidence: float
    requires_human_approval: bool


class ConflictResolver(BaseAgent):
    """
    Agent 8: Conflict Resolver
    
    Mediates disagreements between agents:
    - Numerical disagreements (n=600 vs n=599)
    - Methodology conflicts (log-rank vs Cox regression)
    - Interpretation differences (significant vs not significant)
    - Terminology inconsistencies
    - Priority conflicts (safety vs efficacy focus)
    
    Resolution strategies:
    1. Higher authority (Protocol > Statistical output > Agent opinion)
    2. Statistical consensus (majority of statistical evidence)
    3. Source hierarchy (FDA > ICH > Sponsor SOP)
    4. Confidence weighted (highest confidence wins)
    5. Human arbitration (escalate to human)
    
    Output: Conflict resolution report with decisions
    """
    
    def __init__(self, config: Optional[Dict] = None):
        super().__init__(
            agent_id="ConflictResolver",
            version="1.0.0",
            config=config
        )
        
        # Source hierarchy for resolution
        self.source_hierarchy = [
            "protocol",
            "fda_regulation",
            "ich_guideline",
            "statistical_output",
            "previous_csr",
            "regulatory_guidance",
            "agent_consensus"
        ]
        
        # Agent authority hierarchy
        self.agent_hierarchy = [
            "MetaValidator",
            "StatisticalValidator",
            "ComplianceChecker",
            "ProtocolAnalyzer",
            "SectionWriter"
        ]
    
    def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Main conflict resolution logic
        
        Args:
            input_data: {
                "agent_outputs": Dict[str, Any],
                "validation_results": Dict[str, Any],
                "conflict_threshold": float  # Confidence threshold for auto-resolution
            }
        """
        agent_outputs = input_data.get("agent_outputs", {})
        validation_results = input_data.get("validation_results", {})
        conflict_threshold = input_data.get("conflict_threshold", 0.85)
        
        # Step 1: Detect conflicts
        conflicts = self._detect_conflicts(agent_outputs, validation_results)
        
        # Step 2: Resolve each conflict
        resolutions = []
        for conflict in conflicts:
            resolution = self._resolve_conflict(conflict, conflict_threshold)
            resolutions.append(resolution)
        
        # Step 3: Calculate resolution metrics
        auto_resolved = len([r for r in resolutions if not r.requires_human_approval])
        human_required = len([r for r in resolutions if r.requires_human_approval])
        
        # Step 4: Generate unified output
        unified_output = self._generate_unified_output(agent_outputs, resolutions)
        
        return {
            "total_conflicts": len(conflicts),
            "auto_resolved": auto_resolved,
            "human_required": human_required,
            "conflicts": [self._conflict_to_dict(c) for c in conflicts],
            "resolutions": [self._resolution_to_dict(r) for r in resolutions],
            "unified_output": unified_output,
            "resolution_rate": auto_resolved / max(len(conflicts), 1) * 100,
            "system_stable": len([c for c in conflicts if c.severity == ConflictSeverity.CRITICAL]) == 0
        }
    
    def _detect_conflicts(self, agent_outputs: Dict[str, Any],
                         validation_results: Dict[str, Any]) -> List[Conflict]:
        """Detect conflicts between agent outputs"""
        conflicts = []
        
        # Check for numerical disagreements
        numerical_conflicts = self._detect_numerical_conflicts(agent_outputs)
        conflicts.extend(numerical_conflicts)
        
        # Check for interpretation disagreements
        interpretation_conflicts = self._detect_interpretation_conflicts(agent_outputs)
        conflicts.extend(interpretation_conflicts)
        
        # Check for methodology disagreements
        methodology_conflicts = self._detect_methodology_conflicts(agent_outputs)
        conflicts.extend(methodology_conflicts)
        
        # Check for terminology inconsistencies
        terminology_conflicts = self._detect_terminology_conflicts(agent_outputs)
        conflicts.extend(terminology_conflicts)
        
        return conflicts
    
    def _detect_numerical_conflicts(self, agent_outputs: Dict[str, Any]) -> List[Conflict]:
        """Detect numerical disagreements between agents"""
        conflicts = []
        
        # Collect sample sizes from different agents
        sample_sizes = []
        
        if "ProtocolAnalyzer" in agent_outputs:
            n = agent_outputs["ProtocolAnalyzer"].get("planned_enrollment")
            if n:
                sample_sizes.append(AgentOpinion(
                    agent_id="ProtocolAnalyzer",
                    agent_type="extraction",
                    value=n,
                    confidence=0.95,
                    reasoning="Extracted from protocol",
                    source="protocol"
                ))
        
        if "SectionWriter" in agent_outputs:
            sections = agent_outputs["SectionWriter"].get("sections", {})
            for name, section in sections.items():
                content = section.get("content", "")
                import re
                match = re.search(r'(\d+)\s+patients', content)
                if match:
                    sample_sizes.append(AgentOpinion(
                        agent_id=f"SectionWriter_{name}",
                        agent_type="generation",
                        value=int(match.group(1)),
                        confidence=section.get("confidence", 0.9),
                        reasoning=f"Generated in {name} section",
                        source="agent_generation"
                    ))
        
        # Check for conflicts
        if len(sample_sizes) >= 2:
            values = [op.value for op in sample_sizes]
            if len(set(values)) > 1:
                conflicts.append(Conflict(
                    conflict_id="sample_size_disagreement",
                    conflict_type=ConflictType.NUMERICAL_DISAGREEMENT,
                    severity=ConflictSeverity.HIGH,
                    topic="Sample Size",
                    opinions=sample_sizes,
                    affected_sections=["Methods", "Results"],
                    description=f"Sample size disagreement: {set(values)}"
                ))
        
        return conflicts
    
    def _detect_interpretation_conflicts(self, agent_outputs: Dict[str, Any]) -> List[Conflict]:
        """Detect interpretation disagreements"""
        conflicts = []
        
        # Check for significance interpretation
        significance_opinions = []
        
        if "StatisticalValidator" in agent_outputs:
            result = agent_outputs["StatisticalValidator"]
            if "significance_claim" in result:
                significance_opinions.append(AgentOpinion(
                    agent_id="StatisticalValidator",
                    agent_type="validation",
                    value=result.get("significance_claim"),
                    confidence=result.get("confidence", 0.9),
                    reasoning="Based on p-value threshold",
                    source="statistical_output"
                ))
        
        # Additional interpretations from other agents...
        
        return conflicts
    
    def _detect_methodology_conflicts(self, agent_outputs: Dict[str, Any]) -> List[Conflict]:
        """Detect methodology disagreements"""
        conflicts = []
        
        # Check for statistical method consistency
        methods = []
        
        if "ProtocolAnalyzer" in agent_outputs:
            protocol = agent_outputs["ProtocolAnalyzer"]
            stats = protocol.get("statistical_methods", {})
            if stats:
                methods.append(AgentOpinion(
                    agent_id="ProtocolAnalyzer",
                    agent_type="extraction",
                    value=stats.get("primary_analysis", ""),
                    confidence=0.95,
                    reasoning="From protocol Section 9",
                    source="protocol"
                ))
        
        return conflicts
    
    def _detect_terminology_conflicts(self, agent_outputs: Dict[str, Any]) -> List[Conflict]:
        """Detect terminology inconsistencies"""
        conflicts = []
        
        # Terminology variations that should be standardized
        terminology_checks = [
            ("adverse event", ["side effect", "AE"]),
            ("serious adverse event", ["SAE", "severe event"]),
            ("intent-to-treat", ["ITT", "intent to treat"])
        ]
        
        return conflicts
    
    def _resolve_conflict(self, conflict: Conflict, 
                         threshold: float) -> Resolution:
        """Resolve a single conflict"""
        
        # Strategy 1: Source hierarchy
        resolution = self._resolve_by_source_hierarchy(conflict)
        if resolution and resolution.confidence >= threshold:
            return resolution
        
        # Strategy 2: Confidence weighted
        resolution = self._resolve_by_confidence(conflict)
        if resolution and resolution.confidence >= threshold:
            return resolution
        
        # Strategy 3: Agent authority
        resolution = self._resolve_by_agent_authority(conflict)
        if resolution and resolution.confidence >= threshold:
            return resolution
        
        # Strategy 4: Human arbitration
        return self._escalate_to_human(conflict)
    
    def _resolve_by_source_hierarchy(self, conflict: Conflict) -> Optional[Resolution]:
        """Resolve using source hierarchy"""
        best_opinion = None
        best_rank = len(self.source_hierarchy)
        
        for opinion in conflict.opinions:
            try:
                rank = self.source_hierarchy.index(opinion.source)
                if rank < best_rank:
                    best_rank = rank
                    best_opinion = opinion
            except ValueError:
                continue
        
        if best_opinion:
            return Resolution(
                conflict_id=conflict.conflict_id,
                resolution_strategy=ResolutionStrategy.SOURCE_HIERARCHY,
                winning_agent=best_opinion.agent_id,
                resolved_value=best_opinion.value,
                explanation=f"Selected based on source hierarchy: {best_opinion.source}",
                confidence=best_opinion.confidence,
                requires_human_approval=False
            )
        
        return None
    
    def _resolve_by_confidence(self, conflict: Conflict) -> Optional[Resolution]:
        """Resolve by highest confidence"""
        best_opinion = max(conflict.opinions, key=lambda o: o.confidence)
        
        return Resolution(
            conflict_id=conflict.conflict_id,
            resolution_strategy=ResolutionStrategy.CONFIDENCE_WEIGHTED,
            winning_agent=best_opinion.agent_id,
            resolved_value=best_opinion.value,
            explanation=f"Selected based on highest confidence ({best_opinion.confidence:.0%})",
            confidence=best_opinion.confidence,
            requires_human_approval=best_opinion.confidence < 0.9
        )
    
    def _resolve_by_agent_authority(self, conflict: Conflict) -> Optional[Resolution]:
        """Resolve using agent authority hierarchy"""
        best_opinion = None
        best_rank = len(self.agent_hierarchy)
        
        for opinion in conflict.opinions:
            try:
                rank = self.agent_hierarchy.index(opinion.agent_id.split("_")[0])
                if rank < best_rank:
                    best_rank = rank
                    best_opinion = opinion
            except ValueError:
                continue
        
        if best_opinion:
            return Resolution(
                conflict_id=conflict.conflict_id,
                resolution_strategy=ResolutionStrategy.HIGHER_AUTHORITY,
                winning_agent=best_opinion.agent_id,
                resolved_value=best_opinion.value,
                explanation=f"Selected based on agent authority: {best_opinion.agent_id}",
                confidence=best_opinion.confidence * 0.95,
                requires_human_approval=False
            )
        
        return None
    
    def _escalate_to_human(self, conflict: Conflict) -> Resolution:
        """Escalate conflict to human arbitration"""
        # Default to most common value or first opinion
        values = [op.value for op in conflict.opinions]
        resolved = max(set(values), key=values.count)
        
        return Resolution(
            conflict_id=conflict.conflict_id,
            resolution_strategy=ResolutionStrategy.HUMAN_ARBITRATION,
            winning_agent=None,
            resolved_value=resolved,
            explanation=f"Conflict requires human review: {conflict.description}",
            confidence=0.5,
            requires_human_approval=True
        )
    
    def _generate_unified_output(self, agent_outputs: Dict[str, Any],
                                resolutions: List[Resolution]) -> Dict:
        """Generate unified output incorporating resolutions"""
        unified = {
            "resolved_values": {},
            "pending_human_review": [],
            "applied_resolutions": []
        }
        
        for resolution in resolutions:
            if resolution.requires_human_approval:
                unified["pending_human_review"].append({
                    "conflict_id": resolution.conflict_id,
                    "current_value": resolution.resolved_value,
                    "explanation": resolution.explanation
                })
            else:
                unified["resolved_values"][resolution.conflict_id] = {
                    "value": resolution.resolved_value,
                    "source": resolution.winning_agent,
                    "strategy": resolution.resolution_strategy.value
                }
                unified["applied_resolutions"].append({
                    "conflict": resolution.conflict_id,
                    "winner": resolution.winning_agent,
                    "strategy": resolution.resolution_strategy.value
                })
        
        return unified
    
    def _conflict_to_dict(self, conflict: Conflict) -> Dict:
        """Convert conflict to dictionary"""
        return {
            "id": conflict.conflict_id,
            "type": conflict.conflict_type.value,
            "severity": conflict.severity.value,
            "topic": conflict.topic,
            "description": conflict.description,
            "opinions": [
                {
                    "agent": op.agent_id,
                    "value": op.value,
                    "confidence": op.confidence,
                    "source": op.source
                }
                for op in conflict.opinions
            ]
        }
    
    def _resolution_to_dict(self, resolution: Resolution) -> Dict:
        """Convert resolution to dictionary"""
        return {
            "conflict_id": resolution.conflict_id,
            "strategy": resolution.resolution_strategy.value,
            "winner": resolution.winning_agent,
            "resolved_value": resolution.resolved_value,
            "confidence": resolution.confidence,
            "requires_human": resolution.requires_human_approval,
            "explanation": resolution.explanation
        }


# Demo
if __name__ == "__main__":
    # Sample agent outputs with conflicts
    agent_outputs = {
        "ProtocolAnalyzer": {
            "planned_enrollment": 600,
            "phase": "III",
            "statistical_methods": {
                "primary_analysis": "Stratified log-rank test"
            }
        },
        "SectionWriter": {
            "sections": {
                "Methods": {
                    "content": "Approximately 600 patients were planned for enrollment.",
                    "confidence": 0.95
                },
                "Results": {
                    "content": "A total of 599 patients were randomized to treatment.",
                    "confidence": 0.92
                }
            }
        },
        "StatisticalValidator": {
            "validation_score": 88,
            "sample_size_in_results": 599
        }
    }
    
    validation_results = {
        "CrossReferenceValidator": {
            "findings": [
                {
                    "type": "sample_size_mismatch",
                    "severity": "high"
                }
            ]
        }
    }
    
    # Run conflict resolver
    resolver = ConflictResolver()
    result = resolver.execute({
        "agent_outputs": agent_outputs,
        "validation_results": validation_results,
        "conflict_threshold": 0.85
    })
    
    # Display results
    print("=" * 70)
    print("CONFLICT RESOLVER - AGENT 8")
    print("=" * 70)
    
    print(f"\n📊 Conflict Summary:")
    print(f"   Total Conflicts: {result['total_conflicts']}")
    print(f"   Auto-Resolved: {result['auto_resolved']}")
    print(f"   Human Required: {result['human_required']}")
    print(f"   Resolution Rate: {result['resolution_rate']:.0f}%")
    print(f"   System Stable: {'YES' if result['system_stable'] else 'NO'}")
    
    if result['conflicts']:
        print("\n" + "=" * 70)
        print("DETECTED CONFLICTS:")
        print("=" * 70)
        
        for conflict in result['conflicts']:
            severity_icon = {
                "critical": "🔴",
                "high": "🟠",
                "medium": "🟡",
                "low": "🔵"
            }.get(conflict['severity'], "⚪")
            
            print(f"\n{severity_icon} [{conflict['severity'].upper()}] {conflict['topic']}")
            print(f"   Type: {conflict['type']}")
            print(f"   Description: {conflict['description']}")
            print(f"   Opinions:")
            for op in conflict['opinions']:
                print(f"      • {op['agent']}: {op['value']} (confidence: {op['confidence']:.0%})")
    
    if result['resolutions']:
        print("\n" + "=" * 70)
        print("RESOLUTIONS:")
        print("=" * 70)
        
        for resolution in result['resolutions']:
            print(f"\n📌 {resolution['conflict_id']}")
            print(f"   Strategy: {resolution['strategy']}")
            print(f"   Winner: {resolution['winner'] or 'HUMAN DECISION NEEDED'}")
            print(f"   Resolved Value: {resolution['resolved_value']}")
            print(f"   Confidence: {resolution['confidence']:.0%}")
            print(f"   Requires Human: {'YES' if resolution['requires_human'] else 'NO'}")
    
    if result['unified_output']['resolved_values']:
        print("\n" + "=" * 70)
        print("UNIFIED OUTPUT:")
        print("=" * 70)
        
        for key, value in result['unified_output']['resolved_values'].items():
            print(f"\n✓ {key}:")
            print(f"   Value: {value['value']}")
            print(f"   Source: {value['source']}")
            print(f"   Strategy: {value['strategy']}")
    
    if result['unified_output']['pending_human_review']:
        print("\n" + "=" * 70)
        print("PENDING HUMAN REVIEW:")
        print("=" * 70)
        
        for item in result['unified_output']['pending_human_review']:
            print(f"\n⚠️  {item['conflict_id']}")
            print(f"   Proposed Value: {item['current_value']}")
            print(f"   Reason: {item['explanation']}")
    
    print("\n" + "=" * 70)
