"""
Output parser for extracting structured claims from LLM outputs
Converts various output formats into verifiable assertions
"""

import json
import re
from typing import Dict, Any, List, Union
from dataclasses import dataclass, asdict
import logging

logger = logging.getLogger(__name__)


@dataclass
class ParsedClaim:
    """Represents a single parsed claim from LLM output"""
    path: str
    value: Any
    type: str
    confidence: float = 1.0
    
    def to_dict(self) -> Dict:
        return asdict(self)


class OutputParser:
    """
    Parses LLM outputs into structured format for verification
    Supports JSON, key-value pairs, and natural language extraction
    """
    
    def __init__(self):
        self.type_patterns = {
            'numeric': re.compile(r'^-?\d+\.?\d*$'),
            'boolean': re.compile(r'^(true|false|yes|no|approved|denied)$', re.IGNORECASE),
            'date': re.compile(r'\d{4}-\d{2}-\d{2}'),
            'percentage': re.compile(r'^(\d+\.?\d*)%$'),
            'currency': re.compile(r'^\$?[\d,]+\.?\d*$')
        }
    
    def parse(self, content: Union[str, Dict, List]) -> Dict[str, Any]:
        """
        Main parsing method - handles multiple input formats
        
        Args:
            content: LLM output in various formats
            
        Returns:
            Structured dictionary of claims
        """
        if isinstance(content, dict):
            return self._parse_dict(content)
        elif isinstance(content, list):
            return self._parse_list(content)
        elif isinstance(content, str):
            # Try JSON first
            try:
                json_content = json.loads(content)
                return self.parse(json_content)
            except json.JSONDecodeError:
                # Fall back to text parsing
                return self._parse_text(content)
        else:
            raise ValueError(f"Unsupported content type: {type(content)}")
    
    def _parse_dict(self, content: Dict) -> Dict[str, Any]:
        """Parse dictionary format (most common for structured outputs)"""
        result = {}
        
        for key, value in content.items():
            # Normalize key (remove spaces, lowercase)
            normalized_key = self._normalize_key(key)
            
            # Recursively parse nested structures
            if isinstance(value, dict):
                nested = self._parse_dict(value)
                for nested_key, nested_value in nested.items():
                    result[f"{normalized_key}.{nested_key}"] = nested_value
            elif isinstance(value, list):
                result[normalized_key] = self._parse_list_values(value)
            else:
                result[normalized_key] = self._parse_value(value)
        
        return result
    
    def _parse_list(self, content: List) -> Dict[str, Any]:
        """Parse list format"""
        result = {"items": []}
        
        for i, item in enumerate(content):
            if isinstance(item, dict):
                parsed_item = self._parse_dict(item)
                result["items"].append(parsed_item)
            else:
                result["items"].append(self._parse_value(item))
        
        return result
    
    def _parse_text(self, content: str) -> Dict[str, Any]:
        """Parse natural language text for key-value pairs"""
        result = {}
        
        # Look for common patterns
        patterns = [
            # Key: Value
            re.compile(r'([A-Za-z_][A-Za-z0-9_\s]*?):\s*([^\n]+)'),
            # Key = Value
            re.compile(r'([A-Za-z_][A-Za-z0-9_\s]*?)\s*=\s*([^\n]+)'),
            # "Key" is Value
            re.compile(r'"([^"]+)"\s+is\s+([^\n]+)'),
            # Key -> Value
            re.compile(r'([A-Za-z_][A-Za-z0-9_\s]*?)\s*->\s*([^\n]+)')
        ]
        
        for pattern in patterns:
            matches = pattern.findall(content)
            for key, value in matches:
                normalized_key = self._normalize_key(key.strip())
                result[normalized_key] = self._parse_value(value.strip())
        
        # Extract specific decision patterns
        decision_patterns = [
            (r'(approved|approved)', 'decision', 'approved'),
            (r'(denied|rejected)', 'decision', 'denied'),
            (r'loan amount[:\s]+\$?([\d,]+)', 'loan_amount', None),
            (r'interest rate[:\s]+([\d.]+)%?', 'interest_rate', None),
            (r'credit score[:\s]+(\d+)', 'credit_score', None),
            (r'DTI[:\s]+([\d.]+)%?', 'debt_to_income_ratio', None),
            (r'debt.to.income[:\s]+([\d.]+)%?', 'debt_to_income_ratio', None)
        ]
        
        for pattern, key, default_value in decision_patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                value = default_value if default_value else match.group(1)
                result[key] = self._parse_value(value)
        
        # If no structured data found, return the raw content
        if not result:
            result['raw_content'] = content
        
        return result
    
    def _parse_list_values(self, values: List) -> List[Any]:
        """Parse list of values"""
        return [self._parse_value(v) for v in values]
    
    def _parse_value(self, value: Any) -> Any:
        """Parse individual value and detect type"""
        if value is None:
            return None
        
        # Already parsed types
        if isinstance(value, (bool, int, float)):
            return value
        
        # String parsing
        if isinstance(value, str):
            value = value.strip()
            
            # Boolean
            if value.lower() in ['true', 'yes', 'approved']:
                return True
            elif value.lower() in ['false', 'no', 'denied', 'rejected']:
                return False
            
            # Percentage
            match = self.type_patterns['percentage'].match(value)
            if match:
                return float(match.group(1)) / 100
            
            # Currency
            match = self.type_patterns['currency'].match(value)
            if match:
                return float(value.replace('$', '').replace(',', ''))
            
            # Numeric
            if self.type_patterns['numeric'].match(value):
                if '.' in value:
                    return float(value)
                return int(value)
            
            # Date (keep as string for now)
            if self.type_patterns['date'].match(value):
                return value
            
            # Default to string
            return value
        
        return value
    
    def _normalize_key(self, key: str) -> str:
        """Normalize keys to consistent format"""
        # Remove special characters, convert to snake_case
        key = re.sub(r'[^\w\s]', '', key)
        key = key.strip().lower()
        key = re.sub(r'\s+', '_', key)
        return key
    
    def extract_claims(self, parsed_content: Dict[str, Any]) -> List[ParsedClaim]:
        """Extract individual claims from parsed content"""
        claims = []
        
        for path, value in self._flatten_dict(parsed_content).items():
            claim_type = self._detect_type(value)
            claim = ParsedClaim(
                path=path,
                value=value,
                type=claim_type
            )
            claims.append(claim)
        
        return claims
    
    def _flatten_dict(self, d: Dict, parent_key: str = '', sep: str = '.') -> Dict:
        """Flatten nested dictionary"""
        items = []
        for k, v in d.items():
            new_key = f"{parent_key}{sep}{k}" if parent_key else k
            if isinstance(v, dict):
                items.extend(self._flatten_dict(v, new_key, sep=sep).items())
            else:
                items.append((new_key, v))
        return dict(items)
    
    def _detect_type(self, value: Any) -> str:
        """Detect the type of a value"""
        if isinstance(value, bool):
            return 'boolean'
        elif isinstance(value, int):
            return 'integer'
        elif isinstance(value, float):
            return 'numeric'
        elif isinstance(value, str):
            if self.type_patterns['date'].match(value):
                return 'date'
            return 'string'
        elif isinstance(value, list):
            return 'array'
        else:
            return 'unknown'
