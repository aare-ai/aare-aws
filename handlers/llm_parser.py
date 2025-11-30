"""
LLM output parser for aare.ai
Extracts structured data from unstructured LLM text
"""
import re
from typing import Dict, Any

class LLMParser:
    def parse(self, text: str, ontology: Dict) -> Dict[str, Any]:
        """Parse LLM output using ontology-defined extractors"""
        extracted = {}
        text_lower = text.lower()
        extractors = ontology.get('extractors', {})
        
        for field_name, extractor in extractors.items():
            value = self._extract_field(text, text_lower, extractor)
            if value is not None:
                extracted[field_name] = value
        
        # Calculate derived fields
        extracted = self._calculate_derived_fields(extracted, text_lower)
        
        return extracted
    
    def _extract_field(self, text, text_lower, extractor):
        """Extract a single field based on extractor configuration"""
        extractor_type = extractor.get('type')

        if extractor_type == 'boolean':
            # Check for keyword presence
            keywords = extractor.get('keywords', [])
            negation_words = extractor.get('negation_words', [])
            # Some keywords should check for negation, others shouldn't
            check_negation = extractor.get('check_negation', True)

            # Check if any keyword is present
            keyword_found = False
            for kw in keywords:
                if kw in text_lower:
                    keyword_found = True

                    # Only check negation for recommendation-type keywords
                    if check_negation:
                        # Check for negation context around the keyword (before AND after)
                        kw_pos = text_lower.find(kw)
                        # Look at surrounding context (30 chars before AND 30 chars after)
                        context_start = max(0, kw_pos - 30)
                        context_end = min(len(text_lower), kw_pos + len(kw) + 30)
                        context = text_lower[context_start:context_end]

                        # Check for negation patterns that indicate NOT recommending
                        negation_patterns = ['not ', 'no ', 'avoid', 'contraindicated', 'don\'t',
                                            'cannot', 'should not', 'must not', 'never ',
                                            'prohibited', ' is not ', ' not a ']
                        negation_patterns.extend(negation_words)

                        if any(neg in context for neg in negation_patterns):
                            return False

            return keyword_found
        
        elif extractor_type in ['int', 'float', 'money', 'percentage']:
            # Use regex pattern
            pattern = extractor.get('pattern')
            if not pattern:
                return None
            
            match = re.search(pattern, text_lower)
            if match:
                return self._parse_numeric(match, text, extractor_type)
        
        elif extractor_type == 'string':
            # Extract string value
            pattern = extractor.get('pattern')
            if pattern:
                match = re.search(pattern, text_lower)
                if match:
                    return match.group(1) if match.groups() else match.group(0)
        
        return None
    
    def _parse_numeric(self, match, original_text, value_type):
        """Parse numeric values from regex match"""
        value_str = match.group(1).replace(',', '')
        
        if value_type == 'int':
            return int(value_str)
        
        elif value_type == 'float':
            return float(value_str)
        
        elif value_type == 'percentage':
            return float(value_str)
        
        elif value_type == 'money':
            # Check for k/m/b suffixes
            match_text = original_text[match.start():match.end()].lower()
            multiplier = 1
            if 'k' in match_text:
                multiplier = 1000
            elif 'm' in match_text:
                multiplier = 1000000
            elif 'b' in match_text:
                multiplier = 1000000000
            
            return float(value_str) * multiplier
        
        return None
    
    def _calculate_derived_fields(self, extracted, text_lower):
        """Calculate fields that depend on other fields"""
        # Fee percentage
        if 'fees' in extracted and 'loan_amount' in extracted:
            if extracted['loan_amount'] > 0:
                extracted['fee_percentage'] = (extracted['fees'] / extracted['loan_amount']) * 100
        
        # Compensating factors (simple heuristic)
        if 'compensating' in text_lower:
            if 'two' in text_lower or 'multiple' in text_lower:
                extracted['compensating_factors'] = 2
            elif 'one' in text_lower:
                extracted['compensating_factors'] = 1
            else:
                extracted['compensating_factors'] = 1
        else:
            extracted['compensating_factors'] = 0
        
        return extracted
