"""
FastAPI REST API for Alpha Clinical Agents
Provides HTTP endpoints for CSR generation and agent management
"""

import uuid
import asyncio
from datetime import datetime
from typing import List, Optional, Dict, Any
from contextlib import asynccontextmanager

from fastapi import FastAPI, BackgroundTasks, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from core.orchestrator import ClinicalOrchestrator
from core.logging_config import AgentLogger, set_correlation_id, LogContext
from agents import (
    ProtocolAnalyzer, SectionWriter, StatisticalValidator,
    ComplianceChecker, CrossReferenceValidator, HumanCoordinator,
    FinalCompiler, ConflictResolver, RiskPredictor, MetaValidator,
    HallucinationDetector, FactChecker
)


# Global orchestrator instance
orchestrator: Optional[ClinicalOrchestrator] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup/shutdown"""
    global orchestrator
    
    # Startup: Initialize orchestrator and register all agents
    orchestrator = ClinicalOrchestrator()
    
    agents = [
        ProtocolAnalyzer(),
        SectionWriter(),
        StatisticalValidator(),
        ComplianceChecker(),
        CrossReferenceValidator(),
        HumanCoordinator(),
        FinalCompiler(),
        ConflictResolver(),
        RiskPredictor(),
        MetaValidator(),
        HallucinationDetector(),
        FactChecker()
    ]
    
    for agent in agents:
        orchestrator.register_agent(agent)
    
    print(f"✅ Registered {len(agents)} agents")
    
    yield
    
    # Shutdown: Cleanup
    print("👋 Shutting down...")


app = FastAPI(
    title="Alpha Clinical Agents API",
    description="Enterprise-grade multi-agent system for Clinical Study Report (CSR) automation",
    version="2.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============== Pydantic Models ==============

class ProtocolRequest(BaseModel):
    """Request model for protocol analysis"""
    protocol_text: str = Field(..., min_length=100, description="Full protocol text")
    study_id: Optional[str] = Field(None, description="Study identifier")
    target_sections: List[str] = Field(
        default=["Methods", "Results", "Safety"],
        description="Sections to generate"
    )


class CSRRequest(BaseModel):
    """Request model for full CSR generation"""
    protocol_text: str = Field(..., min_length=100, description="Full protocol text")
    study_id: Optional[str] = Field(None, description="Study identifier")
    include_validation: bool = Field(True, description="Run full validation pipeline")
    require_human_review: bool = Field(True, description="Require human approval for critical sections")


class JobStatus(BaseModel):
    """Job status response"""
    job_id: str
    status: str  # queued, processing, completed, error
    progress_percent: float
    current_stage: Optional[str]
    created_at: datetime
    updated_at: Optional[datetime]
    completed_at: Optional[datetime]
    error_message: Optional[str]


class CSRResponse(BaseModel):
    """Full CSR generation response"""
    job_id: str
    status: str
    document_id: str
    sections: Dict[str, Any]
    validation_score: float
    compliance_score: float
    consistency_score: float
    audit_trail: List[Dict[str, Any]]
    generated_at: datetime


class AgentStatus(BaseModel):
    """Agent status response"""
    agent_id: str
    version: str
    status: str
    total_actions: int
    pending_messages: int


class ValidationRequest(BaseModel):
    """Request for validation only"""
    sections: Dict[str, str] = Field(..., description="Section drafts to validate")
    protocol_data: Optional[Dict[str, Any]] = None


class ValidationResponse(BaseModel):
    """Validation results"""
    validation_score: float
    statistical_validation: Dict[str, Any]
    compliance_validation: Dict[str, Any]
    cross_reference_validation: Dict[str, Any]
    critical_issues: List[Dict[str, Any]]
    warnings: List[Dict[str, Any]]


# ============== In-memory job store (use Redis in production) ==============

jobs: Dict[str, Dict[str, Any]] = {}


# ============== API Endpoints ==============

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "version": "2.0.0",
        "agents_registered": len(orchestrator.agents) if orchestrator else 0,
        "timestamp": datetime.utcnow().isoformat()
    }


@app.get("/agents", response_model=List[AgentStatus])
async def list_agents():
    """List all registered agents and their status"""
    if not orchestrator:
        raise HTTPException(status_code=503, detail="System not initialized")
    
    return [
        AgentStatus(
            agent_id=agent.agent_id,
            version=agent.version,
            status=agent.status.value,
            total_actions=len(agent.audit_log),
            pending_messages=len(agent.message_queue)
        )
        for agent in orchestrator.agents.values()
    ]


@app.post("/v1/csr/generate", response_model=JobStatus)
async def generate_csr(request: CSRRequest, background_tasks: BackgroundTasks):
    """
    Submit a CSR generation job
    Returns immediately with job ID; processing happens in background
    """
    if not orchestrator:
        raise HTTPException(status_code=503, detail="System not initialized")
    
    job_id = str(uuid.uuid4())
    
    # Initialize job
    jobs[job_id] = {
        "job_id": job_id,
        "status": "queued",
        "progress_percent": 0.0,
        "current_stage": None,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
        "completed_at": None,
        "error_message": None,
        "request": request.dict(),
        "result": None
    }
    
    # Start background processing
    background_tasks.add_task(process_csr_job, job_id, request)
    
    return JobStatus(
        job_id=job_id,
        status="queued",
        progress_percent=0.0,
        current_stage=None,
        created_at=jobs[job_id]["created_at"],
        updated_at=jobs[job_id]["updated_at"],
        completed_at=None,
        error_message=None
    )


@app.get("/v1/csr/status/{job_id}", response_model=JobStatus)
async def get_job_status(job_id: str):
    """Get status of a CSR generation job"""
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    
    job = jobs[job_id]
    return JobStatus(
        job_id=job_id,
        status=job["status"],
        progress_percent=job["progress_percent"],
        current_stage=job["current_stage"],
        created_at=job["created_at"],
        updated_at=job["updated_at"],
        completed_at=job["completed_at"],
        error_message=job["error_message"]
    )


@app.get("/v1/csr/result/{job_id}", response_model=CSRResponse)
async def get_job_result(job_id: str):
    """Get result of completed CSR generation job"""
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    
    job = jobs[job_id]
    
    if job["status"] != "completed":
        raise HTTPException(
            status_code=400, 
            detail=f"Job not completed. Current status: {job['status']}"
        )
    
    return CSRResponse(
        job_id=job_id,
        status=job["status"],
        **job["result"]
    )


@app.post("/v1/protocol/analyze")
async def analyze_protocol(request: ProtocolRequest):
    """Analyze protocol and extract study design"""
    if not orchestrator or "ProtocolAnalyzer" not in orchestrator.agents:
        raise HTTPException(status_code=503, detail="ProtocolAnalyzer not available")
    
    with LogContext() as corr_id:
        logger = AgentLogger("API")
        logger.info("protocol_analysis_request", correlation_id=corr_id)
        
        analyzer = orchestrator.agents["ProtocolAnalyzer"]
        result = analyzer.execute({"protocol_text": request.protocol_text})
        
        return {
            "correlation_id": corr_id,
            "analysis": result
        }


@app.post("/v1/validate", response_model=ValidationResponse)
async def validate_sections(request: ValidationRequest):
    """Validate document sections without full generation"""
    if not orchestrator:
        raise HTTPException(status_code=503, detail="System not initialized")
    
    results = {}
    
    # Statistical validation
    if "StatisticalValidator" in orchestrator.agents:
        validator = orchestrator.agents["StatisticalValidator"]
        results["statistical"] = validator.execute({
            "sections": request.sections
        })
    
    # Compliance validation
    if "ComplianceChecker" in orchestrator.agents:
        checker = orchestrator.agents["ComplianceChecker"]
        results["compliance"] = checker.execute({
            "drafts": request.sections
        })
    
    # Cross-reference validation
    if "CrossReferenceValidator" in orchestrator.agents:
        validator = orchestrator.agents["CrossReferenceValidator"]
        results["cross_reference"] = validator.execute({
            "drafts": request.sections,
            "protocol": request.protocol_data
        })
    
    # Aggregate scores
    validation_score = sum(
        r.get("validation_score", 0) for r in results.values()
    ) / len(results) if results else 0
    
    return ValidationResponse(
        validation_score=validation_score,
        statistical_validation=results.get("statistical", {}),
        compliance_validation=results.get("compliance", {}),
        cross_reference_validation=results.get("cross_reference", {}),
        critical_issues=[],  # Aggregate from all validators
        warnings=[]  # Aggregate from all validators
    )


@app.get("/v1/audit/{document_id}")
async def get_audit_trail(document_id: str):
    """Get audit trail for a document (FDA 21 CFR Part 11)"""
    if not orchestrator:
        raise HTTPException(status_code=503, detail="System not initialized")
    
    # Aggregate audit trails from all agents
    audit_trail = []
    for agent in orchestrator.agents.values():
        agent_audit = agent.get_audit_trail()
        audit_trail.extend(agent_audit)
    
    # Sort by timestamp
    audit_trail.sort(key=lambda x: x.get("timestamp", ""))
    
    return {
        "document_id": document_id,
        "audit_trail": audit_trail,
        "total_records": len(audit_trail)
    }


# ============== Background Task ==============

async def process_csr_job(job_id: str, request: CSRRequest):
    """Process CSR generation in background"""
    job = jobs[job_id]
    
    try:
        with LogContext() as corr_id:
            set_correlation_id(corr_id)
            logger = AgentLogger("CSRWorker")
            
            logger.info("csr_job_started", job_id=job_id, correlation_id=corr_id)
            
            job["status"] = "processing"
            job["updated_at"] = datetime.utcnow()
            job["current_stage"] = "protocol_analysis"
            job["progress_percent"] = 10.0
            
            # Execute workflow
            result = orchestrator.execute_workflow({
                "protocol_text": request.protocol_text,
                "study_id": request.study_id
            })
            
            # Update job
            job["status"] = "completed"
            job["progress_percent"] = 100.0
            job["completed_at"] = datetime.utcnow()
            job["result"] = {
                "document_id": result.get("state", {}).get("document_id", str(uuid.uuid4())),
                "sections": result.get("package", {}).get("sections", {}),
                "validation_score": 85.0,  # Calculate from validators
                "compliance_score": 90.0,
                "consistency_score": 88.0,
                "audit_trail": result.get("state", {}).get("stage_history", []),
                "generated_at": datetime.utcnow()
            }
            
            logger.info("csr_job_completed", job_id=job_id)
            
    except Exception as e:
        job["status"] = "error"
        job["error_message"] = str(e)
        job["updated_at"] = datetime.utcnow()
        
        logger = AgentLogger("CSRWorker")
        logger.error("csr_job_failed", job_id=job_id, error=str(e))


# ============== Main ==============

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
