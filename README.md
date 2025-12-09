# aare-aws

AWS Lambda deployment for [aare-core](https://github.com/aare-ai/aare-core) - formal verification for LLM outputs.

This repository provides serverless infrastructure to deploy aare-core on AWS using Lambda, API Gateway, S3, and DynamoDB.

## Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+ (for Serverless Framework)
- AWS Account with CLI configured

### Install

```bash
git clone https://github.com/aare-ai/aare-aws
cd aare-aws
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Deploy

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
    "version": "4.12.1"
  }
}
```

## Project Structure

```
aare-aws/
├── handlers/
│   └── handler.py           # Lambda entry point
├── ontologies/              # Compliance rule definitions
│   ├── hipaa-v1.json
│   ├── mortgage-compliance-v1.json
│   └── ...
├── tests/
│   ├── test_verifier.py
│   ├── test_formula_compiler.py
│   └── test_parser.py
├── serverless.yml           # AWS deployment config
└── requirements.txt
```

## Architecture

```
┌───────────────────────────────────────────────────────────────────────────┐
│                              AWS Cloud                                    │
│                                                                           │
│  ┌──────────────┐     ┌──────────────────┐     ┌───────────────────────┐  │
│  │              │     │                  │     │                       │  │
│  │ API Gateway  │────▶│  Lambda          │◀───▶│  S3                   │  │
│  │              │     │  (aare-ai-prod)  │     │  (ontologies bucket)  │  │
│  │ - API Key    │     │                  │     │                       │  │
│  │ - Rate Limit │     │  ┌────────────┐  │     │  - hipaa-v1.json      │  │
│  │ - CORS       │     │  │ aare-core  │  │     │  - mortgage-v1.json   │  │
│  │              │     │  │            │  │     │  - custom ontologies  │  │
│  └──────────────┘     │  │ ┌────────┐ │  │     │                       │  │
│         │             │  │ │   Z3   │ │  │     └───────────────────────┘  │
│         │             │  │ │ Solver │ │  │                                │
│         ▼             │  │ └────────┘ │  │     ┌───────────────────────┐  │
│  ┌──────────────┐     │  └────────────┘  │     │                       │  │
│  │   CloudWatch │◀────│                  │────▶│  DynamoDB             │  │
│  │   Logs       │     └──────────────────┘     │  - verification logs  │  │
│  └──────────────┘                              │  - proof certificates │  │
│                                                │  - audit trail        │  │
│                                                └───────────────────────┘  │
└───────────────────────────────────────────────────────────────────────────┘

                              │
                              │ HTTPS + API Key
                              ▼
┌───────────────────────────────────────────────────────────────────────────┐
│                           Your Application                                │
│                                                                           │
│  LLM Output ──▶ aare.ai /verify ──▶ Verified Output + Proof Certificate  │
│                                                                           │
└───────────────────────────────────────────────────────────────────────────┘
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

### Deployment Configuration

- **Region**: us-west-2
- **Endpoint**: `https://api.aare.ai/verify` (via custom domain)
- **Memory**: 2048 MB
- **Timeout**: 30 seconds
- **Concurrency**: Default Lambda limits

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

## Related Projects

- [aare-core](https://github.com/aare-ai/aare-core) - Core verification engine (ontologies, formula syntax, API docs)
- [aare-azure](https://github.com/aare-ai/aare-azure) - Azure Functions deployment
- [aare-gcp](https://github.com/aare-ai/aare-gcp) - Google Cloud Functions deployment

## License

MIT

## Links

- Website: [aare.ai](https://aare.ai)
- Documentation: [aare.ai/docs](https://aare.ai/docs.html)
- Email: info@aare.ai
