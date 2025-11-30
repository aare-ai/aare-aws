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

LLM agents are in production today—answering customers, processing claims, drafting contracts. Every response is a compliance risk. Prompt engineering fails silently. Output filters miss edge cases.

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

### Included Ontologies

| Ontology | Domain | Constraints |
|----------|--------|-------------|
| `mortgage-compliance-v1` | Lending | ATR/QM, HOEPA, UDAAP, Reg B |
| `medical-safety-v1` | Healthcare | Drug interactions, dosing limits, referrals |
| `financial-compliance-v1` | Finance | Investment advice, disclaimers, suitability |
| `data-privacy-v1` | Security | PII, credentials, internal URLs |
| `customer-service-v1` | Support | Discount limits, delivery promises, fault admission |
| `fair-lending-v1` | Lending | DTI limits, credit score requirements |
| `trading-compliance-v1` | Trading | Position limits, sector exposure |
| `content-policy-v1` | Content | Real people, religious content, medical advice |
| `contract-compliance-v1` | Legal | Usury limits, late fee caps |

## Project Structure

```
aare-aws/
├── handlers/
│   ├── handler.py          # Lambda entry point
│   ├── llm_parser.py        # Extract data from LLM output
│   ├── smt_verifier.py      # Z3 constraint verification
│   └── ontology_loader.py   # Load ontologies from S3
├── ontologies/              # Compliance rule definitions
│   ├── mortgage-compliance-v1.json
│   ├── medical-safety-v1.json
│   └── ...
├── tests/
│   ├── test_verifier.py
│   └── test_parser.py
├── serverless.yml           # AWS deployment config
└── requirements.txt
```

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

- **Runtime**: Python 3.11 on AWS Lambda
- **Solver**: Z3 SMT Solver
- **Storage**: S3 for ontologies
- **API**: API Gateway with API key authentication
- **Framework**: Serverless Framework

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
