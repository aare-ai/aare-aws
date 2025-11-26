# aare.ai

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python](https://img.shields.io/badge/python-v3.11+-blue.svg)](https://www.python.org/)
[![Z3](https://img.shields.io/badge/Z3-SMT_Solver-blue)](https://github.com/Z3Prover/z3)

Post-generation formal verification for LLMs using SMT solving. Ensure LLM outputs satisfy your constraints with mathematical proofs, not probabilities.

## What is this?

aare.ai is a verification layer that sits between your LLM and production systems. It uses [Z3 theorem prover](https://github.com/Z3Prover/z3) to formally verify that LLM outputs satisfy your business rules before they reach production.

```
LLM Output → aare.ai → Verified Output + Proof
                ↑
          Enterprise Rules
          (OWL/JSON ontologies)
```

## Quick Start

### Local Development

```bash
# Clone and setup
git clone https://github.com/aare-ai/aare-aws
cd aare-aws
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt

# Run tests
pytest tests/

# Run locally (requires AWS credentials)
python -m src.local_server
```

### Deploy to AWS

```bash
# Install Serverless Framework
npm install

# Deploy to AWS
serverless deploy --stage dev

# Get your API endpoint
serverless info --stage dev
```

## How it Works

1. **Define Constraints**: Write your business rules as ontologies
2. **Call API**: Send LLM output to aare.ai
3. **Get Proof**: Receive verification result with mathematical proof

### Example: Verify a Loan Decision

```python
import requests

response = requests.post(
    "https://your-api.execute-api.region.amazonaws.com/dev/verify",
    headers={"x-api-key": "your-key"},
    json={
        "content": {
            "decision": "approve",
            "amount": 50000,
            "dti_ratio": 0.38,
            "credit_score": 720
        },
        "ontology": "fair-lending-v1",
        "rules": ["max_dti_ratio", "min_credit_score"]
    }
)

# Returns:
# {
#   "verified": true,
#   "violations": [],
#   "proof_certificate": "QmX4...",
#   "execution_time_ms": 47
# }

## Writing Ontologies

Ontologies define your verification rules. You can write them in JSON or OWL format.

### JSON Example

```json
{
  "name": "fair-lending-v1",
  "version": "1.0.0",
  "rules": [
    {
      "name": "max_dti_ratio",
      "expression": "debt_to_income_ratio <= 0.43",
      "variables": ["debt_to_income_ratio"],
      "severity": "error"
    },
    {
      "name": "min_credit_score", 
      "expression": "credit_score >= 620",
      "variables": ["credit_score"],
      "severity": "error"
    }
  ]
}
```

### Supported Constraint Types

- **Numeric**: `x <= 100`, `y >= 0`, `z == 42`
- **Boolean**: `a and b`, `x or y`, `not z`
- **Relational**: `forall x in list: x > 0`
- **Aggregate**: `sum(values) < threshold`

## Architecture

This is the AWS serverless implementation. Key components:

- `src/core/verifier.py` - SMT verification engine using Z3
- `src/core/parser.py` - LLM output parser
- `src/handlers/` - Lambda function handlers
- `ontologies/` - Pre-built verification rules

## API Reference

### POST /verify
Verify LLM output against constraints

```json
Request:
{
  "content": {...},        // LLM output to verify
  "ontology": "string",    // Ontology name
  "rules": ["string"],     // Specific rules (optional)
  "timeout": 1000         // Timeout in ms (optional)
}

Response:
{
  "verified": true,
  "violations": [],
  "proof_certificate": "hash",
  "execution_time_ms": 47
}
```

## Development

```bash
# Setup
python -m venv venv
source venv/bin/activate
pip install -r requirements-dev.txt

# Run tests
pytest tests/ -v

# Linting
black src/
pylint src/
```

## Contributing

We need help with:
- Ontologies for specific regulations (GDPR, HIPAA, SOX, etc.)
- Performance optimizations for complex constraints
- Additional language bindings (Node.js, Go, Rust)
- Documentation and examples

See [CONTRIBUTING.md](CONTRIBUTING.md) for details.

## Performance

Current benchmarks on AWS Lambda (1024MB):
- Simple numeric constraints: ~20ms
- Complex relational constraints: ~100ms
- Ontology parsing cached after first use

## Limitations

- SMT solving can be NP-complete for complex constraints
- Natural language parsing is imperfect
- Some constraints may timeout on complex inputs

## License

MIT - See [LICENSE](LICENSE)

## Related Projects

- [Z3 Theorem Prover](https://github.com/Z3Prover/z3)
- [OpenAI Evals](https://github.com/openai/evals)
- [Guardrails AI](https://github.com/guardrails-ai/guardrails)

## Contact

- Issues: [GitHub Issues](https://github.com/aare-ai/aare-aws/issues)
- Email: contact@aare.ai
- Website: [aare.ai](https://aare.ai)
