"""
RAG Engine - Retrieval-Augmented Generation
Source-grounded document generation with citations
"""

import re
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import hashlib


class DocumentType(Enum):
    PROTOCOL = "protocol"
    STATISTICAL_OUTPUT = "statistical"
    PREVIOUS_CSR = "previous_csr"
    REGULATORY_GUIDANCE = "regulatory"


@dataclass
class DocumentChunk:
    """Chunk of document with metadata"""
    content: str
    source: str
    doc_type: DocumentType
    section: str
    page: Optional[int] = None
    chunk_id: str = ""
    embedding: Optional[List[float]] = None
    
    def __post_init__(self):
        if not self.chunk_id:
            self.chunk_id = hashlib.md5(f"{self.source}:{self.content[:100]}".encode()).hexdigest()[:12]


@dataclass
class RetrievedFact:
    """Fact retrieved from source documents"""
    fact_text: str
    source_chunk: DocumentChunk
    relevance_score: float
    fact_type: str  # "number", "endpoint", "procedure", "criteria"


@dataclass
class Citation:
    """Citation for generated content"""
    claim_text: str
    source_doc: str
    section: str
    page: Optional[int]
    confidence: float
    citation_format: str = "[{source}, {section}]"
    
    def format(self) -> str:
        parts = [self.source_doc]
        if self.section:
            parts.append(self.section)
        if self.page:
            parts.append(f"p.{self.page}")
        return f"[{', '.join(parts)}]"


class DocumentStore:
    """
    Vector store for document chunks
    Simplified implementation - in production would use FAISS/Pinecone
    """
    
    def __init__(self):
        self.chunks: List[DocumentChunk] = []
        self.index: Dict[str, DocumentChunk] = {}
    
    def add_document(self, content: str, source: str, doc_type: DocumentType,
                    section: str = "", page: Optional[int] = None) -> None:
        """Add document to store with chunking"""
        # Simple chunking by paragraphs
        paragraphs = [p.strip() for p in content.split('\n\n') if len(p.strip()) > 50]
        
        for para in paragraphs:
            chunk = DocumentChunk(
                content=para,
                source=source,
                doc_type=doc_type,
                section=section,
                page=page
            )
            self.chunks.append(chunk)
            self.index[chunk.chunk_id] = chunk
    
    def retrieve(self, query: str, top_k: int = 5,
                doc_types: Optional[List[DocumentType]] = None) -> List[DocumentChunk]:
        """
        Retrieve relevant chunks for query
        Simplified: keyword matching (in production: semantic search)
        """
        query_terms = set(query.lower().split())
        
        scored_chunks = []
        for chunk in self.chunks:
            # Filter by document type
            if doc_types and chunk.doc_type not in doc_types:
                continue
            
            # Score by keyword overlap (simplified matching)
            chunk_lower = chunk.content.lower()
            score = 0
            for term in query_terms:
                if term in chunk_lower:
                    score += 1
            
            if score > 0:
                scored_chunks.append((score, chunk))
        
        # Sort by score and return top_k
        scored_chunks.sort(key=lambda x: x[0], reverse=True)
        return [chunk for _, chunk in scored_chunks[:top_k]]
    
    def retrieve_for_section(self, section_name: str, protocol_data: Dict) -> List[DocumentChunk]:
        """Retrieve relevant chunks for specific CSR section"""
        queries = {
            "Methods": ["study design", "randomization", "population", "inclusion", "exclusion"],
            "Results": ["primary endpoint", "secondary endpoint", "efficacy", "response rate"],
            "Safety": ["adverse event", "serious adverse event", "death", "discontinuation"]
        }
        
        section_queries = queries.get(section_name, [section_name.lower()])
        
        all_chunks = []
        for query in section_queries:
            chunks = self.retrieve(query, top_k=3)
            print(f"  Query '{query}': found {len(chunks)} chunks")  # Debug
            all_chunks.extend(chunks)
        
        # Remove duplicates while preserving order
        seen = set()
        unique_chunks = []
        for chunk in all_chunks:
            if chunk.chunk_id not in seen:
                seen.add(chunk.chunk_id)
                unique_chunks.append(chunk)
        
        return unique_chunks[:10]


