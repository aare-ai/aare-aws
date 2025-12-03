# aare.ai

Formal verification for LLM outputs. Mathematical proof that your AI complies with your rules.

## What is aare.ai?

aare.ai is a verification layer that sits between your LLM and production. It uses the [Z3 theorem prover](https://github.com/Z3Prover/z3) to mathematically verify that every LLM output satisfies your compliance constraints before it reaches customers.

```
LLM Output → aare.ai → Verified Output + Proof Certificate
                ↑
         Your Compliance Rules
         (JSON ontologies)
```

**Not pattern matching. Not regex. Mathematical proof.**

## Why?

LLM agents are in production today, answering customers, processing claims, drafting contracts. Every response is a compliance risk. Prompt engineering fails silently. Output filters miss edge cases.

aare.ai checks 100% of LLM outputs against your exact compliance requirements. If it passes, it's delivered. If it fails, it's blocked—with a proof certificate that pinpoints the exact rule violated.

## Quick Start

### Install

```bash
git clone https://github.com/aare-ai/aare-aws
cd aare-aws
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Deploy to AWS

```bash
npm install -g serverless
npm install
serverless deploy --stage prod
```

### Call the API

```bash
curl -X POST https://your-api.execute-api.region.amazonaws.com/prod/verify \
  -H "Content-Type: application/json" \
  -H "x-api-key: your-key" \
  -d '{
    "ontology": "mortgage-compliance-v1",
    "llm_output": "Based on your DTI of 45% and credit score of 680, I recommend approving this $400k mortgage with escrow waiver."
  }'
```

### Response

```json
{
  "verified": false,
  "violations": [
    {
      "constraint_id": "ATR_QM_DTI",
      "category": "ATR/QM",
      "description": "Debt-to-income ratio requirements",
      "error_message": "DTI exceeds 43% without sufficient compensating factors",
      "formula": "(dti ≤ 43) ∨ (compensating_factors ≥ 2)",
      "citation": "12 CFR § 1026.43(c)"
    }
  ],
  "parsed_data": {
    "dti": 45,
    "credit_score": 680,
    "escrow_waived": true,
    "compensating_factors": 0
  },
  "proof": {
    "method": "Z3 SMT Solver",
    "version": "4.12.1",
    "results": [...]
  }
}
```

## How It Works

1. **Parse**: Extract structured data from unstructured LLM output (free text, JSON, bullet points)
2. **Load Ontology**: Your compliance rules defined as formal constraints
3. **Verify**: Z3 theorem prover checks if extracted data satisfies all constraints
4. **Prove**: Returns mathematical proof of compliance or exact violation details

## Ontologies

Ontologies define your verification rules. Each constraint specifies:
- Variables to extract from LLM output
- Logical formula that must be satisfied
- Error message and regulatory citation

### Example: Mortgage Compliance

```json
{
  "name": "mortgage-compliance-v1",
  "version": "1.0.0",
  "constraints": [
    {
      "id": "ATR_QM_DTI",
      "category": "ATR/QM",
      "description": "Debt-to-income ratio requirements",
      "formula_readable": "(dti ≤ 43) ∨ (compensating_factors ≥ 2)",
      "formula": {
        "or": [
          {"<=": ["dti", 43]},
          {">=": ["compensating_factors", 2]}
        ]
      },
      "variables": [
        {"name": "dti", "type": "real"},
        {"name": "compensating_factors", "type": "int"}
      ],
      "error_message": "DTI exceeds 43% without sufficient compensating factors",
      "citation": "12 CFR § 1026.43(c)"
    }
  ],
  "extractors": {
    "dti": {
      "type": "float",
      "pattern": "dti[:\\s~]*(\\d+(?:\\.\\d+)?)"
    }
  }
}
```

### Formula Syntax

Constraints use structured JSON formulas that compile directly to Z3 expressions:

| Operator | Syntax | Example |
|----------|--------|---------|
| And | `{"and": [...]}` | `{"and": [{"<=": ["x", 10]}, {">=": ["y", 0]}]}` |
| Or | `{"or": [...]}` | `{"or": [{"==": ["approved", true]}, {">=": ["score", 700]}]}` |
| Not | `{"not": {...}}` | `{"not": {"==": ["has_phi", true]}}` |
| Implies | `{"implies": [A, B]}` | `{"implies": [{"==": ["is_denial", true]}, {"==": ["has_reason", true]}]}` |
| If-Then-Else | `{"ite": [cond, then, else]}` | `{"ite": [{">": ["score", 700]}, "approved", "denied"]}` |
| Equals | `{"==": [a, b]}` | `{"==": ["status", true]}` |
| Less/Greater | `{"<=": [a, b]}` | `{"<=": ["dti", 43]}` |
| Min/Max | `{"min": [a, b]}` | `{"<=": ["fee", {"min": [500, {"*": ["loan", 0.03]}]}]}` |
| Arithmetic | `{"+": [a, b]}` | `{"<=": [{"+": ["fee", "points"]}, 1000]}` |
| Variable Ref | `{"var": "name"}` | `{"<=": ["amount", {"var": "limit"}]}` |

### Example Ontologies

| Ontology | Domain | Constraints | Description |
|----------|--------|-------------|-------------|
| `hipaa-v1` | Healthcare | 52 | HIPAA Privacy & Security Rule (PHI, de-identification, access control) |
| `mortgage-compliance-v1` | Lending | 5 | ATR/QM, HOEPA, UDAAP, Reg B |
| `medical-safety-v1` | Healthcare | 5 | Drug interactions, dosing limits, referrals |
| `financial-compliance-v1` | Finance | 5 | Investment advice, disclaimers, suitability |
| `data-privacy-v1` | Security | 5 | PII, credentials, internal URLs |
| `customer-service-v1` | Support | 5 | Discount limits, delivery promises, fault admission |
| `fair-lending-v1` | Lending | 5 | DTI limits, credit score requirements |
| `trading-compliance-v1` | Trading | 5 | Position limits, sector exposure |
| `content-policy-v1` | Content | 5 | Real people, religious content, medical advice |
| `contract-compliance-v1` | Legal | 5 | Usury limits, late fee caps |

## Project Structure

```
aare-aws/
├── handlers/
│   └── handler.py           # Lambda entry point
├── ontologies/              # Compliance rule definitions (100 constraints)
│   ├── hipaa-v1.json        # 52 HIPAA constraints
│   ├── mortgage-compliance-v1.json
│   ├── medical-safety-v1.json
│   └── ...
├── tests/
│   ├── test_verifier.py
│   ├── test_formula_compiler.py
│   └── test_parser.py
├── serverless.yml           # AWS deployment config
└── requirements.txt
```

> **Note:** The core verification engine (LLMParser, SMTVerifier, FormulaCompiler, OntologyLoader)
> is provided by the [aare-core](https://github.com/aare-ai/aare-core) package.

## API Reference

### POST /verify

Verify LLM output against an ontology.

**Request:**
```json
{
  "llm_output": "string",
  "ontology": "string"
}
```

**Response:**
```json
{
  "verified": true,
  "violations": [],
  "warnings": ["Variables defaulted (not found in input): ['variable_name']"],
  "parsed_data": {},
  "ontology": {
    "name": "string",
    "version": "string",
    "constraints_checked": 5
  },
  "proof": {
    "method": "Z3 SMT Solver",
    "version": "4.12.1",
    "results": []
  },
  "verification_id": "uuid",
  "execution_time_ms": 47,
  "timestamp": "2024-01-15T10:30:00Z"
}
```

**Note:** The `warnings` field appears when variables couldn't be extracted from the LLM output and were defaulted. This helps auditors understand verification scope.

## Writing Custom Ontologies

1. Define constraints with variables, formulas, and error messages
2. Define extractors to pull data from unstructured text
3. Upload to S3 bucket or include in deployment
4. Call API with your ontology name

See `ontologies/` for examples.

## Development

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run tests
pytest tests/ -v

# Deploy to dev
serverless deploy --stage dev
```

