"""
Tests for SMT verifier module
"""

import pytest
from src.core.verifier import SMTVerifier, Constraint, ConstraintType, Violation


class TestSMTVerifier:
    """Test cases for SMTVerifier"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.ontology = {
            "name": "test-ontology",
            "version": "1.0.0",
            "rules": [
                {
                    "name": "max_amount",
                    "expression": "amount <= 100000",
                    "variables": ["amount"],
                    "severity": "error",
                    "description": "Amount must not exceed 100000"
                },
                {
                    "name": "min_credit_score",
                    "expression": "credit_score >= 600",
                    "variables": ["credit_score"],
                    "severity": "error",
                    "description": "Credit score must be at least 600"
                },
                {
                    "name": "dti_ratio",
                    "expression": "debt_to_income_ratio <= 0.43",
                    "variables": ["debt_to_income_ratio"],
                    "severity": "error",
                    "description": "DTI must not exceed 43%"
                }
            ]
        }
        self.verifier = SMTVerifier(self.ontology)
    
    def test_initialization(self):
        """Test verifier initialization"""
        assert len(self.verifier.constraints) == 3
        assert all(isinstance(c, Constraint) for c in self.verifier.constraints)
    
    def test_verify_all_passing(self):
        """Test verification with all constraints passing"""
        data = {
            "amount": 50000,
            "credit_score": 750,
            "debt_to_income_ratio": 0.35
        }
        
        result = self.verifier.verify(data)
        
        assert result["verified"] == True
        assert len(result["violations"]) == 0
        assert result["constraints_checked"] == 3
    
    def test_verify_with_violation(self):
        """Test verification with constraint violations"""
        data = {
            "amount": 150000,  # Exceeds max
            "credit_score": 550,  # Below min
            "debt_to_income_ratio": 0.35
        }
        
        result = self.verifier.verify(data)
        
        assert result["verified"] == False
        assert len(result["violations"]) == 2
        
        # Check specific violations
        violations = result["violations"]
        constraint_names = [v["constraint"] for v in violations]
        assert "max_amount" in constraint_names
        assert "min_credit_score" in constraint_names
    
    def test_verify_missing_variables(self):
        """Test verification with missing required variables"""
        data = {
            "amount": 50000
            # Missing credit_score and debt_to_income_ratio
        }
        
        result = self.verifier.verify(data)
        
        # Should handle missing variables gracefully
        assert "verified" in result
        assert "violations" in result
    
    def test_set_active_rules(self):
        """Test setting specific rules to be active"""
        self.verifier.set_active_rules(["max_amount"])
        
        data = {
            "amount": 50000,
            "credit_score": 550,  # Would violate if checked
            "debt_to_income_ratio": 0.5  # Would violate if checked
        }
        
        result = self.verifier.verify(data)
        
        # Only max_amount should be checked
        assert result["constraints_checked"] == 1
        assert result["verified"] == True
    
    def test_numeric_constraint_parsing(self):
        """Test parsing of numeric constraints"""
        data = {
            "amount": 75000,
            "credit_score": 700,
            "debt_to_income_ratio": 0.40
        }
        
        result = self.verifier.verify(data)
        
        assert result["verified"] == True
    
    def test_timeout_handling(self):
        """Test timeout parameter"""
        data = {
            "amount": 50000,
            "credit_score": 750,
            "debt_to_income_ratio": 0.35
        }
        
        # Should complete quickly
        result = self.verifier.verify(data, timeout_ms=100)
        
        assert "execution_time_ms" in result
        assert result["execution_time_ms"] < 100
    
    def test_constraint_type_detection(self):
        """Test detection of constraint types"""
        rules = [
            {"expression": "x <= 100", "expected_type": ConstraintType.NUMERIC_RANGE},
            {"expression": "a and b", "expected_type": ConstraintType.BOOLEAN_LOGIC},
            {"expression": "forall x: x > 0", "expected_type": ConstraintType.RELATIONAL},
            {"expression": "sum(values) < 1000", "expected_type": ConstraintType.AGGREGATE}
        ]
        
        for rule in rules:
            constraint_type = self.verifier._determine_constraint_type(rule)
            assert constraint_type == rule["expected_type"]
    
    def test_flatten_dict(self):
        """Test dictionary flattening"""
        nested = {
            "level1": {
                "level2": {
                    "value": 123
                }
            },
            "simple": "value"
        }
        
        flat = self.verifier._flatten_dict(nested)
        
        assert flat["level1.level2.value"] == 123
        assert flat["simple"] == "value"
    
    def test_violation_details(self):
        """Test that violations contain proper details"""
        data = {
            "amount": 150000,
            "credit_score": 750,
            "debt_to_income_ratio": 0.35
        }
        
        result = self.verifier.verify(data)
        
        assert result["verified"] == False
        violation = result["violations"][0]
        
        assert "constraint" in violation
        assert "description" in violation
        assert "severity" in violation
        assert "expected" in violation
        assert "actual" in violation