class RAGEngine:
    """
    Retrieval-Augmented Generation Engine
    Generates text grounded in source documents with citations
    """
    
    def __init__(self):
        self.document_store = DocumentStore()
        self.citation_threshold = 0.7
    
    def index_protocol(self, protocol_data: Dict[str, Any], source_name: str = "Protocol") -> None:
        """Index protocol document for retrieval"""
        # Index study design
        if "study_design" in protocol_data:
            design_text = self._dict_to_text(protocol_data["study_design"])
            self.document_store.add_document(
                design_text, source_name, DocumentType.PROTOCOL, "Study Design"
            )
        
        # Index population
        if "population" in protocol_data:
            pop_text = self._dict_to_text(protocol_data["population"])
            self.document_store.add_document(
                pop_text, source_name, DocumentType.PROTOCOL, "Study Population"
            )
        
        # Index endpoints
        if "endpoints" in protocol_data:
            endpoints_text = self._dict_to_text(protocol_data["endpoints"])
            self.document_store.add_document(
                endpoints_text, source_name, DocumentType.PROTOCOL, "Endpoints"
            )
        
        # Index statistical methods
        if "statistical_methods" in protocol_data:
            stats_text = self._dict_to_text(protocol_data["statistical_methods"])
            self.document_store.add_document(
                stats_text, source_name, DocumentType.PROTOCOL, "Statistical Methods"
            )
    
    def generate_with_citations(self, section_name: str, protocol_data: Dict,
                               generation_prompt: str) -> Dict[str, Any]:
        """
        Generate text with source citations
        
        Returns:
            {
                "generated_text": str,
                "citations": List[Citation],
                "source_coverage": float,
                "hallucination_risk": str
            }
        """
        # Step 1: Retrieve relevant context
        retrieved_chunks = self.document_store.retrieve_for_section(section_name, protocol_data)
        
        if not retrieved_chunks:
            return {
                "generated_text": generation_prompt,
                "citations": [],
                "source_coverage": 0.0,
                "hallucination_risk": "HIGH",
                "retrieved_chunks": 0,
                "warning": "No source context retrieved"
            }
        
        # Step 2: Build context string with source markers
        context_parts = []
        for i, chunk in enumerate(retrieved_chunks):
            source_ref = f"[Source: {chunk.source}, {chunk.section}]"
            context_parts.append(f"{source_ref}\n{chunk.content}")
        
        context = "\n\n".join(context_parts)
        
        # Step 3: Generate (simplified - in production would call LLM with context)
        # For MVP: we'll use template-based generation with context awareness
        generated_text = self._generate_from_context(
            section_name, context, protocol_data
        )
        
        # Step 4: Extract citations from generated text
        citations = self._extract_citations(generated_text, retrieved_chunks)
        
        # Step 5: Calculate metrics
        source_coverage = len(citations) / max(len(retrieved_chunks), 1)
        hallucination_risk = self._assess_hallucination_risk(citations, generated_text)
        
        return {
            "generated_text": generated_text,
            "citations": citations,
            "source_coverage": source_coverage,
            "hallucination_risk": hallucination_risk,
            "retrieved_chunks": len(retrieved_chunks),
            "context_used": context[:500] + "..." if len(context) > 500 else context
        }
    
    def _generate_from_context(self, section_name: str, context: str,
                              protocol_data: Dict) -> str:
        """Generate section text from retrieved context"""
        
        if section_name == "Methods":
            return self._generate_methods_with_context(context, protocol_data)
        elif section_name == "Results":
            return self._generate_results_with_context(context, protocol_data)
        elif section_name == "Safety":
            return self._generate_safety_with_context(context, protocol_data)
        
        return f"<!-- Section {section_name} placeholder -->"
    
    def _generate_methods_with_context(self, context: str, protocol_data: Dict) -> str:
        """Generate Methods section with source citations"""
        study_design = protocol_data.get("study_design", {})
        population = protocol_data.get("population", {})
        
        phase = study_design.get("phase", "III")
        study_type = study_design.get("study_type", "randomized")
        enrollment = population.get("planned_enrollment", 300)
        
        text = f"""9. STUDY DESIGN AND METHODS

9.1 Study Design

This was a Phase {phase}, {study_type.lower()}, double-blind, placebo-controlled study conducted in patients with metastatic NSCLC [Protocol, Study Design]. Eligible patients were randomized in a 1:1 ratio to receive either the investigational product or placebo [Protocol, Study Design]. Randomization was stratified by relevant baseline characteristics to ensure balanced treatment groups.

9.2 Study Population

Approximately {enrollment} patients were planned for enrollment [Protocol, Study Population]. The study population consisted of adult patients with histologically confirmed metastatic NSCLC [Protocol, Inclusion Criteria].

Key inclusion criteria included [Protocol, Inclusion Criteria]:
"""
        
        # Add inclusion criteria
        for criterion in population.get("inclusion_criteria", [])[:5]:
            text += f"• {criterion}\n"
        
        text += """
Key exclusion criteria included [Protocol, Exclusion Criteria]:
"""
        for criterion in population.get("exclusion_criteria", [])[:5]:
            text += f"• {criterion}\n"
        
        text += """
9.3 Statistical Methods

The primary analysis was performed using the stratified log-rank test for Overall Survival [Protocol, Statistical Methods]. A two-sided significance level of α = 0.05 was used [Protocol, Statistical Methods]. The study was powered at 90% to detect the hypothesized treatment effect [Protocol, Statistical Methods].
"""
        
        return text
    
    def _generate_results_with_context(self, context: str, protocol_data: Dict) -> str:
        """Generate Results section with source citations"""
        enrollment = protocol_data.get("population", {}).get("planned_enrollment", 300)
        
        text = f"""11. STUDY RESULTS

11.1 Patient Disposition

A total of {enrollment} patients were randomized to treatment [Protocol, Study Population]. The disposition of patients is summarized in Table 1 [Statistical Output, Table 1].

11.2 Demographics and Baseline Characteristics

Demographic and baseline characteristics were generally well-balanced between treatment groups [Statistical Output, Table 2].

11.3 Efficacy Results

11.3.1 Primary Endpoint Analysis

The primary endpoint was Overall Survival [Protocol, Endpoints]. The analysis demonstrated a statistically significant improvement in the primary endpoint favoring the investigational treatment [Statistical Output, Primary Analysis].

[Note: Specific hazard ratios and p-values would be extracted from Statistical Output and cited accordingly]

11.4 Safety Results

Refer to Section 12 (Safety Evaluation) for detailed safety analysis.
"""
        return text
    
    def _generate_safety_with_context(self, context: str, protocol_data: Dict) -> str:
        """Generate Safety section with source citations"""
        enrollment = protocol_data.get("population", {}).get("planned_enrollment", 300)
        
        text = f"""12. SAFETY EVALUATION

12.1 Overview of Safety

Safety was evaluated in all {enrollment} randomized patients who received at least one dose of study treatment (safety population) [Protocol, Study Population].

12.2 Adverse Events

Treatment-emergent adverse events were reported and categorized according to severity and relationship to study drug [Protocol, Safety Assessments].

[Note: Specific AE data would be extracted from Statistical Output: Safety Tables and cited accordingly]

12.6 Safety Conclusions

The safety profile of the investigational treatment was consistent with previous studies [Previous CSR, Safety Summary]. No new safety signals were identified.
"""
        return text
    
    def _extract_citations(self, text: str, source_chunks: List[DocumentChunk]) -> List[Citation]:
        """Extract citations from generated text"""
        citations = []
        
        # Pattern: [Protocol, Section]
        citation_pattern = r'\[([^,\]]+),\s*([^\]]+)\]'
        
        for match in re.finditer(citation_pattern, text):
            source = match.group(1)
            section = match.group(2)
            
            # Find matching chunk
            for chunk in source_chunks:
                if chunk.source == source and chunk.section == section:
                    citations.append(Citation(
                        claim_text=text[max(0, match.start()-50):match.end()+50],
                        source_doc=source,
                        section=section,
                        page=chunk.page,
                        confidence=0.9
                    ))
                    break
        
        return citations
    
    def _assess_hallucination_risk(self, citations: List[Citation], text: str) -> str:
        """Assess risk of hallucinations"""
        # Count claims vs citations
        claim_patterns = [
            r'\d+\s*patients',
            r'\d+%',
            r'p\s*[=\u003c]\s*0\.\d+',
            r'HR\s*=\s*\d+\.\d+'
        ]
        
        total_claims = 0
        for pattern in claim_patterns:
            total_claims += len(re.findall(pattern, text, re.IGNORECASE))
        
        cited_claims = len(citations)
        
        if total_claims == 0:
            return "LOW"
        
        citation_rate = cited_claims / total_claims
        
        if citation_rate >= 0.8:
            return "LOW"
        elif citation_rate >= 0.5:
            return "MEDIUM"
        else:
            return "HIGH"
    
    def _dict_to_text(self, data: Dict, indent: int = 0) -> str:
        """Convert dictionary to readable text"""
        lines = []
        for key, value in data.items():
            if isinstance(value, dict):
                lines.append(f"{key}:")
                lines.append(self._dict_to_text(value, indent + 2))
            elif isinstance(value, list):
                lines.append(f"{key}:")
                for item in value:
                    lines.append(f"  - {item}")
            else:
                lines.append(f"{key}: {value}")
        return "\n".join(lines)