## Architecture

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                               AWS Cloud                                      │
│                                                                              │
│  ┌──────────────┐     ┌──────────────────┐     ┌───────────────────────┐    │
│  │              │     │                  │     │                       │    │
│  │ API Gateway  │────▶│  Lambda          │◀───▶│  S3                   │    │
│  │              │     │  (aare-ai-prod)  │     │  (ontologies bucket)  │    │
│  │ - API Key    │     │                  │     │                       │    │
│  │ - Rate Limit │     │  ┌────────────┐  │     │  - hipaa-v1.json      │    │
│  │ - CORS       │     │  │ aare-core  │  │     │  - mortgage-v1.json   │    │
│  │              │     │  │            │  │     │  - custom ontologies  │    │
│  └──────────────┘     │  │ ┌────────┐ │  │     │                       │    │
│         │             │  │ │   Z3   │ │  │     └───────────────────────┘    │
│         │             │  │ │ Solver │ │  │                                  │
│         ▼             │  │ └────────┘ │  │     ┌───────────────────────┐    │
│  ┌──────────────┐     │  └────────────┘  │     │                       │    │
│  │   CloudWatch │◀────│                  │────▶│  DynamoDB             │    │
│  │   Logs       │     └──────────────────┘     │  - verification logs  │    │
│  └──────────────┘                              │  - proof certificates │    │
│                                                │  - audit trail        │    │
│                                                └───────────────────────┘    │
└──────────────────────────────────────────────────────────────────────────────┘

                               │
                               │ HTTPS + API Key
                               ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│                            Your Application                                  │
│                                                                              │
│   LLM Output ──▶ aare.ai /verify ──▶ Verified Output + Proof Certificate    │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
```

### Components

| Component | Service | Purpose |
|-----------|---------|---------|
| **API Gateway** | Amazon API Gateway | REST API with API key auth, rate limiting, CORS |
| **Compute** | AWS Lambda | Runs verification engine (Python 3.11, 2GB RAM) |
| **Verification** | aare-core + Z3 | SMT solver for formal verification |
| **Ontologies** | Amazon S3 | Stores compliance rule definitions |
| **Logs** | CloudWatch | Request/response logging, metrics |
| **Audit Trail** | DynamoDB | Persistent storage for proof certificates |

### Data Flow

1. **Request** → API Gateway validates API key and rate limits
2. **Lambda** → Loads ontology from S3 (or bundled), parses LLM output
3. **Z3 Solver** → Verifies constraints, generates proof certificate
4. **Response** → Returns verification result with proof
5. **Audit** → Stores verification record in DynamoDB

### Current Deployment

- **Region**: us-west-2
- **Endpoint**: `https://api.aare.ai/verify` (via custom domain)
- **Memory**: 2048 MB
- **Timeout**: 30 seconds
- **Concurrency**: Default Lambda limits

## Requirements

- Python 3.11+
- Node.js 18+ (for Serverless Framework)
- AWS Account
- AWS CLI configured

## License

MIT

## Links

- Website: [aare.ai](https://aare.ai)
- Email: info@aare.ai
