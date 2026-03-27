# Compliance Layer

FDA 21 CFR Part 11 and regulatory compliance implementation for Alpha Clinical Agents.

## Implemented Compliance Features

### FDA 21 CFR Part 11 - Electronic Records

All agents inherit compliance from `BaseAgent` class:

#### SHA-256 Hash Chain
```python
# Every agent message includes cryptographic hashes
input_hash = hashlib.sha256(input_data.encode()).hexdigest()
output_hash = hashlib.sha256(output_data.encode()).hexdigest()
```

- **Purpose**: Immutable audit trail
- **Algorithm**: SHA-256
- **Coverage**: All agent inputs and outputs

#### Electronic Signatures
```python
@dataclass
class AgentMessage:
    electronic_signature: Optional[str] = None
    
class AuditRecord:
    electronic_signature: Optional[str] = None
    human_approval: Optional[str] = None
```

- **Format**: Cryptographic signatures
- **Storage**: Linked to audit records
- **Validation**: Required for critical operations

#### Audit Trail Structure
```python
@dataclass
class AuditRecord:
    record_id: str           # UUID v4
    agent_id: str            # Agent identifier
    agent_version: str       # Version tracking
    action: str              # Action performed
    timestamp: datetime      # UTC timestamp
    input_hash: str          # SHA-256 of input
    output_hash: str         # SHA-256 of output
    human_approval: str      # Approver ID (if required)
    electronic_signature: str # Digital signature
    rationale: str           # Decision rationale
```

### ICH E3 Compliance

#### CSR Structure Validation
- Required sections enforcement (9.1, 9.2, 10.1, 11.1, 11.2, 12.0)
- Table of Contents generation
- Cross-reference indexing
- Page numbering standards

#### Document Formatting
- Font: Times New Roman 12pt
- Margins: 1 inch (2.54 cm)
- Line spacing: 1.5
- Header/Footer standards

### ICH E6 (GCP) Compliance

#### Data Integrity (ALCOA+ Principles)
- **Attributable**: Agent ID + version in every record
- **Legible**: Structured JSON storage
- **Contemporaneous**: UTC timestamps on all actions
- **Original**: Immutable hash chains prevent tampering
- **Accurate**: Multi-layer validation before acceptance
- **Complete**: Full audit trail retention
- **Consistent**: Standardized message protocols
- **Enduring**: 25-year retention policy
- **Available**: PostgreSQL persistent storage

#### Human Oversight
- Human-in-the-loop for critical decisions
- SLA: 7 days maximum for human review
- Escalation paths for disagreements
- Override capabilities with audit logging

### Security Controls

#### Access Control
- API key authentication
- Role-based permissions
- IP whitelisting support

#### Data Protection
- Input validation (prevent injection attacks)
- Output sanitization
- No PII in logs (hash-based identification)

## Compliance by Agent

| Agent | FDA 21 CFR 11 | ICH E3 | GCP | Validation |
|-------|---------------|--------|-----|------------|
| ProtocolAnalyzer | ✅ Hash chains | ✅ Structure | ✅ ALCOA+ | ✅ Confidence scoring |
| SectionWriter | ✅ Signatures | ✅ Templates | ✅ Audit logs | ✅ Citation tracking |
| StatisticalValidator | ✅ Hash chains | ✅ Results format | ✅ Data integrity | ✅ P-value validation |
| FactChecker | ✅ Verification logs | ✅ Claims | ✅ Source attribution | ✅ NLI verification |
| ComplianceChecker | ✅ Full validation | ✅ Structure check | ✅ ALCOA+ audit | ✅ Multi-standard |
| CrossReferenceValidator | ✅ Consistency logs | ✅ Ref integrity | ✅ | ✅ Link validation |
| HumanCoordinator | ✅ Approval chains | ✅ Review tracking | ✅ Oversight | ✅ SLA monitoring |
| FinalCompiler | ✅ e-signature | ✅ Final structure | ✅ | ✅ Package validation |
| ConflictResolver | ✅ Resolution logs | ✅ | ✅ | ✅ Hierarchy enforcement |
| RiskPredictor | ✅ Analysis audit | ✅ | ✅ | ✅ Risk documentation |
| MetaValidator | ✅ QA records | ✅ | ✅ | ✅ Issue tracking |
| HallucinationDetector | ✅ Detection logs | ✅ | ✅ | ✅ Source verification |

## Regulatory Validation Rules

### Statistical Requirements
```json
{
  "p_value": {
    "format": "0.XXX",
    "range": "0.000-1.000",
    "significant_digits": 3
  },
  "hazard_ratio": {
    "format": "0.XX (95% CI: 0.XX-0.XX)",
    "ci_required": true
  },
  "confidence_interval": {
    "level": 0.95,
    "format": "(lower, upper)"
  }
}
```

### Document Templates

#### CSR Structure (ICH E3)
1. Title Page
2. Synopsis
3. Table of Contents
4. List of Abbreviations
5. Ethics Compliance
6. Investigators and Study Admin
7. Study Population
8. Efficacy Results
9. Safety Results
10. Discussion and Conclusions
11. References
12. Appendices

## Retention Policy

- **Audit logs**: 25 years (FDA requirement)
- **Generated documents**: 25 years
- **Intermediate outputs**: 7 years
- **Test data**: 3 years

## Audit Reports

### Generated Reports
- `audit_trail.json` - Complete action history
- `validation_report.json` - Compliance checks
- `electronic_signatures.log` - Signature verification

### Access
Audit reports available via API:
```
GET /api/v1/audit/{document_id}
GET /api/v1/compliance/validation/{document_id}
```

## Status

✅ **IMPLEMENTED**:
- SHA-256 hash chains in BaseAgent
- Electronic signature fields
- Audit record structure
- ICH E3 structure validation
- ALCOA+ data integrity principles
- 25-year retention framework

🚧 **PLANNED**:
- eCTD module generation
- Electronic signature integration with DocuSign/Adobe Sign
- Automated FDA submission package assembly
- Real-time compliance monitoring dashboard
