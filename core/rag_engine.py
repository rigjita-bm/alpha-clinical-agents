"""
RAG Engine - Retrieval-Augmented Generation
Source-grounded document generation with FAISS semantic search
"""

import re
import hashlib
import logging
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

import numpy as np

# Optional imports - system works without FAISS in fallback mode
try:
    import faiss
    FAISS_AVAILABLE = True
except ImportError:
    FAISS_AVAILABLE = False
    logging.warning("FAISS not available. Using fallback search mode.")

try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False
    logging.warning("sentence-transformers not available. Using fallback embeddings.")


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
    embedding: Optional[np.ndarray] = None
    
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
    Vector store for document chunks using FAISS
    Semantic search with sentence embeddings
    Falls back to simple keyword search if FAISS unavailable
    """
    
    def __init__(self, model_name: str = 'all-MiniLM-L6-v2'):
        """
        Initialize document store with embedding model
        
        Args:
            model_name: Sentence transformer model for embeddings
        """
        self.chunks: List[DocumentChunk] = []
        self.fallback_mode = not FAISS_AVAILABLE
        
        if self.fallback_mode:
            # Fallback: simple keyword-based storage
            self.dimension = 384  # Default dimension
            self.index = None
            logging.info("DocumentStore initialized in fallback mode (no FAISS)")
        else:
            # FAISS mode
            if SENTENCE_TRANSFORMERS_AVAILABLE:
                self.model = SentenceTransformer(model_name)
                self.dimension = self.model.get_sentence_embedding_dimension()
            else:
                self.dimension = 384
                self.model = None
            
            # Initialize FAISS index (Inner Product = Cosine similarity for normalized vectors)
            self.index = faiss.IndexFlatIP(self.dimension)
        
        self.id_map: Dict[int, str] = {}  # Maps FAISS index to chunk_id
        
    def add_document(self, content: str, source: str, doc_type: DocumentType,
                    section: str = "", page: Optional[int] = None) -> None:
        """
        Add document to store with semantic chunking
        
        Args:
            content: Document text
            source: Document name/identifier
            doc_type: Type of document
            section: Section within document
            page: Page number
        """
        # Semantic chunking: split into meaningful paragraphs
        paragraphs = self._chunk_document(content)
        
        embeddings = []
        for para in paragraphs:
            chunk = DocumentChunk(
                content=para,
                source=source,
                doc_type=doc_type,
                section=section,
                page=page
            )
            
            # Create embedding if model available
            if self.model is not None:
                embedding = self.model.encode(para, convert_to_numpy=True)
                embedding = embedding / np.linalg.norm(embedding)  # Normalize for cosine similarity
                chunk.embedding = embedding
                embeddings.append(embedding)
            else:
                # Fallback: no embeddings
                chunk.embedding = None
            
            self.chunks.append(chunk)
            
        # Add to FAISS index if available
        if embeddings and self.index is not None:
            embeddings_array = np.array(embeddings).astype('float32')
            start_idx = self.index.ntotal
            self.index.add(embeddings_array)
            
            # Map indices to chunk IDs
            for i, chunk in enumerate(self.chunks[-len(embeddings):]):
                self.id_map[start_idx + i] = chunk.chunk_id
    
    def _chunk_document(self, content: str, max_chunk_size: int = 512) -> List[str]:
        """
        Split document into semantic chunks
        
        Args:
            content: Full document text
            max_chunk_size: Maximum tokens per chunk
            
        Returns:
            List of document chunks
        """
        # Split by paragraphs first
        paragraphs = [p.strip() for p in content.split('\n\n') if len(p.strip()) > 50]
        
        chunks = []
        current_chunk = []
        current_size = 0
        
        for para in paragraphs:
            para_size = len(para.split())  # Rough token count
            
            if current_size + para_size > max_chunk_size and current_chunk:
                # Save current chunk and start new one
                chunks.append(' '.join(current_chunk))
                current_chunk = [para]
                current_size = para_size
            else:
                current_chunk.append(para)
                current_size += para_size
        
        # Don't forget the last chunk
        if current_chunk:
            chunks.append(' '.join(current_chunk))
        
        return chunks if chunks else [content]
    
    def retrieve(self, query: str, top_k: int = 5,
                doc_types: Optional[List[DocumentType]] = None) -> List[Tuple[DocumentChunk, float]]:
        """
        Retrieve relevant chunks using semantic search
        Falls back to keyword search if FAISS unavailable
        
        Args:
            query: Search query
            top_k: Number of results to return
            doc_types: Filter by document types
            
        Returns:
            List of (chunk, score) tuples sorted by relevance
        """
        # Fallback mode: simple keyword matching
        if self.fallback_mode or self.index is None or self.model is None:
            return self._fallback_retrieve(query, top_k, doc_types)
        
        # Create query embedding
        query_embedding = self.model.encode(query, convert_to_numpy=True)
        query_embedding = query_embedding / np.linalg.norm(query_embedding)  # Normalize
        query_embedding = np.array([query_embedding]).astype('float32')
        
        # Search FAISS index
        scores, indices = self.index.search(query_embedding, top_k)
        
        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx == -1:  # FAISS returns -1 for empty slots
                continue
                
            chunk_id = self.id_map.get(int(idx))
            if not chunk_id:
                continue
            
            # Find chunk by ID
            chunk = next((c for c in self.chunks if c.chunk_id == chunk_id), None)
            if not chunk:
                continue
            
            # Filter by document type if specified
            if doc_types and chunk.doc_type not in doc_types:
                continue
            
            results.append((chunk, float(score)))
        
        return results
    
    def _fallback_retrieve(self, query: str, top_k: int = 5,
                          doc_types: Optional[List[DocumentType]] = None) -> List[Tuple[DocumentChunk, float]]:
        """
        Fallback retrieval using simple keyword matching
        
        Args:
            query: Search query
            top_k: Number of results to return
            doc_types: Filter by document types
            
        Returns:
            List of (chunk, score) tuples
        """
        query_words = set(query.lower().split())
        results = []
        
        for chunk in self.chunks:
            # Filter by document type if specified
            if doc_types and chunk.doc_type not in doc_types:
                continue
            
            # Simple word overlap scoring
            chunk_words = set(chunk.content.lower().split())
            overlap = len(query_words & chunk_words)
            score = overlap / max(len(query_words), 1)
            
            if score > 0:
                results.append((chunk, score))
        
        # Sort by score and return top_k
        results.sort(key=lambda x: x[1], reverse=True)
        return results[:top_k]
    
    def verify_claim(self, claim: str, threshold: float = 0.7) -> Tuple[bool, List[RetrievedFact]]:
        """
        Verify a claim against stored documents
        
        Args:
            claim: Claim to verify
            threshold: Minimum similarity score for verification
            
        Returns:
            (is_verified, supporting_facts)
        """
        results = self.retrieve(claim, top_k=3)
        
        supporting_facts = []
        for chunk, score in results:
            if score >= threshold:
                supporting_facts.append(RetrievedFact(
                    fact_text=chunk.content,
                    source_chunk=chunk,
                    relevance_score=score,
                    fact_type=self._classify_fact_type(chunk.content)
                ))
        
        is_verified = len(supporting_facts) > 0
        return is_verified, supporting_facts
    
    def _classify_fact_type(self, text: str) -> str:
        """Classify the type of fact in the text"""
        text_lower = text.lower()
        
        if re.search(r'\b(n=\d+|\d+\s*patients|\d+\s*subjects)\b', text_lower):
            return "number"
        elif re.search(r'\b(primary|secondary)\s+endpoint', text_lower):
            return "endpoint"
        elif re.search(r'\b(inclusion|exclusion)\s+criteria', text_lower):
            return "criteria"
        elif re.search(r'\b(procedure|method|assess)\b', text_lower):
            return "procedure"
        else:
            return "general"
    
    def generate_with_citations(self, prompt: str, context_window: int = 3) -> Tuple[str, List[Citation]]:
        """
        Generate text with automatic citations
        
        Args:
            prompt: Generation prompt
            context_window: Number of chunks to retrieve
            
        Returns:
            (generated_text, citations)
        """
        # Retrieve relevant context
        results = self.retrieve(prompt, top_k=context_window)
        
        # Build context
        context_parts = []
        citations = []
        
        for chunk, score in results:
            context_parts.append(f"[{chunk.source}, {chunk.section}]: {chunk.content}")
            
            citations.append(Citation(
                claim_text=chunk.content[:100] + "...",
                source_doc=chunk.source,
                section=chunk.section,
                page=chunk.page,
                confidence=score
            ))
        
        # In real implementation, this would call an LLM with the context
        # For now, return a structured response
        context_str = "\n".join(context_parts)
        generated_text = f"Based on the following sources:\n{context_str}\n\n[Generated response would go here]"
        
        return generated_text, citations
    
    def save(self, path: str) -> None:
        """Save index and chunks to disk"""
        faiss.write_index(self.index, f"{path}.index")
        
        # Save chunks and id_map
        import pickle
        with open(f"{path}.meta", 'wb') as f:
            pickle.dump({
                'chunks': self.chunks,
                'id_map': self.id_map,
                'dimension': self.dimension
            }, f)
    
    def load(self, path: str) -> None:
        """Load index and chunks from disk"""
        self.index = faiss.read_index(f"{path}.index")
        
        import pickle
        with open(f"{path}.meta", 'rb') as f:
            meta = pickle.load(f)
            self.chunks = meta['chunks']
            self.id_map = meta['id_map']
            self.dimension = meta['dimension']


class RAGEngine:
    """
    High-level RAG engine for clinical document generation
    Coordinates document store, retrieval, and citation
    """
    
    def __init__(self):
        self.document_store = DocumentStore()
        self.protocol_data: Optional[Dict] = None
    
    def load_protocol(self, protocol_text: str, study_id: str) -> None:
        """Load and index protocol document"""
        self.document_store.add_document(
            content=protocol_text,
            source=f"Protocol_{study_id}",
            doc_type=DocumentType.PROTOCOL,
            section="Protocol"
        )
        
        # Extract and index sections separately
        sections = self._extract_protocol_sections(protocol_text)
        for section_name, section_text in sections.items():
            self.document_store.add_document(
                content=section_text,
                source=f"Protocol_{study_id}",
                doc_type=DocumentType.PROTOCOL,
                section=section_name
            )
    
    def load_statistical_output(self, stats_text: str, study_id: str) -> None:
        """Load and index statistical output (TLFs)"""
        self.document_store.add_document(
            content=stats_text,
            source=f"Stats_{study_id}",
            doc_type=DocumentType.STATISTICAL_OUTPUT,
            section="Statistical Analysis"
        )
    
    def _extract_protocol_sections(self, protocol_text: str) -> Dict[str, str]:
        """Extract sections from protocol text"""
        sections = {}
        
        # Simple section extraction based on common headers
        section_patterns = [
            (r'(?i)(STUDY DESIGN|DESIGN).*?(?=\n\n|\Z)', 'Study Design'),
            (r'(?i)(INCLUSION CRITERIA).*?(?=EXCLUSION|\Z)', 'Inclusion Criteria'),
            (r'(?i)(EXCLUSION CRITERIA).*?(?=\n\n|\Z)', 'Exclusion Criteria'),
            (r'(?i)(ENDPOINTS|PRIMARY ENDPOINT).*?(?=\n\n|\Z)', 'Endpoints'),
            (r'(?i)(STATISTICAL METHODS|STATISTICS).*?(?=\n\n|\Z)', 'Statistical Methods'),
        ]
        
        for pattern, section_name in section_patterns:
            match = re.search(pattern, protocol_text, re.DOTALL)
            if match:
                sections[section_name] = match.group(0)
        
        return sections
    
    def generate_section_with_citations(self, section_name: str, prompt: str) -> Dict[str, Any]:
        """Generate a document section with automatic citations"""
        # Retrieve relevant context
        context_results = self.document_store.retrieve(
            query=f"{section_name}: {prompt}",
            top_k=5
        )
        
        # Build cited context
        context_with_citations = []
        for chunk, score in context_results:
            context_with_citations.append({
                "text": chunk.content,
                "source": chunk.source,
                "section": chunk.section,
                "page": chunk.page,
                "relevance": score
            })
        
        return {
            "section": section_name,
            "context": context_with_citations,
            "citations": [c for c in context_with_citations],
            "grounded": len(context_results) > 0
        }
    
    def verify_statistics(self, claim: str) -> Dict[str, Any]:
        """Verify statistical claims against source data"""
        is_verified, facts = self.document_store.verify_claim(
            claim,
            threshold=0.7
        )
        
        return {
            "verified": is_verified,
            "confidence": max([f.relevance_score for f in facts], default=0),
            "supporting_facts": [
                {
                    "text": f.fact_text,
                    "source": f.source_chunk.source,
                    "score": f.relevance_score
                }
                for f in facts
            ]
        }

        # Filter by document type
        for chunk in all_chunks:
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
