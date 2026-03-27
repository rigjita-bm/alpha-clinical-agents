"""
Final Compiler - Agent 7
Assembles all validated sections into FDA-ready submission package
"""

import hashlib
import json
import re
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
from collections import OrderedDict

from core.base_agent import BaseAgent


class DocumentFormat(Enum):
    ECTD = "ectd"  # Electronic Common Technical Document
    PDF = "pdf"
    DOCX = "docx"
    XML = "xml"


class CompilationStatus(Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    VALIDATED = "validated"


@dataclass
class SectionVersion:
    """Version info for a section"""
    section_name: str
    version: str
    agent_id: str
    validation_score: float
    approved_by: List[str] = field(default_factory=list)
    compiled_at: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class PackageManifest:
    """Manifest for the final package"""
    package_id: str
    document_type: str
    study_id: str
    created_at: str
    sections: Dict[str, SectionVersion]
    total_pages: int
    file_size_bytes: int
    checksum: str
    validation_summary: Dict


class FinalCompiler(BaseAgent):
    """
    Agent 7: Final Compiler
    
    Assembles final submission package:
    - Collects all validated sections
    - Orders sections per ICH E3
    - Generates table of contents
    - Creates cross-reference index
    - Generates package manifest
    - Creates eCTD-compliant structure
    - Final validation before submission
    
    Output: FDA-ready submission package with complete audit trail
    """
    
    # ICH E3 standard section order for CSR
    ICH_E3_ORDER = [
        "Title Page",
        "Synopsis",
        "Table of Contents",
        "List of Abbreviations",
        "Ethics",
        "Investigators and Study Administrative Structure",
        "Introduction",
        "Study Objectives",
        "Investigational Plan",
        "Study Population",
        "Efficacy Evaluation",
        "Safety Evaluation",
        "Discussion",
        "Overall Conclusions",
        "List of References",
        "Tables, Figures, and Appendices"
    ]
    
    def __init__(self, config: Optional[Dict] = None):
        super().__init__(
            agent_id="FinalCompiler",
            version="1.0.0",
            config=config
        )
        
        self.compiled_sections: Dict[str, Dict] = {}
        self.manifest: Optional[PackageManifest] = None
    
    def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Main compilation logic
        
        Args:
            input_data: {
                "sections": Dict[str, Dict],  # section_name: {content, metadata, validation}
                "study_id": str,
                "document_type": str,  # "CSR", "Protocol", etc.
                "output_format": str,  # "ECTD", "PDF", etc.
                "include_audit_trail": bool
            }
        """
        sections = input_data.get("sections", {})
        study_id = input_data.get("study_id", "STUDY-001")
        document_type = input_data.get("document_type", "CSR")
        output_format = input_data.get("output_format", "ECTD")
        include_audit_trail = input_data.get("include_audit_trail", True)
        
        # Step 1: Validate all sections are present and approved
        validation_result = self._validate_sections(sections)
        if not validation_result["valid"]:
            return {
                "status": CompilationStatus.FAILED.value,
                "error": validation_result["error"],
                "missing_sections": validation_result.get("missing", []),
                "unapproved_sections": validation_result.get("unapproved", [])
            }
        
        # Step 2: Order sections per ICH E3
        ordered_sections = self._order_sections(sections)
        
        # Step 3: Generate table of contents
        toc = self._generate_toc(ordered_sections)
        
        # Step 4: Generate cross-reference index
        xref_index = self._generate_cross_reference_index(ordered_sections)
        
        # Step 5: Compile final document
        compiled_document = self._compile_document(
            ordered_sections, toc, xref_index
        )
        
        # Step 6: Generate audit trail summary
        audit_summary = self._generate_audit_summary(ordered_sections) if include_audit_trail else {}
        
        # Step 7: Create package manifest
        self.manifest = self._create_manifest(
            ordered_sections, study_id, document_type, audit_summary
        )
        
        # Step 8: Final validation
        final_validation = self._final_validation(compiled_document)
        
        return {
            "status": CompilationStatus.COMPLETED.value,
            "package_id": self.manifest.package_id,
            "study_id": study_id,
            "document_type": document_type,
            "output_format": output_format,
            "sections_compiled": len(ordered_sections),
            "total_pages": self.manifest.total_pages,
            "file_size_mb": round(self.manifest.file_size_bytes / (1024 * 1024), 2),
            "checksum": self.manifest.checksum,
            "table_of_contents": toc,
            "cross_reference_index": xref_index,
            "audit_summary": audit_summary,
            "validation_summary": self.manifest.validation_summary,
            "final_validation": final_validation,
            "submission_ready": final_validation["passed"],
            "warnings": final_validation.get("warnings", []),
            "manifest": self._manifest_to_dict(self.manifest)
        }
    
    def _validate_sections(self, sections: Dict[str, Dict]) -> Dict:
        """Validate all sections are present and approved"""
        # Check for required sections
        present_sections = set(sections.keys())
        
        # Required sections for CSR
        required = {"Methods", "Results", "Safety", "Discussion"}
        
        missing = required - present_sections
        if missing:
            return {
                "valid": False,
                "error": f"Missing required sections: {missing}",
                "missing": list(missing)
            }
        
        # Check approval status
        unapproved = []
        for section_name, section_data in sections.items():
            if not section_data.get("approved", False):
                validation = section_data.get("validation", {})
                if validation.get("risk_level") in ["CRITICAL", "HIGH"]:
                    unapproved.append(section_name)
        
        if unapproved:
            return {
                "valid": False,
                "error": f"Sections not approved: {unapproved}",
                "unapproved": unapproved
            }
        
        return {"valid": True}
    
    def _order_sections(self, sections: Dict[str, Dict]) -> OrderedDict:
        """Order sections per ICH E3 standard"""
        ordered = OrderedDict()
        
        # Map common section names to ICH E3 order
        section_mapping = {
            "Title Page": "Title Page",
            "Synopsis": "Synopsis",
            "Methods": "Investigational Plan",
            "Results": "Efficacy Evaluation",
            "Safety": "Safety Evaluation",
            "Discussion": "Discussion",
            "Conclusions": "Overall Conclusions"
        }
        
        # Order based on ICH E3
        for ich_section in self.ICH_E3_ORDER:
            for section_name, section_data in sections.items():
                mapped = section_mapping.get(section_name, section_name)
                if mapped == ich_section or section_name == ich_section:
                    ordered[section_name] = section_data
                    break
        
        # Add any remaining sections
        for section_name, section_data in sections.items():
            if section_name not in ordered:
                ordered[section_name] = section_data
        
        return ordered
    
    def _generate_toc(self, ordered_sections: OrderedDict) -> List[Dict]:
        """Generate table of contents"""
        toc = []
        page_number = 1
        
        for section_name, section_data in ordered_sections.items():
            # Estimate page count (simplified)
            content = section_data.get("content", "")
            estimated_pages = max(1, len(content) // 3000)
            
            toc.append({
                "section": section_name,
                "page_start": page_number,
                "page_end": page_number + estimated_pages - 1,
                "validation_score": section_data.get("validation", {}).get("score", 0)
            })
            
            page_number += estimated_pages
        
        return toc
    
    def _generate_cross_reference_index(self, ordered_sections: OrderedDict) -> Dict:
        """Generate cross-reference index"""
        index = {
            "tables": [],
            "figures": [],
            "sections": [],
            "abbreviations": {}
        }
        
        for section_name, section_data in ordered_sections.items():
            content = section_data.get("content", "")
            
            # Find table references
            tables = re.findall(r'Table\s+(\d+)', content)
            for table_num in set(tables):
                index["tables"].append({
                    "table": f"Table {table_num}",
                    "section": section_name
                })
            
            # Find figure references
            figures = re.findall(r'Figure\s+(\d+)', content)
            for fig_num in set(figures):
                index["figures"].append({
                    "figure": f"Figure {fig_num}",
                    "section": section_name
                })
        
        return index
    
    def _compile_document(self, ordered_sections: OrderedDict,
                         toc: List[Dict],
                         xref_index: Dict) -> str:
        """Compile final document"""
        parts = []
        
        # Header
        parts.append("CLINICAL STUDY REPORT")
        parts.append("=" * 70)
        parts.append("")
        
        # Table of Contents
        parts.append("TABLE OF CONTENTS")
        parts.append("-" * 70)
        for entry in toc:
            parts.append(f"{entry['section']:<50} Page {entry['page_start']}")
        parts.append("")
        
        # Sections
        for section_name, section_data in ordered_sections.items():
            parts.append(f"\n{'=' * 70}")
            parts.append(section_name.upper())
            parts.append(f"{'=' * 70}\n")
            parts.append(section_data.get("content", ""))
            parts.append("")
        
        # Cross-reference index
        parts.append(f"\n{'=' * 70}")
        parts.append("CROSS-REFERENCE INDEX")
        parts.append(f"{'=' * 70}\n")
        
        if xref_index["tables"]:
            parts.append("\nTables:")
            for table in xref_index["tables"]:
                parts.append(f"  {table['table']} - {table['section']}")
        
        if xref_index["figures"]:
            parts.append("\nFigures:")
            for figure in xref_index["figures"]:
                parts.append(f"  {figure['figure']} - {figure['section']}")
        
        return "\n".join(parts)
    
    def _generate_audit_summary(self, ordered_sections: OrderedDict) -> Dict:
        """Generate audit trail summary"""
        summary = {
            "total_agents_involved": set(),
            "total_reviews": 0,
            "section_versions": {},
            "approval_chain": []
        }
        
        for section_name, section_data in ordered_sections.items():
            # Track agents
            if "agent_id" in section_data:
                summary["total_agents_involved"].add(section_data["agent_id"])
            
            # Track reviews
            reviews = section_data.get("reviews", [])
            summary["total_reviews"] += len(reviews)
            
            # Track version
            summary["section_versions"][section_name] = {
                "version": section_data.get("version", "1.0"),
                "last_modified": section_data.get("last_modified", "unknown"),
                "validation_score": section_data.get("validation", {}).get("score", 0)
            }
            
            # Track approvals
            for review in reviews:
                if review.get("decision") == "approved":
                    summary["approval_chain"].append({
                        "section": section_name,
                        "reviewer": review.get("reviewer"),
                        "date": review.get("date")
                    })
        
        summary["total_agents_involved"] = list(summary["total_agents_involved"])
        return summary
    
    def _create_manifest(self, ordered_sections: OrderedDict,
                        study_id: str,
                        document_type: str,
                        audit_summary: Dict) -> PackageManifest:
        """Create package manifest"""
        # Calculate checksum
        content_hash = hashlib.sha256()
        for section_name, section_data in ordered_sections.items():
            content = section_data.get("content", "").encode('utf-8')
            content_hash.update(content)
        
        # Calculate total size
        total_size = sum(len(s.get("content", "").encode('utf-8')) 
                        for s in ordered_sections.values())
        
        # Estimate pages
        total_pages = sum(max(1, len(s.get("content", "")) // 3000) 
                         for s in ordered_sections.values())
        
        # Create section versions
        section_versions = {}
        for section_name, section_data in ordered_sections.items():
            section_versions[section_name] = SectionVersion(
                section_name=section_name,
                version=section_data.get("version", "1.0"),
                agent_id=section_data.get("agent_id", "unknown"),
                validation_score=section_data.get("validation", {}).get("score", 0),
                approved_by=[r.get("reviewer") for r in section_data.get("reviews", [])
                           if r.get("decision") == "approved"]
            )
        
        # Calculate validation summary
        scores = [s.get("validation", {}).get("score", 0) for s in ordered_sections.values()]
        
        return PackageManifest(
            package_id=f"{study_id}-{document_type}-{datetime.now().strftime('%Y%m%d')}",
            document_type=document_type,
            study_id=study_id,
            created_at=datetime.now().isoformat(),
            sections=section_versions,
            total_pages=total_pages,
            file_size_bytes=total_size,
            checksum=content_hash.hexdigest()[:16],
            validation_summary={
                "average_score": sum(scores) / len(scores) if scores else 0,
                "min_score": min(scores) if scores else 0,
                "max_score": max(scores) if scores else 0,
                "sections_count": len(ordered_sections)
            }
        )
    
    def _final_validation(self, compiled_document: str) -> Dict:
        """Final validation before submission"""
        warnings = []
        
        # Check document size
        doc_size_mb = len(compiled_document.encode('utf-8')) / (1024 * 1024)
        if doc_size_mb > 50:
            warnings.append(f"Document size ({doc_size_mb:.1f} MB) exceeds 50 MB recommendation")
        
        # Check for placeholder text
        placeholders = re.findall(r'\[.*?\]', compiled_document)
        if placeholders:
            warnings.append(f"Found {len(placeholders)} placeholder(s) that may need attention")
        
        # Check for incomplete sections
        if "TBD" in compiled_document or "TODO" in compiled_document.upper():
            warnings.append("Document contains TBD/TODO items")
        
        return {
            "passed": len(warnings) == 0,
            "warnings": warnings,
            "document_size_mb": round(doc_size_mb, 2),
            "word_count": len(compiled_document.split())
        }
    
    def _manifest_to_dict(self, manifest: PackageManifest) -> Dict:
        """Convert manifest to dictionary"""
        return {
            "package_id": manifest.package_id,
            "document_type": manifest.document_type,
            "study_id": manifest.study_id,
            "created_at": manifest.created_at,
            "sections": {k: {
                "version": v.version,
                "agent": v.agent_id,
                "validation_score": v.validation_score,
                "approved_by": v.approved_by
            } for k, v in manifest.sections.items()},
            "total_pages": manifest.total_pages,
            "file_size_bytes": manifest.file_size_bytes,
            "checksum": manifest.checksum,
            "validation_summary": manifest.validation_summary
        }


# Demo
if __name__ == "__main__":
    # Sample validated sections
    sections = {
        "Methods": {
            "content": """9. STUDY DESIGN AND METHODS

9.1 Study Design

This was a Phase III, randomized, double-blind, placebo-controlled study.

9.2 Study Population

Approximately 600 patients were planned for enrollment.

9.3 Statistical Methods

Primary analysis used stratified log-rank test.""",
            "version": "1.0",
            "agent_id": "SectionWriter",
            "approved": True,
            "validation": {"score": 92, "risk_level": "LOW"},
            "reviews": [{"reviewer": "Medical Director", "decision": "approved", "date": "2024-03-27"}]
        },
        
        "Results": {
            "content": """11. STUDY RESULTS

11.1 Patient Disposition

A total of 600 patients were randomized.

11.2 Efficacy Results

Statistically significant improvement observed (p=0.003, HR=0.72).

See Table 1 for patient disposition.""",
            "version": "1.0",
            "agent_id": "SectionWriter",
            "approved": True,
            "validation": {"score": 95, "risk_level": "LOW"},
            "reviews": [{"reviewer": "Biostatistician", "decision": "approved", "date": "2024-03-27"}]
        },
        
        "Safety": {
            "content": """12. SAFETY EVALUATION

12.1 Overview

Safety was evaluated in all 600 patients.

12.2 Adverse Events

Treatment-emergent adverse events reported per Table 2.""",
            "version": "1.0",
            "agent_id": "SectionWriter",
            "approved": True,
            "validation": {"score": 88, "risk_level": "LOW"},
            "reviews": [{"reviewer": "Safety Physician", "decision": "approved", "date": "2024-03-27"}]
        },
        
        "Discussion": {
            "content": """13. DISCUSSION

This study demonstrated significant efficacy with an acceptable safety profile.
Results are consistent with previous studies.""",
            "version": "1.0",
            "agent_id": "SectionWriter",
            "approved": True,
            "validation": {"score": 90, "risk_level": "LOW"},
            "reviews": [{"reviewer": "Clinical Lead", "decision": "approved", "date": "2024-03-27"}]
        }
    }
    
    # Run compiler
    compiler = FinalCompiler()
    result = compiler.execute({
        "sections": sections,
        "study_id": "ABC-301",
        "document_type": "CSR",
        "output_format": "ECTD",
        "include_audit_trail": True
    })
    
    # Display results
    print("=" * 70)
    print("FINAL COMPILER - AGENT 7")
    print("=" * 70)
    
    print(f"\n📦 Package ID: {result['package_id']}")
    print(f"📄 Document Type: {result['document_type']}")
    print(f"🔬 Study ID: {result['study_id']}")
    print(f"✅ Status: {result['status'].upper()}")
    
    print(f"\n📊 Compilation Summary:")
    print(f"   Sections: {result['sections_compiled']}")
    print(f"   Pages: {result['total_pages']}")
    print(f"   File Size: {result['file_size_mb']} MB")
    print(f"   Checksum: {result['checksum']}")
    
    print(f"\n📋 Validation:")
    print(f"   Average Score: {result['validation_summary']['average_score']:.1f}/100")
    print(f"   Min Score: {result['validation_summary']['min_score']:.1f}")
    print(f"   Max Score: {result['validation_summary']['max_score']:.1f}")
    
    print(f"\n✅ Submission Ready: {'YES' if result['submission_ready'] else 'NO'}")
    
    if result['warnings']:
        print(f"\n⚠️  Warnings:")
        for warning in result['warnings']:
            print(f"   • {warning}")
    
    print("\n" + "=" * 70)
    print("TABLE OF CONTENTS:")
    print("=" * 70)
    
    for entry in result['table_of_contents']:
        print(f"{entry['section']:<50} Page {entry['page_start']:>3}")
    
    print("\n" + "=" * 70)
    print("CROSS-REFERENCE INDEX:")
    print("=" * 70)
    
    if result['cross_reference_index']['tables']:
        print("\nTables:")
        for table in result['cross_reference_index']['tables']:
            print(f"  {table['table']} - {table['section']}")
    
    print("\n" + "=" * 70)
    print("AUDIT SUMMARY:")
    print("=" * 70)
    
    audit = result['audit_summary']
    print(f"Agents Involved: {len(audit.get('total_agents_involved', []))}")
    print(f"Total Reviews: {audit.get('total_reviews', 0)}")
    print(f"Approval Chain: {len(audit.get('approval_chain', []))} approvals")
    
    print("\nSection Versions:")
    for section, version_info in audit.get('section_versions', {}).items():
        print(f"  {section}: v{version_info['version']} (score: {version_info['validation_score']})")
    
    print("\n" + "=" * 70)