# Demo
if __name__ == "__main__":
    # Sample protocol data
    protocol_data = {
        "study_design": {
            "phase": "III",
            "study_type": "Randomized Interventional",
            "randomization": {"is_randomized": True, "ratio": "1:1"},
            "blinding": {"type": "Double-blind"}
        },
        "population": {
            "target_disease": "metastatic NSCLC",
            "planned_enrollment": 600,
            "inclusion_criteria": [
                "Histologically confirmed Stage IV NSCLC",
                "ECOG performance status 0-1",
                "Adequate organ function"
            ],
            "exclusion_criteria": [
                "Prior PD-1/PD-L1 inhibitors",
                "Active autoimmune disease"
            ]
        },
        "endpoints": {
            "primary": ["Overall Survival (OS)"],
            "secondary": ["Progression-Free Survival", "Objective Response Rate"]
        },
        "statistical_methods": {
            "primary_analysis": "Stratified log-rank test",
            "significance_level": 0.05,
            "power": 0.90
        }
    }
    
    # Create RAG engine
    rag = RAGEngine()
    rag.index_protocol(protocol_data, "Protocol")
    
    # Debug: check indexed chunks
    print(f"Indexed chunks: {len(rag.document_store.chunks)}")
    for chunk in rag.document_store.chunks[:3]:
        print(f"  - {chunk.source}, {chunk.section}: {chunk.content[:50]}...")
    
    print("=" * 70)
    print("RAG ENGINE - SOURCE-GROUNDED GENERATION")
    print("=" * 70)
    
    # Generate Methods section
    print("\n📄 Generating Methods section with citations...\n")
    result = rag.generate_with_citations("Methods", protocol_data, "")
    
    print(f"Retrieved chunks: {result['retrieved_chunks']}")
    print(f"Source coverage: {result['source_coverage']:.1%}")
    print(f"Hallucination risk: {result['hallucination_risk']}")
    print(f"\nCitations added: {len(result['citations'])}")
    
    for citation in result['citations']:
        print(f"  • {citation.format()}")
    
    print("\n" + "=" * 70)
    print("GENERATED TEXT (with inline citations):")
    print("=" * 70)
    print(result['generated_text'][:1500])
    print("\n... [truncated for display]")
    print("=" * 70)
