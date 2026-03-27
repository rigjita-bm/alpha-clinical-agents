"""
Risk Predictor - Agent 9
Pre-execution complexity analysis and risk forecasting
"""

from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import json

from core.base_agent import BaseAgent


class RiskCategory(Enum):
    STATISTICAL_COMPLEXITY = "statistical_complexity"
    REGULATORY_RISK = "regulatory_risk"
    TIMELINE_RISK = "timeline_risk"
    QUALITY_RISK = "quality_risk"
    RESOURCE_RISK = "resource_risk"
    INTEGRATION_RISK = "integration_risk"


class RiskLevel(Enum):
    CRITICAL = "critical"  # High probability of failure
    HIGH = "high"  # Likely to cause issues
    MEDIUM = "medium"  # Manageable with attention
    LOW = "low"  # Minor concern
    MINIMAL = "minimal"  # Negligible risk


class ComplexityDimension(Enum):
    STUDY_DESIGN = "study_design"
    POPULATION_HETEROGENEITY = "population_heterogeneity"
    ENDPOINT_COMPLEXITY = "endpoint_complexity"
    STATISTICAL_METHODS = "statistical_methods"
    SAFETY_PROFILE = "safety_profile"
    REGULATORY_NOVELTY = "regulatory_novelty"


@dataclass
class RiskFactor:
    """Individual risk factor"""
    category: RiskCategory
    level: RiskLevel
    description: str
    probability: float  # 0-1
    impact: float  # 0-1
    mitigation: str
    early_warning_signs: List[str]


@dataclass
class ComplexityScore:
    """Complexity score for a dimension"""
    dimension: ComplexityDimension
    score: float  # 0-10
    contributing_factors: List[str]
    benchmark: str  # "typical", "complex", "highly_complex"


