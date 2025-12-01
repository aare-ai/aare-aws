"""
Ontology loader for aare.ai
Loads verification rules from S3 or returns default if S3 fails
"""
import json
import boto3
from functools import lru_cache

class OntologyLoader:
    def __init__(self, bucket='aare-ai-ontologies-prod'):
        self.s3 = boto3.client('s3')
        self.bucket = bucket
        
    @lru_cache(maxsize=10)
    def load(self, ontology_name):
        """Load ontology from S3 or return default"""
        try:
            # Try to load from S3
            response = self.s3.get_object(
                Bucket=self.bucket,
                Key=f'{ontology_name}.json'
            )
            ontology = json.loads(response['Body'].read())
            return self._validate_ontology(ontology)
        except Exception as e:
            print(f"Failed to load from S3: {str(e)}, using default ontology")
            # Return default mortgage compliance ontology
            return self._get_default_ontology()
    
    def _validate_ontology(self, ontology):
        """Validate ontology structure"""
        required_fields = ['name', 'version', 'constraints', 'extractors']
        for field in required_fields:
            if field not in ontology:
                raise ValueError(f"Invalid ontology: missing {field}")
        return ontology
    
    def _get_default_ontology(self):
        """Return default mortgage compliance ontology"""
        return {
            "name": "mortgage-compliance-v1",
            "version": "1.0.0",
            "description": "U.S. Mortgage Compliance - Core constraints",
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
                },
                {
                    "id": "HOEPA_HIGH_COST",
                    "category": "HOEPA",
                    "description": "High-cost mortgage counseling requirement",
                    "formula_readable": "(fee_percentage < 8) ∨ counseling_disclosed",
                    "formula": {
                        "or": [
                            {"<": ["fee_percentage", 8]},
                            {"==": ["counseling_disclosed", True]}
                        ]
                    },
                    "variables": [
                        {"name": "fee_percentage", "type": "real"},
                        {"name": "counseling_disclosed", "type": "bool"}
                    ],
                    "error_message": "HOEPA triggered - counseling disclosure required",
                    "citation": "12 CFR § 1026.32"
                },
                {
                    "id": "UDAAP_NO_GUARANTEES",
                    "category": "UDAAP",
                    "description": "Prohibition on guarantee language",
                    "formula_readable": "¬(has_guarantee ∧ has_approval)",
                    "formula": {
                        "not": {
                            "and": [
                                {"==": ["has_guarantee", True]},
                                {"==": ["has_approval", True]}
                            ]
                        }
                    },
                    "variables": [
                        {"name": "has_guarantee", "type": "bool"},
                        {"name": "has_approval", "type": "bool"}
                    ],
                    "error_message": "Cannot guarantee approval",
                    "citation": "12 CFR § 1036.3"
                },
                {
                    "id": "HPML_ESCROW",
                    "category": "Escrow",
                    "description": "Escrow requirements based on FICO",
                    "formula_readable": "(credit_score ≥ 620) ∨ ¬escrow_waived",
                    "formula": {
                        "or": [
                            {">=": ["credit_score", 620]},
                            {"==": ["escrow_waived", False]}
                        ]
                    },
                    "variables": [
                        {"name": "credit_score", "type": "int"},
                        {"name": "escrow_waived", "type": "bool"}
                    ],
                    "error_message": "Cannot waive escrow with FICO < 620",
                    "citation": "12 CFR § 1026.35(b)"
                },
                {
                    "id": "REG_B_ADVERSE",
                    "category": "Regulation B",
                    "description": "Adverse action disclosure requirements",
                    "formula_readable": "is_denial → has_specific_reason",
                    "formula": {
                        "implies": [
                            {"==": ["is_denial", True]},
                            {"==": ["has_specific_reason", True]}
                        ]
                    },
                    "variables": [
                        {"name": "is_denial", "type": "bool"},
                        {"name": "has_specific_reason", "type": "bool"}
                    ],
                    "error_message": "Must disclose specific denial reason",
                    "citation": "12 CFR § 1002.9"
                }
            ],
            "extractors": {
                "dti": {
                    "type": "float",
                    "pattern": "dti[:\\s~]*(\\d+(?:\\.\\d+)?)"
                },
                "credit_score": {
                    "type": "int",
                    "pattern": "(?:fico|credit score)[:\\s]*(\\d{3})"
                },
                "fees": {
                    "type": "money",
                    "pattern": "\\$?([\\d,]+)k?\\s*(?:fees?|costs?)"
                },
                "loan_amount": {
                    "type": "money",
                    "pattern": "\\$?([\\d,]+)k?\\s*(?:loan|mortgage)"
                },
                "has_guarantee": {
                    "type": "boolean",
                    "keywords": ["guaranteed", "100%", "definitely"]
                },
                "has_approval": {
                    "type": "boolean",
                    "keywords": ["approved", "approve"]
                },
                "counseling_disclosed": {
                    "type": "boolean",
                    "keywords": ["counseling"]
                },
                "escrow_waived": {
                    "type": "boolean",
                    "keywords": ["escrow waived", "waive escrow", "skip escrow"]
                },
                "is_denial": {
                    "type": "boolean",
                    "keywords": ["denied", "cannot approve"]
                },
                "has_specific_reason": {
                    "type": "boolean",
                    "keywords": ["credit", "income", "dti", "debt", "score"]
                }
            }
        }
    
    def list_available(self):
        """List all available ontologies"""
        try:
            response = self.s3.list_objects_v2(Bucket=self.bucket)
            return [obj['Key'].replace('.json', '') 
                    for obj in response.get('Contents', [])]
        except:
            return ['mortgage-compliance-v1']