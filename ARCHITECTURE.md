# aare.ai AWS - Technical Documentation

**GitHub**: [github.com/aare-ai](https://www.github.com/aare-ai) | [github.com/aare-ai/aare-aws](https://www.github.com/aare-ai/aare-aws)

## Overview

**aare.ai** is a formal verification platform that provides mathematical proof of LLM (Large Language Model) compliance. It uses the Z3 theorem prover to mathematically verify that every LLM response satisfies compliance constraints before reaching customers.

### Key Features

- **Mathematical Verification**: Z3 SMT solver provides formal proofs (not regex or pattern matching)
- **Multi-Domain Compliance**: 10+ ontologies covering HIPAA, lending, trading, data privacy, etc.
- **Proof Certificates**: SHA256 hashed certificates for audit trails
- **100+ Constraints**: Comprehensive rule coverage across regulatory domains
- **Serverless Architecture**: AWS Lambda with API Gateway and DynamoDB

---

## Architecture Diagram

```
+------------------------------------------------------------------------+
|                              aare.ai                                    |
|                   LLM Compliance Verification Platform                  |
+------------------------------------------------------------------------+

                            +---------------------+
                            |      CLIENTS        |
                            | (LLM Applications)  |
                            +----------+----------+
                                       |
                                       | POST /verify
                                       | x-api-key header
                                       v
+------------------------------------------------------------------------+
| EXTERNAL SERVICES                                                       |
|                                                                         |
|  +------------------------------------------------------------------+  |
|  |                      API Gateway (REST)                          |  |
|  |                      api.aare.ai/verify                          |  |
|  |                                                                  |  |
|  |  - API Key Authentication (aare-ai-key-{stage})                  |  |
|  |  - Rate Limiting: 200 req/s, 500 burst, 100k/day                 |  |
|  |  - CORS: aare.ai, localhost:3000/8000                            |  |
|  +------------------------------+-----------------------------------+  |
|                                 |                                      |
+------------------------------------------------------------------------+
                                  |
                                  v
+------------------------------------------------------------------------+
| AWS                                                                     |
|                                                                         |
|  +------------------------------------------------------------------+  |
|  |                     Lambda Function                              |  |
|  |                     (Python 3.11, 2GB, 30s)                      |  |
|  |                                                                  |  |
|  |  +------------------------------------------------------------+  |  |
|  |  |                   aare-core Engine                         |  |  |
|  |  |                                                            |  |  |
|  |  |  1. Parse Request (llm_output, ontology name)              |  |  |
|  |  |  2. Load Ontology from S3                                  |  |  |
|  |  |  3. Extract Variables (LLMParser - regex/keywords)         |  |  |
|  |  |  4. Compile Constraints (FormulaCompiler -> Z3)            |  |  |
|  |  |  5. Run Verification (SMTVerifier - Z3 Solver)             |  |  |
|  |  |  6. Generate Proof Certificate (SHA256)                    |  |  |
|  |  |  7. Store Audit Record in DynamoDB                         |  |  |
|  |  |  8. Return Verification Result                             |  |  |
|  |  +------------------------------------------------------------+  |  |
|  |                                                                  |  |
|  |  +------------------+                                            |  |
|  |  |   Z3 SMT Solver  |  <-- Mathematical constraint verification  |  |
|  |  |   (v4.12.1)      |      Formal proofs, not pattern matching   |  |
|  |  +------------------+                                            |  |
|  +------------------------------------------------------------------+  |
|                                                                         |
|         +---------------+---------------+---------------+               |
|         |               |               |               |               |
|         v               v               v               v               |
|  +-------------+  +-------------+  +-------------+  +-------------+     |
|  |     S3      |  |  DynamoDB   |  | CloudWatch  |  |     ECR     |     |
|  |             |  |             |  |             |  |             |     |
|  | Ontologies  |  | Audit Trail |  |   Logs &    |  |   Docker    |     |
|  | Bucket      |  |   Table     |  |  Metrics    |  |   Images    |     |
|  |             |  |             |  |             |  |             |     |
|  | -mortgage   |  | -verify_id  |  | -Requests   |  | -Lambda     |     |
|  | -hipaa      |  | -timestamp  |  | -Latency    |  |  with Z3    |     |
|  | -trading    |  | -violations |  | -Errors     |  |             |     |
|  | -medical    |  | -cert_hash  |  |             |  |             |     |
|  | -privacy    |  | -TTL 90 day |  |             |  |             |     |
|  | -financial  |  |             |  |             |  |             |     |
|  | +7 more...  |  | GSI: ontol- |  |             |  |             |     |
|  |             |  | ogy+time    |  |             |  |             |     |
|  +-------------+  +-------------+  +-------------+  +-------------+     |
|                                                                         |
+------------------------------------------------------------------------+

                                  |
                                  v
                      +---------------------+
                      |      RESPONSE       |
                      +---------------------+
                      | {                   |
                      |   verified: bool,   |
                      |   violations: [...],|
                      |   parsed_data: {},  |
                      |   proof: {          |
                      |     method: "Z3",   |
                      |     results: [...]  |
                      |   },                |
                      |   certificate_hash, |
                      |   verification_id   |
                      | }                   |
                      +---------------------+
```

---

## Technology Stack

### Backend

| Layer | Technology | Version |
|-------|------------|---------|
| **Runtime** | Python | 3.11 |
| **Framework** | Serverless Framework | 3.x |
| **Cloud Provider** | AWS | us-west-2 |
| **Verification Engine** | Z3 SMT Solver | 4.12.1 |
| **Core Library** | aare-core | >=0.2.5 |

### Key Dependencies

| Package | Purpose |
|---------|---------|
| **aare-core** | Verification engine (OntologyLoader, LLMParser, SMTVerifier) |
| **z3-solver** | Satisfiability Modulo Theories solver |
| **boto3** | AWS SDK for Python |
| **aws-lambda-powertools** | Lambda utilities and logging |
| **pydantic** | Data validation |
| **rdflib / owlready2** | OWL/RDF ontology processing |

---

## AWS Services

| Service | Purpose | Configuration |
|---------|---------|---------------|
| **Lambda** | Verification engine | Python 3.11, 2GB RAM, 30s timeout |
| **API Gateway** | REST API endpoint | POST /verify, API key auth, rate limiting |
| **DynamoDB** | Audit trail storage | aare-ai-verifications-{stage}, 90-day TTL, GSI |
| **S3** | Ontology storage | aare-ai-ontologies-{stage}, 10+ JSON files |
| **CloudWatch** | Logging & monitoring | Request logs, latency metrics, errors |
| **ECR** | Container registry | Docker images with Z3 precompiled |
| **IAM** | Access control | Lambda role with S3 read, DynamoDB write |

---

## API Endpoint

### POST /verify

**Authentication**: API Key (x-api-key header)

**Request**:
```json
{
  "llm_output": "The recommended loan has a DTI of 38% and...",
  "ontology": "mortgage-compliance-v1"
}
```

**Response**:
```json
{
  "verified": true,
  "violations": [],
  "parsed_data": {
    "dti_ratio": 0.38,
    "has_guarantee_language": false
  },
  "ontology": {
    "name": "mortgage-compliance-v1",
    "version": "1.0.0",
    "constraints_checked": 8
  },
  "proof": {
    "method": "Z3 SMT Solver",
    "version": "4.12.1",
    "results": [...]
  },
  "certificate_hash": "SHA256:abc123...",
  "verification_id": "uuid-v4",
  "execution_time_ms": 145,
  "timestamp": "2024-01-15T10:30:00Z"
}
```

**Rate Limits**:
- 200 requests/second
- 500 burst capacity
- 100,000 requests/day quota

---

## Ontologies (Compliance Domains)

| Ontology | Domain | Constraints | Key Rules |
|----------|--------|-------------|-----------|
| **mortgage-compliance-v1** | Lending | 8 | ATR/QM (DTI ≤43%), HOEPA, UDAAP, Escrow |
| **hipaa-v1** | Healthcare | 52 | PHI detection, de-identification, access control |
| **medical-safety-v1** | Healthcare | 5 | Drug dosing, interactions, kidney function |
| **financial-compliance-v1** | Finance | 6 | No specific securities, disclaimers required |
| **data-privacy-v1** | Security | 5 | No PII, no credentials, no internal URLs |
| **fair-lending-v1** | Lending | 5 | Credit limits, DTI caps, down payment |
| **customer-service-v1** | Support | 5 | Discount limits, delivery promises |
| **trading-compliance-v1** | Trading | 5 | Position sizing, sector exposure |
| **contract-compliance-v1** | Legal | Multiple | Usury limits, late fee caps |
| **content-policy-v1** | Content | Multiple | Medical advice, religious content |

---

## Verification Flow

```
+-------------------+     +-------------------+     +-------------------+
|   LLM Output      | --> |   LLM Parser      | --> |  Extracted Data   |
|   (raw text)      |     |  (regex/keywords) |     |  (variables)      |
+-------------------+     +-------------------+     +-------------------+
                                                            |
                                                            v
+-------------------+     +-------------------+     +-------------------+
|   Verification    | <-- |  Formula Compiler | <-- |   Ontology        |
|   Result          |     |  (JSON -> Z3)     |     |   (constraints)   |
+-------------------+     +-------------------+     +-------------------+
        |
        v
+-------------------+     +-------------------+
|   Z3 SMT Solver   | --> |  Proof/Violation  |
|   (formal proof)  |     |  (with citations) |
+-------------------+     +-------------------+
```

---

## Database Schema

### DynamoDB Table: `aare-ai-verifications-{stage}`

**Primary Key**: `verification_id` (String)

**Attributes**:
```javascript
{
  verification_id: "uuid-v4",           // Primary key
  timestamp: "ISO8601",                 // Sort key in GSI
  ontology_name: "string",              // GSI partition key
  verified: boolean,
  violation_count: number,
  violations: [                         // Array of violations
    {
      constraint_id: "string",
      category: "string",
      description: "string",
      error_message: "string",
      citation: "string"
    }
  ],
  input_hash: "SHA256",                 // Hash of llm_output
  certificate_hash: "SHA256",           // Hash of full verification
  execution_time_ms: number,
  ttl: number                           // Auto-delete after 90 days
}
```

**Global Secondary Index**: `ontology_name` + `timestamp`
- Query verifications by ontology and time range

---

## Deployment

### Using Serverless Framework

```bash
# Install dependencies
npm install
pip install -r requirements.txt

# Deploy to dev
serverless deploy --stage dev

# Deploy to production
serverless deploy --stage prod
```

### Using Docker (ECR)

```bash
# Build Docker image with Z3
./deploy.sh

# This script:
# 1. Builds Dockerfile.z3 with precompiled Z3
# 2. Tags and pushes to ECR
# 3. Updates Lambda function with new image
# 4. Tests the API endpoint
```

---

## Security

### API Security
- API Key authentication required
- Rate limiting prevents abuse
- CORS restricted to aare.ai domains and localhost

### Data Security
- SHA256 hashing for verification certificates
- Audit trail stored in DynamoDB
- 90-day automatic TTL on records
- Input hashing for traceability

### Verification Security
- Mathematical proofs (not pattern matching)
- Z3 SMT Solver for formal verification
- Proof certificates included in responses
- Citation references for audit compliance

---

## Environment Configuration

```bash
# AWS
AWS_REGION=us-west-2
AWS_PROFILE=default

# Resources (auto-generated by stage)
DYNAMODB_TABLE=aare-ai-verifications-{stage}
S3_ONTOLOGY_BUCKET=aare-ai-ontologies-{stage}

# Security
API_KEY=your-api-key-here

# Monitoring
CLOUDWATCH_NAMESPACE=aare-ai
LOG_LEVEL=INFO
METRICS_ENABLED=true
```

---

## Monitoring

### CloudWatch Metrics
- Request count and latency
- Verification success/failure rate
- Violation counts by ontology
- Lambda execution time and memory

### Logging
- All verification requests logged
- Violations recorded with full context
- Error stack traces for debugging

---

## Testing

```bash
# Run all tests
pytest tests/

# Test verification logic
pytest tests/test_verifier.py

# Test LLM output parsing
pytest tests/test_parser.py

# Test formula compilation
pytest tests/test_formula_compiler.py
```

### Test Coverage
- All constraint types (AND, OR, NOT, IMPLIES)
- Variable extraction (float, int, boolean)
- Missing variable handling
- Violation detection
- Proof certificate generation

---

## Use Cases

1. **LLM Guardrails**: Verify AI responses before reaching customers
2. **Compliance Validation**: Mathematical proof of regulatory compliance
3. **Risk Mitigation**: Block non-compliant outputs with citations
4. **Audit Support**: Proof certificates for compliance auditors
5. **Multi-Domain**: Finance, healthcare, lending, trading, legal