class RiskPredictor(BaseAgent):
    """
    Agent 9: Risk Predictor
    
    Pre-execution analysis to forecast:
    - Document generation complexity
    - Statistical validation challenges
    - Regulatory review risks
    - Timeline estimation accuracy
    - Quality control requirements
    - Resource allocation needs
    
    Complexity Scoring (0-10 per dimension):
    - Study Design: Adaptive? Multi-arm? Complex randomization?
    - Population Heterogeneity: Stratification factors? Subgroups?
    - Endpoint Complexity: Composite? Multiple primary? Novel?
    - Statistical Methods: Bayesian? Interim analyses? Multiplicity?
    - Safety Profile: Known class risks? New safety signals?
    - Regulatory Novelty: New mechanism? Breakthrough designation?
    
    Output: Risk assessment report with mitigation strategies
    """
    
    def __init__(self, config: Optional[Dict] = None):
        super().__init__(
            agent_id="RiskPredictor",
            version="1.0.0",
            config=config
        )
        
        # Risk thresholds
        self.risk_thresholds = {
            "critical": 0.8,
            "high": 0.6,
            "medium": 0.4,
            "low": 0.2
        }
        
        # Complexity benchmarks
        self.benchmarks = {
            "typical": (0, 4),
            "moderate": (4, 6.5),
            "complex": (6.5, 8),
            "highly_complex": (8, 10)
        }
    
    def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Main risk prediction logic
        
        Args:
            input_data: {
                "protocol_data": Dict,
                "historical_data": Dict,  # Optional: similar studies
                "target_timeline_days": int,
                "available_resources": Dict
            }
        """
        protocol_data = input_data.get("protocol_data", {})
        historical_data = input_data.get("historical_data", {})
        target_timeline = input_data.get("target_timeline_days", 30)
        resources = input_data.get("available_resources", {})
        
        # Step 1: Calculate complexity scores
        complexity_scores = self._calculate_complexity(protocol_data)
        
        # Step 2: Identify risk factors
        risk_factors = self._identify_risk_factors(
            protocol_data, complexity_scores, historical_data
        )
        
        # Step 3: Estimate timeline
        timeline_estimate = self._estimate_timeline(
            complexity_scores, risk_factors, target_timeline
        )
        
        # Step 4: Assess resource requirements
        resource_assessment = self._assess_resources(
            complexity_scores, risk_factors, resources
        )
        
        # Step 5: Generate early warning indicators
        early_warnings = self._generate_early_warnings(risk_factors)
        
        # Step 6: Calculate overall risk score
        overall_risk = self._calculate_overall_risk(complexity_scores, risk_factors)
        
        # Step 7: Generate recommendations
        recommendations = self._generate_recommendations(
            risk_factors, timeline_estimate, resource_assessment
        )
        
        return {
            "overall_risk_level": overall_risk["level"].value,
            "overall_risk_score": overall_risk["score"],
            "complexity_analysis": {
                "dimensions": [self._score_to_dict(s) for s in complexity_scores],
                "overall_complexity": sum(s.score for s in complexity_scores) / len(complexity_scores) if complexity_scores else 0
            },
            "risk_factors": [self._risk_to_dict(r) for r in risk_factors],
            "critical_risks": len([r for r in risk_factors if r.level == RiskLevel.CRITICAL]),
            "high_risks": len([r for r in risk_factors if r.level == RiskLevel.HIGH]),
            "timeline_estimate": timeline_estimate,
            "resource_assessment": resource_assessment,
            "early_warning_indicators": early_warnings,
            "recommendations": recommendations,
            "success_probability": overall_risk["success_probability"],
            "proceed_recommendation": overall_risk["level"] not in [RiskLevel.CRITICAL]
        }
    
    def _calculate_complexity(self, protocol_data: Dict) -> List[ComplexityScore]:
        """Calculate complexity scores for each dimension"""
        scores = []
        
        # Study Design Complexity
        study_design = protocol_data.get("study_design", {})
        design_score = self._calculate_design_complexity(study_design)
        scores.append(design_score)
        
        # Population Heterogeneity
        population = protocol_data.get("population", {})
        population_score = self._calculate_population_complexity(population)
        scores.append(population_score)
        
        # Endpoint Complexity
        endpoints = protocol_data.get("endpoints", {})
        endpoint_score = self._calculate_endpoint_complexity(endpoints)
        scores.append(endpoint_score)
        
        # Statistical Methods Complexity
        stats = protocol_data.get("statistical_methods", {})
        stats_score = self._calculate_statistical_complexity(stats)
        scores.append(stats_score)
        
        # Safety Profile Complexity (placeholder)
        safety_score = ComplexityScore(
            dimension=ComplexityDimension.SAFETY_PROFILE,
            score=5.0,
            contributing_factors=["Standard safety monitoring"],
            benchmark="typical"
        )
        scores.append(safety_score)
        
        # Regulatory Novelty
        novelty_score = self._calculate_regulatory_complexity(protocol_data)
        scores.append(novelty_score)
        
        return scores
    
    def _calculate_design_complexity(self, study_design: Dict) -> ComplexityScore:
        """Calculate study design complexity (0-10)"""
        factors = []
        score = 5.0  # Base score
        
        # Adaptive design increases complexity
        if study_design.get("adaptive_design"):
            score += 2.0
            factors.append("Adaptive design with interim analyses")
        
        # Multi-arm increases complexity
        arms = study_design.get("treatment_arms", [])
        if len(arms) > 2:
            score += 1.5
            factors.append(f"Multi-arm design ({len(arms)} arms)")
        
        # Complex randomization
        randomization = study_design.get("randomization", {})
        if randomization.get("stratified"):
            score += 1.0
            factors.append("Stratified randomization")
        
        # Multi-center increases complexity
        if study_design.get("multi_center", True):
            score += 0.5
            factors.append("Multi-center study")
        
        score = min(score, 10.0)
        benchmark = self._get_benchmark(score)
        
        return ComplexityScore(
            dimension=ComplexityDimension.STUDY_DESIGN,
            score=round(score, 1),
            contributing_factors=factors or ["Standard randomized design"],
            benchmark=benchmark
        )
    
    def _calculate_population_complexity(self, population: Dict) -> ComplexityScore:
        """Calculate population heterogeneity complexity (0-10)"""
        factors = []
        score = 4.0  # Base score
        
        # Stratification factors
        stratification = population.get("stratification_factors", [])
        if len(stratification) > 2:
            score += 1.5
            factors.append(f"Multiple stratification factors ({len(stratification)})")
        
        # Subgroup analyses
        subgroups = population.get("planned_subgroups", [])
        if len(subgroups) > 3:
            score += 1.5
            factors.append(f"Multiple subgroup analyses ({len(subgroups)})")
        
        # Multiple countries/sites
        countries = population.get("countries", [])
        if len(countries) > 5:
            score += 1.0
            factors.append(f"Multi-regional study ({len(countries)} countries)")
        
        # Large sample size increases complexity
        n = population.get("planned_enrollment", 300)
        if n > 1000:
            score += 1.0
            factors.append(f"Large sample size ({n} patients)")
        
        score = min(score, 10.0)
        benchmark = self._get_benchmark(score)
        
        return ComplexityScore(
            dimension=ComplexityDimension.POPULATION_HETEROGENEITY,
            score=round(score, 1),
            contributing_factors=factors or ["Standard population"],
            benchmark=benchmark
        )
    
    def _calculate_endpoint_complexity(self, endpoints: Dict) -> ComplexityScore:
        """Calculate endpoint complexity (0-10)"""
        factors = []
        score = 4.0  # Base score
        
        # Multiple primary endpoints
        primary = endpoints.get("primary", [])
        if len(primary) > 1:
            score += 2.0
            factors.append(f"Co-primary endpoints ({len(primary)})")
        
        # Composite endpoints
        for endpoint in primary:
            if "composite" in endpoint.lower():
                score += 1.0
                factors.append("Composite primary endpoint")
                break
        
        # Secondary endpoints
        secondary = endpoints.get("secondary", [])
        if len(secondary) > 5:
            score += 1.0
            factors.append(f"Many secondary endpoints ({len(secondary)})")
        
        score = min(score, 10.0)
        benchmark = self._get_benchmark(score)
        
        return ComplexityScore(
            dimension=ComplexityDimension.ENDPOINT_COMPLEXITY,
            score=round(score, 1),
            contributing_factors=factors or ["Standard endpoints"],
            benchmark=benchmark
        )
    
    def _calculate_statistical_complexity(self, stats: Dict) -> ComplexityScore:
        """Calculate statistical methods complexity (0-10)"""
        factors = []
        score = 4.0  # Base score
        
        # Interim analyses
        if stats.get("interim_analyses"):
            score += 1.5
            factors.append("Planned interim analyses")
        
        # Multiplicity adjustment
        if stats.get("multiplicity_adjustment"):
            score += 1.0
            factors.append("Multiplicity adjustment required")
        
        # Non-inferiority/superiority
        if stats.get("test_type") in ["non-inferiority", "superiority"]:
            score += 0.5
            factors.append(f"{stats['test_type']} testing")
        
        # Complex methods
        primary = stats.get("primary_analysis", "").lower()
        if "cox" in primary or "bayesian" in primary:
            score += 1.0
            factors.append("Advanced statistical methods")
        
        score = min(score, 10.0)
        benchmark = self._get_benchmark(score)
        
        return ComplexityScore(
            dimension=ComplexityDimension.STATISTICAL_METHODS,
            score=round(score, 1),
            contributing_factors=factors or ["Standard statistical methods"],
            benchmark=benchmark
        )
    
    def _calculate_regulatory_complexity(self, protocol_data: Dict) -> ComplexityScore:
        """Calculate regulatory novelty complexity (0-10)"""
        factors = []
        score = 3.0  # Base score
        
        # Novel mechanism
        if protocol_data.get("novel_mechanism"):
            score += 2.0
            factors.append("Novel mechanism of action")
        
        # Breakthrough designation
        if protocol_data.get("breakthrough_designation"):
            score += 1.0
            factors.append("Breakthrough therapy designation")
        
        # Orphan drug
        if protocol_data.get("orphan_drug"):
            score += 0.5
            factors.append("Orphan drug indication")
        
        score = min(score, 10.0)
        benchmark = self._get_benchmark(score)
        
        return ComplexityScore(
            dimension=ComplexityDimension.REGULATORY_NOVELTY,
            score=round(score, 1),
            contributing_factors=factors or ["Standard regulatory pathway"],
            benchmark=benchmark
        )
    
    def _identify_risk_factors(self, protocol_data: Dict,
                              complexity_scores: List[ComplexityScore],
                              historical_data: Dict) -> List[RiskFactor]:
        """Identify specific risk factors"""
        risks = []
        
        # High complexity risks
        for score in complexity_scores:
            if score.score >= 7:
                risks.append(RiskFactor(
                    category=RiskCategory.STATISTICAL_COMPLEXITY,
                    level=RiskLevel.HIGH if score.score >= 8 else RiskLevel.MEDIUM,
                    description=f"High complexity in {score.dimension.value}",
                    probability=0.6,
                    impact=0.7,
                    mitigation=f"Allocate additional resources for {score.dimension.value}",
                    early_warning_signs=["Delays in analysis", "Multiple revisions needed"]
                ))
        
        # Timeline risks
        avg_complexity = sum(s.score for s in complexity_scores) / len(complexity_scores)
        if avg_complexity > 6:
            risks.append(RiskFactor(
                category=RiskCategory.TIMELINE_RISK,
                level=RiskLevel.HIGH,
                description="High complexity may delay document completion",
                probability=0.5,
                impact=0.8,
                mitigation="Build buffer time into schedule",
                early_warning_signs=["Slower than expected progress", "Repeated validation failures"]
            ))
        
        # Quality risks
        if any(s.score > 7 for s in complexity_scores):
            risks.append(RiskFactor(
                category=RiskCategory.QUALITY_RISK,
                level=RiskLevel.MEDIUM,
                description="Complex study design may lead to quality issues",
                probability=0.4,
                impact=0.6,
                mitigation="Enhanced QC procedures",
                early_warning_signs=["High error rates", "Inconsistent outputs"]
            ))
        
        return risks
    
    def _estimate_timeline(self, complexity_scores: List[ComplexityScore],
                          risk_factors: List[RiskFactor],
                          target_timeline: int) -> Dict:
        """Estimate realistic timeline"""
        # Base timeline by complexity
        avg_complexity = sum(s.score for s in complexity_scores) / len(complexity_scores)
        
        if avg_complexity < 4:
            base_days = 14
        elif avg_complexity < 6:
            base_days = 21
        elif avg_complexity < 8:
            base_days = 35
        else:
            base_days = 49
        
        # Add buffer for high risks
        high_risks = len([r for r in risk_factors if r.level in [RiskLevel.CRITICAL, RiskLevel.HIGH]])
        buffer_days = high_risks * 3
        
        estimated_days = base_days + buffer_days
        
        return {
            "estimated_days": estimated_days,
            "target_days": target_timeline,
            "feasible": estimated_days <= target_timeline,
            "variance_days": int(estimated_days * 0.2),  # 20% variance
            "complexity_factor": f"{avg_complexity:.1f}/10"
        }
    
    def _assess_resources(self, complexity_scores: List[ComplexityScore],
                         risk_factors: List[RiskFactor],
                         available: Dict) -> Dict:
        """Assess resource requirements"""
        avg_complexity = sum(s.score for s in complexity_scores) / len(complexity_scores)
        
        # Calculate required resources
        if avg_complexity < 4:
            required = {"medical_writers": 1, "statisticians": 0.5, "reviewers": 2}
        elif avg_complexity < 6:
            required = {"medical_writers": 2, "statisticians": 1, "reviewers": 3}
        elif avg_complexity < 8:
            required = {"medical_writers": 3, "statisticians": 1.5, "reviewers": 4}
        else:
            required = {"medical_writers": 4, "statisticians": 2, "reviewers": 5}
        
        # Check against available
        gaps = {}
        for role, req in required.items():
            avail = available.get(role, 0)
            if req > avail:
                gaps[role] = req - avail
        
        return {
            "required_resources": required,
            "gaps": gaps,
            "adequate": len(gaps) == 0
        }
    
    def _generate_early_warnings(self, risk_factors: List[RiskFactor]) -> List[Dict]:
        """Generate early warning indicators"""
        warnings = []
        
        for risk in risk_factors:
            for sign in risk.early_warning_signs:
                warnings.append({
                    "indicator": sign,
                    "risk_category": risk.category.value,
                    "risk_level": risk.level.value
                })
        
        return warnings
    
    def _calculate_overall_risk(self, complexity_scores: List[ComplexityScore],
                               risk_factors: List[RiskFactor]) -> Dict:
        """Calculate overall risk assessment"""
        avg_complexity = sum(s.score for s in complexity_scores) / len(complexity_scores)
        
        # Weight by severity
        severity_weights = {
            RiskLevel.CRITICAL: 1.0,
            RiskLevel.HIGH: 0.7,
            RiskLevel.MEDIUM: 0.4,
            RiskLevel.LOW: 0.2,
            RiskLevel.MINIMAL: 0.0
        }
        
        risk_score = sum(severity_weights.get(r.level, 0.3) for r in risk_factors)
        risk_score = min(risk_score, 10.0)
        
        # Determine level
        if risk_score >= 7:
            level = RiskLevel.CRITICAL
        elif risk_score >= 5:
            level = RiskLevel.HIGH
        elif risk_score >= 3:
            level = RiskLevel.MEDIUM
        elif risk_score >= 1:
            level = RiskLevel.LOW
        else:
            level = RiskLevel.MINIMAL
        
        # Success probability
        success_prob = max(0, 1 - (risk_score / 10))
        
        return {
            "score": round(risk_score, 1),
            "level": level,
            "success_probability": round(success_prob, 2)
        }
    
    def _generate_recommendations(self, risk_factors: List[RiskFactor],
                                 timeline: Dict,
                                 resources: Dict) -> List[str]:
        """Generate actionable recommendations"""
        recommendations = []
        
        # Timeline recommendations
        if not timeline["feasible"]:
            recommendations.append(f"Consider extending timeline to {timeline['estimated_days']} days")
        
        # Resource recommendations
        if resources["gaps"]:
            for role, gap in resources["gaps"].items():
                recommendations.append(f"Add {gap} {role} to resource plan")
        
        # Risk-specific recommendations
        for risk in risk_factors:
            if risk.level in [RiskLevel.CRITICAL, RiskLevel.HIGH]:
                recommendations.append(risk.mitigation)
        
        return recommendations
    
    def _get_benchmark(self, score: float) -> str:
        """Get benchmark category for score"""
        for benchmark, (low, high) in self.benchmarks.items():
            if low <= score <= high:
                return benchmark
        return "highly_complex"
    
    def _score_to_dict(self, score: ComplexityScore) -> Dict:
        """Convert complexity score to dict"""
        return {
            "dimension": score.dimension.value,
            "score": score.score,
            "factors": score.contributing_factors,
            "benchmark": score.benchmark
        }
    
    def _risk_to_dict(self, risk: RiskFactor) -> Dict:
        """Convert risk factor to dict"""
        return {
            "category": risk.category.value,
            "level": risk.level.value,
            "description": risk.description,
            "probability": risk.probability,
            "impact": risk.impact,
            "mitigation": risk.mitigation
        }


# Demo
if __name__ == "__main__":
    # Sample complex protocol
    protocol_data = {
        "study_design": {
            "phase": "III",
            "adaptive_design": True,
            "treatment_arms": ["Drug A", "Drug B", "Placebo"],
            "randomization": {"stratified": True, "factors": ["region", "ECOG"]},
            "multi_center": True
        },
        "population": {
            "planned_enrollment": 1200,
            "stratification_factors": ["region", "ECOG", "prior_therapy"],
            "planned_subgroups": ["age", "sex", "region", "biomarker"],
            "countries": ["US", "EU", "Japan", "China", "Brazil"]
        },
        "endpoints": {
            "primary": ["Overall Survival", "Progression-Free Survival"],
            "secondary": ["ORR", "DOR", "TTR", "Quality of Life", "Biomarker"]
        },
        "statistical_methods": {
            "primary_analysis": "Stratified log-rank test",
            "interim_analyses": True,
            "multiplicity_adjustment": True,
            "test_type": "superiority"
        },
        "novel_mechanism": True,
        "breakthrough_designation": True
    }
    
    available_resources = {
        "medical_writers": 2,
        "statisticians": 1,
        "reviewers": 3
    }
    
    # Run risk prediction
    predictor = RiskPredictor()
    result = predictor.execute({
        "protocol_data": protocol_data,
        "target_timeline_days": 30,
        "available_resources": available_resources
    })
    
    # Display results
    print("=" * 70)
    print("RISK PREDICTOR - AGENT 9")
    print("=" * 70)
    
    print(f"\n📊 Overall Risk Assessment:")
    print(f"   Risk Level: {result['overall_risk_level'].upper()}")
    print(f"   Risk Score: {result['overall_risk_score']}/10")
    print(f"   Success Probability: {result['success_probability']:.0%}")
    print(f"   Proceed Recommendation: {'YES ✓' if result['proceed_recommendation'] else 'NO ⚠️'}")
    
    print(f"\n📈 Complexity Analysis:")
    print(f"   Overall Complexity: {result['complexity_analysis']['overall_complexity']:.1f}/10")
    print(f"\n   Dimensions:")
    for dim in result['complexity_analysis']['dimensions']:
        bar = "█" * int(dim['score']) + "░" * (10 - int(dim['score']))
        print(f"      {dim['dimension']:<30s} {bar} {dim['score']}/10 ({dim['benchmark']})")
    
    print(f"\n⚠️  Risk Factors:")
    print(f"   Critical: {result['critical_risks']}")
    print(f"   High: {result['high_risks']}")
    
    if result['risk_factors']:
        print("\n   Details:")
        for risk in result['risk_factors']:
            icon = {"critical": "🔴", "high": "🟠", "medium": "🟡", "low": "🔵"}.get(risk['level'], "⚪")
            print(f"      {icon} [{risk['level'].upper()}] {risk['category']}")
            print(f"         {risk['description']}")
            print(f"         P={risk['probability']:.0%}, Impact={risk['impact']:.0%}")
    
    print(f"\n📅 Timeline Estimate:")
    timeline = result['timeline_estimate']
    print(f"   Estimated: {timeline['estimated_days']} days")
    print(f"   Target: {timeline['target_days']} days")
    print(f"   Feasible: {'YES ✓' if timeline['feasible'] else 'NO ⚠️'}")
    print(f"   Variance: ±{timeline['variance_days']} days")
    
    print(f"\n👥 Resource Assessment:")
    resources = result['resource_assessment']
    print(f"   Adequate: {'YES ✓' if resources['adequate'] else 'NO ⚠️'}")
    if resources['gaps']:
        print("   Gaps:")
        for role, gap in resources['gaps'].items():
            print(f"      • {role}: need {gap} more")
    
    if result['recommendations']:
        print("\n💡 Recommendations:")
        for i, rec in enumerate(result['recommendations'][:5], 1):
            print(f"   {i}. {rec}")
    
    if result['early_warning_indicators']:
        print("\n🔔 Early Warning Indicators:")
        for warning in result['early_warning_indicators'][:3]:
            print(f"   • {warning['indicator']} ({warning['risk_level']})")
    
    print("\n" + "=" * 70)
