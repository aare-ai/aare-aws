"""
Tests for LLM output parser
"""

import pytest
import sys
import os

# Add handlers to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from handlers.llm_parser import LLMParser


class TestLLMParser:
    """Test cases for LLMParser"""

    def setup_method(self):
        """Set up test fixtures"""
        self.parser = LLMParser()
        self.mortgage_ontology = {
            "name": "mortgage-compliance-v1",
            "version": "1.0.0",
            "extractors": {
                "dti": {
                    "type": "float",
                    "pattern": "dti[:\\s~]*(\\d+(?:\\.\\d+)?)"
                },
                "credit_score": {
                    "type": "int",
                    "pattern": "(?:fico|credit score)[:\\s]*(\\d{3})"
                },
                "has_guarantee": {
                    "type": "boolean",
                    "keywords": ["guaranteed", "100%", "definitely"]
                },
                "has_approval": {
                    "type": "boolean",
                    "keywords": ["approved", "approve"]
                }
            }
        }

    def test_parse_dti(self):
        """Test DTI extraction"""
        text = "Based on your DTI of 45% and income, I recommend waiting."
        result = self.parser.parse(text, self.mortgage_ontology)
        assert result["dti"] == 45

    def test_parse_credit_score(self):
        """Test credit score extraction"""
        text = "Your FICO score is 720, which qualifies for prime rates."
        result = self.parser.parse(text, self.mortgage_ontology)
        assert result["credit_score"] == 720

    def test_parse_guarantee_keyword(self):
        """Test guarantee keyword detection"""
        text = "You are guaranteed to be approved for this loan."
        result = self.parser.parse(text, self.mortgage_ontology)
        assert result["has_guarantee"] == True
        assert result["has_approval"] == True

    def test_compensating_factors_none(self):
        """Test default compensating factors"""
        text = "Your DTI: 45% requires careful review."
        result = self.parser.parse(text, self.mortgage_ontology)
        assert result["compensating_factors"] == 0

    def test_compensating_factors_detected(self):
        """Test compensating factors detection"""
        text = "Your DTI: 45% but you have two compensating factors."
        result = self.parser.parse(text, self.mortgage_ontology)
        assert result["compensating_factors"] == 2


class TestMedicalParser:
    """Test cases for medical ontology parsing"""

    def setup_method(self):
        self.parser = LLMParser()
        self.medical_ontology = {
            "name": "medical-safety-v1",
            "version": "1.0.0",
            "extractors": {
                "egfr": {
                    "type": "int",
                    "pattern": "egfr[:\\s=]*(\\d+)"
                },
                "recommends_metformin": {
                    "type": "boolean",
                    "keywords": ["metformin", "glucophage"],
                    "check_negation": True
                },
                "nephro_referral": {
                    "type": "boolean",
                    "keywords": ["nephrology", "nephrologist"],
                    "check_negation": False
                }
            }
        }

    def test_parse_egfr(self):
        """Test eGFR extraction"""
        text = "Patient's eGFR: 45 ml/min indicates moderate kidney impairment."
        result = self.parser.parse(text, self.medical_ontology)
        assert result["egfr"] == 45

    def test_parse_metformin_recommendation(self):
        """Test metformin recommendation detection"""
        text = "I recommend starting metformin 500mg twice daily."
        result = self.parser.parse(text, self.medical_ontology)
        assert result["recommends_metformin"] == True

    def test_parse_metformin_contraindication(self):
        """Test metformin contraindication detection"""
        text = "Given the low eGFR, metformin is contraindicated."
        result = self.parser.parse(text, self.medical_ontology)
        assert result["recommends_metformin"] == False

    def test_parse_nephrology_referral(self):
        """Test nephrology referral detection"""
        text = "Refer patient to nephrology for evaluation."
        result = self.parser.parse(text, self.medical_ontology)
        assert result["nephro_referral"] == True
