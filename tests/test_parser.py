"""
Tests for output parser module
"""

import pytest
from src.core.parser import OutputParser, ParsedClaim


class TestOutputParser:
    """Test cases for OutputParser"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.parser = OutputParser()
    
    def test_parse_dict_simple(self):
        """Test parsing simple dictionary"""
        content = {
            "decision": "approve",
            "amount": 50000,
            "rate": 5.5
        }
        
        result = self.parser.parse(content)
        
        assert result["decision"] == "approve"
        assert result["amount"] == 50000
        assert result["rate"] == 5.5
    
    def test_parse_dict_nested(self):
        """Test parsing nested dictionary"""
        content = {
            "loan": {
                "amount": 100000,
                "term": 30
            },
            "borrower": {
                "credit_score": 750,
                "income": 120000
            }
        }
        
        result = self.parser.parse(content)
        
        assert result["loan.amount"] == 100000
        assert result["loan.term"] == 30
        assert result["borrower.credit_score"] == 750
        assert result["borrower.income"] == 120000
    
    def test_parse_json_string(self):
        """Test parsing JSON string"""
        content = '{"decision": "denied", "reason": "low credit score"}'
        
        result = self.parser.parse(content)
        
        assert result["decision"] == "denied"
        assert result["reason"] == "low credit score"
    
    def test_parse_text_key_value(self):
        """Test parsing text with key-value pairs"""
        content = """
        Decision: Approved
        Loan Amount: $75,000
        Interest Rate: 4.5%
        Credit Score: 720
        DTI: 0.35
        """
        
        result = self.parser.parse(content)
        
        assert result["decision"] == True  # "Approved" -> True
        assert result["loan_amount"] == 75000
        assert result["interest_rate"] == 0.045  # 4.5% -> 0.045
        assert result["credit_score"] == 720
        assert result["dti"] == 0.35
    
    def test_parse_boolean_values(self):
        """Test boolean value parsing"""
        content = {
            "approved": "yes",
            "denied": "no",
            "verified": True,
            "failed": "false"
        }
        
        result = self.parser.parse(content)
        
        assert result["approved"] == True
        assert result["denied"] == False
        assert result["verified"] == True
        assert result["failed"] == False
    
    def test_parse_percentage_values(self):
        """Test percentage parsing"""
        content = {
            "rate": "5.5%",
            "dti": "43%",
            "ltv": "80%"
        }
        
        result = self.parser.parse(content)
        
        assert result["rate"] == 0.055
        assert result["dti"] == 0.43
        assert result["ltv"] == 0.80
    
    def test_parse_currency_values(self):
        """Test currency parsing"""
        content = {
            "amount": "$100,000",
            "income": "85000",
            "payment": "$1,250.50"
        }
        
        result = self.parser.parse(content)
        
        assert result["amount"] == 100000
        assert result["income"] == 85000
        assert result["payment"] == 1250.50
    
    def test_normalize_keys(self):
        """Test key normalization"""
        content = {
            "Loan Amount": 50000,
            "debt-to-income ratio": 0.35,
            "CREDIT_SCORE": 700,
            "  interest rate  ": 4.5
        }
        
        result = self.parser.parse(content)
        
        assert "loan_amount" in result
        assert "debtoincome_ratio" in result  # Special chars removed
        assert "credit_score" in result
        assert "interest_rate" in result
    
    def test_extract_claims(self):
        """Test claim extraction"""
        parsed_content = {
            "decision": "approve",
            "amount": 50000,
            "rate": 0.045,
            "verified": True
        }
        
        claims = self.parser.extract_claims(parsed_content)
        
        assert len(claims) == 4
        assert all(isinstance(claim, ParsedClaim) for claim in claims)
        
        # Check specific claims
        decision_claim = next(c for c in claims if c.path == "decision")
        assert decision_claim.value == "approve"
        assert decision_claim.type == "string"
        
        amount_claim = next(c for c in claims if c.path == "amount")
        assert amount_claim.value == 50000
        assert amount_claim.type == "integer"
    
    def test_parse_list(self):
        """Test parsing list of items"""
        content = [
            {"id": 1, "status": "approved"},
            {"id": 2, "status": "denied"}
        ]
        
        result = self.parser.parse(content)
        
        assert "items" in result
        assert len(result["items"]) == 2
        assert result["items"][0]["status"] == "approved"
    
    def test_parse_empty_content(self):
        """Test parsing empty content"""
        assert self.parser.parse({}) == {}
        assert self.parser.parse([]) == {"items": []}
        assert "raw_content" in self.parser.parse("")
    
    def test_parse_invalid_json(self):
        """Test parsing invalid JSON falls back to text parsing"""
        content = "This is not JSON but has amount: 5000"
        
        result = self.parser.parse(content)
        
        assert result.get("amount") == 5000 or "raw_content" in result
