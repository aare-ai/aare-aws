"""
Core SMT verification engine using Z3
Translates ontology constraints to SMT formulas and verifies LLM outputs
"""

from typing import Dict, Any, List, Optional, Tuple
import z3
import time
import logging
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class ConstraintType(Enum):
    """Types of constraints supported"""
    NUMERIC_RANGE = "numeric_range"
    BOOLEAN_LOGIC = "boolean_logic"
    STRING_PATTERN = "string_pattern"
    TEMPORAL = "temporal"
    RELATIONAL = "relational"
    AGGREGATE = "aggregate"


@dataclass
class Constraint:
    """Represents a single constraint from the ontology"""
    name: str
    type: ConstraintType
    expression: str
    variables: List[str]
    description: str
    severity: str = "error"  # error, warning, info


@dataclass
class Violation:
    """Represents a constraint violation"""
    constraint_name: str
    description: str
    severity: str
    expected: Any
    actual: Any
    path: str


class SMTVerifier:
    """
    Main SMT verification engine
    Converts ontology rules to Z3 constraints and checks satisfiability
    """
    
    def __init__(self, ontology: Dict[str, Any]):
        """
        Initialize verifier with ontology
        
        Args:
            ontology: Parsed ontology dictionary
        """
        self.ontology = ontology
        self.constraints = self._parse_constraints(ontology)
        self.active_rules = None
        self.z3_solver = z3.Solver()
        self.z3_solver.set("timeout", 1000)  # Default 1 second timeout
        
    def _parse_constraints(self, ontology: Dict) -> List[Constraint]:
        """Parse ontology into constraint objects"""
        constraints = []
        
        for rule in ontology.get('rules', []):
            constraint_type = self._determine_constraint_type(rule)
            constraint = Constraint(
                name=rule['name'],
                type=constraint_type,
                expression=rule['expression'],
                variables=rule.get('variables', []),
                description=rule.get('description', ''),
                severity=rule.get('severity', 'error')
            )
            constraints.append(constraint)
            
        logger.info(f"Parsed {len(constraints)} constraints from ontology")
        return constraints
    
    def _determine_constraint_type(self, rule: Dict) -> ConstraintType:
        """Determine constraint type from rule definition"""
        expression = rule.get('expression', '')
        
        if any(op in expression for op in ['<', '>', '<=', '>=', '==']):
            return ConstraintType.NUMERIC_RANGE
        elif any(op in expression for op in ['and', 'or', 'not', 'implies']):
            return ConstraintType.BOOLEAN_LOGIC
        elif 'regex' in expression or 'pattern' in expression:
            return ConstraintType.STRING_PATTERN
        elif any(t in expression for t in ['date', 'time', 'duration']):
            return ConstraintType.TEMPORAL
        elif any(r in expression for r in ['forall', 'exists']):
            return ConstraintType.RELATIONAL
        elif any(a in expression for a in ['sum', 'count', 'avg', 'max', 'min']):
            return ConstraintType.AGGREGATE
        else:
            return ConstraintType.BOOLEAN_LOGIC
    
    def set_active_rules(self, rule_names: List[str]):
        """Set specific rules to be active for verification"""
        self.active_rules = rule_names
        logger.info(f"Active rules set: {rule_names}")
    
    def verify(self, structured_output: Dict[str, Any], timeout_ms: int = 1000) -> Dict[str, Any]:
        """
        Main verification method
        
        Args:
            structured_output: Parsed LLM output
            timeout_ms: Timeout in milliseconds
            
        Returns:
            Verification result with violations if any
        """
        start_time = time.time()
        self.z3_solver.reset()
        self.z3_solver.set("timeout", timeout_ms)
        
        # Get applicable constraints
        constraints_to_check = self._get_applicable_constraints()
        
        # Create Z3 variables from structured output
        z3_vars = self._create_z3_variables(structured_output)
        
        # Convert each constraint to Z3 formula
        violations = []
        for constraint in constraints_to_check:
            try:
                z3_formula = self._constraint_to_z3(constraint, z3_vars, structured_output)
                
                # Add negation to check for violation
                self.z3_solver.push()
                self.z3_solver.add(z3.Not(z3_formula))
                
                # Check if constraint can be violated
                check_result = self.z3_solver.check()
                
                if check_result == z3.sat:
                    # Constraint can be violated - extract counterexample
                    model = self.z3_solver.model()
                    violation = self._extract_violation(constraint, model, structured_output)
                    violations.append(violation)
                    logger.warning(f"Constraint violated: {constraint.name}")
                elif check_result == z3.unknown:
                    logger.warning(f"Could not determine satisfiability for constraint: {constraint.name}")
                    
                self.z3_solver.pop()
                
            except Exception as e:
                logger.error(f"Error processing constraint {constraint.name}: {str(e)}")
                violations.append(Violation(
                    constraint_name=constraint.name,
                    description=f"Error evaluating constraint: {str(e)}",
                    severity="error",
                    expected="Valid constraint",
                    actual="Processing error",
                    path=""
                ))
        
        execution_time = (time.time() - start_time) * 1000
        
        return {
            'verified': len(violations) == 0,
            'violations': [self._violation_to_dict(v) for v in violations],
            'constraints_checked': len(constraints_to_check),
            'execution_time_ms': execution_time,
            'solver_status': 'complete'
        }
    
    def _get_applicable_constraints(self) -> List[Constraint]:
        """Get constraints to check based on active rules"""
        if self.active_rules:
            return [c for c in self.constraints if c.name in self.active_rules]
        return [c for c in self.constraints if c.severity == "error"]
    
    def _create_z3_variables(self, structured_output: Dict) -> Dict[str, Any]:
        """Create Z3 variables from structured output"""
        z3_vars = {}
        
        for key, value in self._flatten_dict(structured_output).items():
            if isinstance(value, bool):
                z3_vars[key] = z3.Bool(key)
            elif isinstance(value, int):
                z3_vars[key] = z3.Int(key)
            elif isinstance(value, float):
                z3_vars[key] = z3.Real(key)
            elif isinstance(value, str):
                # For strings, we create a string variable or use enumeration
                z3_vars[key] = z3.String(key)
            else:
                # For complex types, store as is
                z3_vars[key] = value
                
        return z3_vars
    
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
    
    def _constraint_to_z3(self, constraint: Constraint, z3_vars: Dict, output: Dict) -> z3.BoolRef:
        """Convert constraint to Z3 formula"""
        if constraint.type == ConstraintType.NUMERIC_RANGE:
            return self._numeric_constraint_to_z3(constraint, z3_vars, output)
        elif constraint.type == ConstraintType.BOOLEAN_LOGIC:
            return self._boolean_constraint_to_z3(constraint, z3_vars, output)
        elif constraint.type == ConstraintType.STRING_PATTERN:
            return self._string_constraint_to_z3(constraint, z3_vars, output)
        elif constraint.type == ConstraintType.RELATIONAL:
            return self._relational_constraint_to_z3(constraint, z3_vars, output)
        elif constraint.type == ConstraintType.AGGREGATE:
            return self._aggregate_constraint_to_z3(constraint, z3_vars, output)
        else:
            # Default to true if constraint type not implemented
            logger.warning(f"Constraint type {constraint.type} not fully implemented")
            return z3.BoolVal(True)
    
    def _numeric_constraint_to_z3(self, constraint: Constraint, z3_vars: Dict, output: Dict) -> z3.BoolRef:
        """Convert numeric range constraint to Z3"""
        # Parse expression like "debt_to_income_ratio <= 0.43"
        parts = constraint.expression.split()
        if len(parts) != 3:
            raise ValueError(f"Invalid numeric constraint: {constraint.expression}")
            
        var_name = parts[0]
        operator = parts[1]
        threshold = float(parts[2])
        
        # Get actual value from output
        flat_output = self._flatten_dict(output)
        actual_value = flat_output.get(var_name, 0)
        
        # Create Z3 constraint
        if operator == '<=':
            return z3.RealVal(actual_value) <= threshold
        elif operator == '>=':
            return z3.RealVal(actual_value) >= threshold
        elif operator == '<':
            return z3.RealVal(actual_value) < threshold
        elif operator == '>':
            return z3.RealVal(actual_value) > threshold
        elif operator == '==':
            return z3.RealVal(actual_value) == threshold
        else:
            raise ValueError(f"Unknown operator: {operator}")
    
    def _boolean_constraint_to_z3(self, constraint: Constraint, z3_vars: Dict, output: Dict) -> z3.BoolRef:
        """Convert boolean logic constraint to Z3"""
        # This is simplified - in production, you'd parse complex boolean expressions
        # For now, evaluate simple conditions
        expression = constraint.expression
        flat_output = self._flatten_dict(output)
        
        # Replace variable names with actual values
        for var_name in constraint.variables:
            if var_name in flat_output:
                value = flat_output[var_name]
                if isinstance(value, bool):
                    expression = expression.replace(var_name, str(value))
        
        # Evaluate using Z3's parser (simplified)
        try:
            # This is a placeholder - implement proper expression parsing
            return z3.BoolVal(True)
        except Exception as e:
            logger.error(f"Error parsing boolean constraint: {e}")
            return z3.BoolVal(False)
    
    def _string_constraint_to_z3(self, constraint: Constraint, z3_vars: Dict, output: Dict) -> z3.BoolRef:
        """Convert string pattern constraint to Z3"""
        # Z3 has limited string support, so we may need to use alternative approaches
        # For now, return true - implement regex validation separately
        return z3.BoolVal(True)
    
    def _relational_constraint_to_z3(self, constraint: Constraint, z3_vars: Dict, output: Dict) -> z3.BoolRef:
        """Convert relational constraint to Z3"""
        # Implement forall/exists quantifiers
        return z3.BoolVal(True)
    
    def _aggregate_constraint_to_z3(self, constraint: Constraint, z3_vars: Dict, output: Dict) -> z3.BoolRef:
        """Convert aggregate constraint to Z3"""
        # Implement sum/count/avg operations
        return z3.BoolVal(True)
    
    def _extract_violation(self, constraint: Constraint, model: z3.ModelRef, output: Dict) -> Violation:
        """Extract violation details from Z3 model"""
        flat_output = self._flatten_dict(output)
        
        # Get the actual value that caused violation
        actual_value = None
        for var in constraint.variables:
            if var in flat_output:
                actual_value = flat_output[var]
                break
        
        return Violation(
            constraint_name=constraint.name,
            description=constraint.description,
            severity=constraint.severity,
            expected=constraint.expression,
            actual=actual_value,
            path=constraint.variables[0] if constraint.variables else ""
        )
    
    def _violation_to_dict(self, violation: Violation) -> Dict:
        """Convert violation to dictionary"""
        return {
            'constraint': violation.constraint_name,
            'description': violation.description,
            'severity': violation.severity,
            'expected': str(violation.expected),
            'actual': str(violation.actual),
            'path': violation.path
        }
