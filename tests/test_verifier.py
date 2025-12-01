"""
Tests for SMT verifier
"""

import pytest
import sys
import os

# Add handlers to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from handlers.smt_verifier import SMTVerifier


class TestSMTVerifier:
    """Test cases for SMTVerifier"""

    def setup_method(self):
        """Set up test fixtures"""
        self.verifier = SMTVerifier()
        self.mortgage_ontology = {
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
                }
            ]
        }

    def test_verify_all_passing(self):
        """Test verification with all constraints passing"""
        data = {
            "dti": 40,
            "compensating_factors": 0,
            "has_guarantee": False,
            "has_approval": True
        }

        result = self.verifier.verify(data, self.mortgage_ontology)

        assert result["verified"] == True
        assert len(result["violations"]) == 0

    def test_verify_dti_violation(self):
        """Test verification with DTI violation"""
        data = {
            "dti": 50,  # Exceeds 43%
            "compensating_factors": 0,  # No compensating factors
            "has_guarantee": False,
            "has_approval": True
        }

        result = self.verifier.verify(data, self.mortgage_ontology)

        assert result["verified"] == False
        assert len(result["violations"]) == 1
        assert result["violations"][0]["constraint_id"] == "ATR_QM_DTI"

    def test_verify_dti_with_compensating_factors(self):
        """Test that high DTI passes with compensating factors"""
        data = {
            "dti": 50,  # Exceeds 43%
            "compensating_factors": 2,  # Has compensating factors
            "has_guarantee": False,
            "has_approval": True
        }

        result = self.verifier.verify(data, self.mortgage_ontology)

        assert result["verified"] == True
        assert len(result["violations"]) == 0

    def test_verify_guarantee_violation(self):
        """Test verification with guarantee + approval violation"""
        data = {
            "dti": 40,
            "compensating_factors": 0,
            "has_guarantee": True,  # Guarantee language
            "has_approval": True    # With approval
        }

        result = self.verifier.verify(data, self.mortgage_ontology)

        assert result["verified"] == False
        violations = [v["constraint_id"] for v in result["violations"]]
        assert "UDAAP_NO_GUARANTEES" in violations

    def test_verify_missing_variables(self):
        """Test verification handles missing variables gracefully"""
        data = {
            "dti": 40
            # Missing other variables
        }

        result = self.verifier.verify(data, self.mortgage_ontology)

        # Should complete without error
        assert "verified" in result
        assert "violations" in result

    def test_missing_variables_warning(self):
        """Test that missing variables produce warnings for auditors"""
        data = {
            "dti": 40
            # Missing: compensating_factors, has_guarantee, has_approval
        }

        result = self.verifier.verify(data, self.mortgage_ontology)

        # Should include warnings about missing variables
        assert "warnings" in result
        assert len(result["warnings"]) > 0
        # Check that warnings mention the missing variables
        warning_text = result["warnings"][0]
        assert "compensating_factors" in warning_text
        assert "has_guarantee" in warning_text
        assert "has_approval" in warning_text

    def test_execution_time_included(self):
        """Test that execution time is included in result"""
        data = {
            "dti": 40,
            "compensating_factors": 0,
            "has_guarantee": False,
            "has_approval": True
        }

        result = self.verifier.verify(data, self.mortgage_ontology)

        assert "execution_time_ms" in result
        assert isinstance(result["execution_time_ms"], int)

    def test_proof_certificate_included(self):
        """Test that proof certificate is included in result"""
        data = {
            "dti": 40,
            "compensating_factors": 0,
            "has_guarantee": False,
            "has_approval": True
        }

        result = self.verifier.verify(data, self.mortgage_ontology)

        assert "proof" in result
        assert result["proof"]["method"] == "Z3 SMT Solver"


class TestMedicalOntology:
    """Test cases for medical safety ontology"""

    def setup_method(self):
        self.verifier = SMTVerifier()
        self.medical_ontology = {
            "name": "medical-safety-v1",
            "version": "1.0.0",
            "constraints": [
                {
                    "id": "EGFR_METFORMIN",
                    "category": "Kidney Function",
                    "description": "Metformin contraindication based on kidney function",
                    "formula_readable": "(egfr >= 45) ∨ ¬recommends_metformin",
                    "formula": {
                        "or": [
                            {">=": ["egfr", 45]},
                            {"==": ["recommends_metformin", False]}
                        ]
                    },
                    "variables": [
                        {"name": "egfr", "type": "int"},
                        {"name": "recommends_metformin", "type": "bool"}
                    ],
                    "error_message": "Metformin contraindicated when eGFR < 45 ml/min",
                    "citation": "FDA Metformin Label Update 2016"
                },
                {
                    "id": "DRUG_INTERACTION",
                    "category": "Drug Safety",
                    "description": "Check for contraindicated drug combinations",
                    "formula_readable": "¬(ace_inhibitor ∧ potassium_sparing)",
                    "formula": {
                        "not": {
                            "and": [
                                {"==": ["ace_inhibitor", True]},
                                {"==": ["potassium_sparing", True]}
                            ]
                        }
                    },
                    "variables": [
                        {"name": "ace_inhibitor", "type": "bool"},
                        {"name": "potassium_sparing", "type": "bool"}
                    ],
                    "error_message": "ACE inhibitor with potassium-sparing diuretic risk",
                    "citation": "Drug Interaction Database"
                }
            ]
        }

    def test_metformin_safe_egfr(self):
        """Test metformin recommendation with safe eGFR"""
        data = {
            "egfr": 60,
            "recommends_metformin": True,
            "ace_inhibitor": False,
            "potassium_sparing": False
        }

        result = self.verifier.verify(data, self.medical_ontology)

        assert result["verified"] == True

    def test_metformin_low_egfr_violation(self):
        """Test metformin recommendation with low eGFR"""
        data = {
            "egfr": 30,  # Below 45
            "recommends_metformin": True,  # Recommending anyway
            "ace_inhibitor": False,
            "potassium_sparing": False
        }

        result = self.verifier.verify(data, self.medical_ontology)

        assert result["verified"] == False
        assert any(v["constraint_id"] == "EGFR_METFORMIN" for v in result["violations"])

    def test_metformin_low_egfr_no_recommendation(self):
        """Test no metformin recommendation with low eGFR is safe"""
        data = {
            "egfr": 30,  # Below 45
            "recommends_metformin": False,  # Not recommending
            "ace_inhibitor": False,
            "potassium_sparing": False
        }

        result = self.verifier.verify(data, self.medical_ontology)

        assert result["verified"] == True

    def test_drug_interaction_violation(self):
        """Test drug interaction detection"""
        data = {
            "egfr": 60,
            "recommends_metformin": False,
            "ace_inhibitor": True,  # ACE inhibitor
            "potassium_sparing": True  # With potassium-sparing diuretic
        }

        result = self.verifier.verify(data, self.medical_ontology)

        assert result["verified"] == False
        assert any(v["constraint_id"] == "DRUG_INTERACTION" for v in result["violations"])
