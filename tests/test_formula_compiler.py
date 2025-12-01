"""
Tests for Formula Compiler
"""

import pytest
import sys
import os

# Add handlers to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from z3 import Bool, Int, Real, And, Or, Not, Implies, sat, unsat, Solver
from handlers.formula_compiler import FormulaCompiler


class TestFormulaCompiler:
    """Test cases for FormulaCompiler"""

    def setup_method(self):
        """Set up test fixtures"""
        self.compiler = FormulaCompiler()

    def test_simple_less_than_or_equal(self):
        """Test simple <= comparison"""
        formula = {"<=": ["x", 43]}
        z3_vars = {"x": Real("x")}

        result = self.compiler.compile(formula, z3_vars)

        # Verify with Z3
        solver = Solver()
        solver.add(z3_vars["x"] == 40)
        solver.add(Not(result))
        assert solver.check() == unsat  # 40 <= 43 is true, so Not(result) is unsat

    def test_simple_greater_than_or_equal(self):
        """Test simple >= comparison"""
        formula = {">=": ["x", 2]}
        z3_vars = {"x": Int("x")}

        result = self.compiler.compile(formula, z3_vars)

        solver = Solver()
        solver.add(z3_vars["x"] == 3)
        solver.add(Not(result))
        assert solver.check() == unsat  # 3 >= 2 is true

    def test_or_operator(self):
        """Test OR operator"""
        formula = {
            "or": [
                {"<=": ["dti", 43]},
                {">=": ["factors", 2]}
            ]
        }
        z3_vars = {"dti": Real("dti"), "factors": Int("factors")}

        result = self.compiler.compile(formula, z3_vars)

        # Case 1: dti = 40 (satisfies first clause)
        solver = Solver()
        solver.add(z3_vars["dti"] == 40)
        solver.add(z3_vars["factors"] == 0)
        solver.add(Not(result))
        assert solver.check() == unsat  # (40 <= 43) OR (0 >= 2) is true

        # Case 2: dti = 50, factors = 2 (satisfies second clause)
        solver = Solver()
        solver.add(z3_vars["dti"] == 50)
        solver.add(z3_vars["factors"] == 2)
        solver.add(Not(result))
        assert solver.check() == unsat  # (50 <= 43) OR (2 >= 2) is true

        # Case 3: dti = 50, factors = 1 (violates both)
        solver = Solver()
        solver.add(z3_vars["dti"] == 50)
        solver.add(z3_vars["factors"] == 1)
        solver.add(Not(result))
        assert solver.check() == sat  # (50 <= 43) OR (1 >= 2) is false

    def test_and_operator(self):
        """Test AND operator"""
        formula = {
            "and": [
                {"==": ["a", True]},
                {"==": ["b", True]}
            ]
        }
        z3_vars = {"a": Bool("a"), "b": Bool("b")}

        result = self.compiler.compile(formula, z3_vars)

        # Both true - constraint satisfied
        solver = Solver()
        solver.add(z3_vars["a"] == True)
        solver.add(z3_vars["b"] == True)
        solver.add(Not(result))
        assert solver.check() == unsat

        # One false - constraint violated
        solver = Solver()
        solver.add(z3_vars["a"] == True)
        solver.add(z3_vars["b"] == False)
        solver.add(Not(result))
        assert solver.check() == sat

    def test_not_operator(self):
        """Test NOT operator"""
        formula = {"not": {"==": ["x", True]}}
        z3_vars = {"x": Bool("x")}

        result = self.compiler.compile(formula, z3_vars)

        # x = False -> Not(True) = False... wait, let me think this through
        # formula is ¬(x == True), which means x should be False for constraint to be satisfied
        solver = Solver()
        solver.add(z3_vars["x"] == False)
        solver.add(Not(result))
        assert solver.check() == unsat  # ¬(False == True) = ¬False = True

        solver = Solver()
        solver.add(z3_vars["x"] == True)
        solver.add(Not(result))
        assert solver.check() == sat  # ¬(True == True) = ¬True = False

    def test_implies_operator(self):
        """Test IMPLIES operator"""
        formula = {
            "implies": [
                {"==": ["denial", True]},
                {"==": ["reason", True]}
            ]
        }
        z3_vars = {"denial": Bool("denial"), "reason": Bool("reason")}

        result = self.compiler.compile(formula, z3_vars)

        # denial=True, reason=True -> satisfied (T -> T = T)
        solver = Solver()
        solver.add(z3_vars["denial"] == True)
        solver.add(z3_vars["reason"] == True)
        solver.add(Not(result))
        assert solver.check() == unsat

        # denial=False, reason=False -> satisfied (F -> F = T)
        solver = Solver()
        solver.add(z3_vars["denial"] == False)
        solver.add(z3_vars["reason"] == False)
        solver.add(Not(result))
        assert solver.check() == unsat

        # denial=True, reason=False -> violated (T -> F = F)
        solver = Solver()
        solver.add(z3_vars["denial"] == True)
        solver.add(z3_vars["reason"] == False)
        solver.add(Not(result))
        assert solver.check() == sat

    def test_complex_nested_formula(self):
        """Test complex nested formula: ¬(has_guarantee ∧ has_approval)"""
        formula = {
            "not": {
                "and": [
                    {"==": ["has_guarantee", True]},
                    {"==": ["has_approval", True]}
                ]
            }
        }
        z3_vars = {
            "has_guarantee": Bool("has_guarantee"),
            "has_approval": Bool("has_approval")
        }

        result = self.compiler.compile(formula, z3_vars)

        # Both True -> violated (can't have both)
        solver = Solver()
        solver.add(z3_vars["has_guarantee"] == True)
        solver.add(z3_vars["has_approval"] == True)
        solver.add(Not(result))
        assert solver.check() == sat

        # One True, one False -> satisfied
        solver = Solver()
        solver.add(z3_vars["has_guarantee"] == True)
        solver.add(z3_vars["has_approval"] == False)
        solver.add(Not(result))
        assert solver.check() == unsat

    def test_dti_mortgage_formula(self):
        """Test the actual DTI mortgage formula from the ontology"""
        formula = {
            "or": [
                {"<=": ["dti", 43]},
                {">=": ["compensating_factors", 2]}
            ]
        }
        z3_vars = {
            "dti": Real("dti"),
            "compensating_factors": Int("compensating_factors")
        }

        result = self.compiler.compile(formula, z3_vars)

        # DTI 50%, no factors -> violation
        solver = Solver()
        solver.add(z3_vars["dti"] == 50)
        solver.add(z3_vars["compensating_factors"] == 0)
        solver.add(Not(result))
        assert solver.check() == sat

        # DTI 50%, 2 factors -> passes
        solver = Solver()
        solver.add(z3_vars["dti"] == 50)
        solver.add(z3_vars["compensating_factors"] == 2)
        solver.add(Not(result))
        assert solver.check() == unsat

        # DTI 40%, 0 factors -> passes
        solver = Solver()
        solver.add(z3_vars["dti"] == 40)
        solver.add(z3_vars["compensating_factors"] == 0)
        solver.add(Not(result))
        assert solver.check() == unsat

    def test_unknown_variable_raises_error(self):
        """Test that unknown variables raise an error"""
        formula = {"<=": ["unknown_var", 43]}
        z3_vars = {"x": Real("x")}

        with pytest.raises(ValueError, match="Unknown variable"):
            self.compiler.compile(formula, z3_vars)

    def test_null_formula_returns_true(self):
        """Test that None formula returns BoolVal(True)"""
        result = self.compiler.compile(None, {})

        solver = Solver()
        solver.add(Not(result))
        assert solver.check() == unsat  # True can't be violated

    def test_equality_with_boolean_false(self):
        """Test equality comparison with False"""
        formula = {"==": ["x", False]}
        z3_vars = {"x": Bool("x")}

        result = self.compiler.compile(formula, z3_vars)

        # x = False -> satisfied
        solver = Solver()
        solver.add(z3_vars["x"] == False)
        solver.add(Not(result))
        assert solver.check() == unsat

        # x = True -> violated
        solver = Solver()
        solver.add(z3_vars["x"] == True)
        solver.add(Not(result))
        assert solver.check() == sat

    def test_strict_less_than(self):
        """Test < operator"""
        formula = {"<": ["fee_pct", 8]}
        z3_vars = {"fee_pct": Real("fee_pct")}

        result = self.compiler.compile(formula, z3_vars)

        # 7 < 8 -> satisfied
        solver = Solver()
        solver.add(z3_vars["fee_pct"] == 7)
        solver.add(Not(result))
        assert solver.check() == unsat

        # 8 < 8 -> violated (not strictly less than)
        solver = Solver()
        solver.add(z3_vars["fee_pct"] == 8)
        solver.add(Not(result))
        assert solver.check() == sat

    def test_strict_greater_than(self):
        """Test > operator"""
        formula = {">": ["score", 600]}
        z3_vars = {"score": Int("score")}

        result = self.compiler.compile(formula, z3_vars)

        # 650 > 600 -> satisfied
        solver = Solver()
        solver.add(z3_vars["score"] == 650)
        solver.add(Not(result))
        assert solver.check() == unsat

        # 600 > 600 -> violated
        solver = Solver()
        solver.add(z3_vars["score"] == 600)
        solver.add(Not(result))
        assert solver.check() == sat

    def test_multiple_operators_raises_error(self):
        """Test that multiple operators in one dict raises an error"""
        formula = {"and": [{"==": ["x", True]}], "or": [{"==": ["y", True]}]}
        z3_vars = {"x": Bool("x"), "y": Bool("y")}

        with pytest.raises(ValueError, match="multiple operators"):
            self.compiler.compile(formula, z3_vars)

    def test_ite_operator(self):
        """Test if-then-else (ite) operator"""
        # if x > 10 then 100 else 0
        formula = {
            "ite": [
                {">": ["x", 10]},
                100,
                0
            ]
        }
        z3_vars = {"x": Int("x")}

        result = self.compiler.compile(formula, z3_vars)

        # x = 15 -> result should be 100
        solver = Solver()
        solver.add(z3_vars["x"] == 15)
        solver.add(result != 100)
        assert solver.check() == unsat

        # x = 5 -> result should be 0
        solver = Solver()
        solver.add(z3_vars["x"] == 5)
        solver.add(result != 0)
        assert solver.check() == unsat

    def test_min_operator(self):
        """Test min operator: fee capped at lesser of $500 or 3% of loan"""
        # min(500, loan * 0.03)
        formula = {
            "min": [
                500,
                {"*": ["loan", 0.03]}
            ]
        }
        z3_vars = {"loan": Real("loan")}

        result = self.compiler.compile(formula, z3_vars)

        # loan = 10000 -> 3% = 300, min(500, 300) = 300
        solver = Solver()
        solver.add(z3_vars["loan"] == 10000)
        solver.add(result != 300)
        assert solver.check() == unsat

        # loan = 20000 -> 3% = 600, min(500, 600) = 500
        solver = Solver()
        solver.add(z3_vars["loan"] == 20000)
        solver.add(result != 500)
        assert solver.check() == unsat

    def test_max_operator(self):
        """Test max operator"""
        formula = {"max": ["a", "b"]}
        z3_vars = {"a": Int("a"), "b": Int("b")}

        result = self.compiler.compile(formula, z3_vars)

        # a=10, b=5 -> max = 10
        solver = Solver()
        solver.add(z3_vars["a"] == 10)
        solver.add(z3_vars["b"] == 5)
        solver.add(result != 10)
        assert solver.check() == unsat

        # a=3, b=7 -> max = 7
        solver = Solver()
        solver.add(z3_vars["a"] == 3)
        solver.add(z3_vars["b"] == 7)
        solver.add(result != 7)
        assert solver.check() == unsat

    def test_fee_cap_constraint(self):
        """Test realistic constraint: fee <= min(500, loan * 0.03)"""
        formula = {
            "<=": [
                "fee",
                {"min": [500, {"*": ["loan", 0.03]}]}
            ]
        }
        z3_vars = {
            "fee": Real("fee"),
            "loan": Real("loan")
        }

        result = self.compiler.compile(formula, z3_vars)

        # loan=10000, fee=250 -> 250 <= min(500, 300) = 250 <= 300 ✓
        solver = Solver()
        solver.add(z3_vars["loan"] == 10000)
        solver.add(z3_vars["fee"] == 250)
        solver.add(Not(result))
        assert solver.check() == unsat

        # loan=10000, fee=350 -> 350 <= min(500, 300) = 350 <= 300 ✗
        solver = Solver()
        solver.add(z3_vars["loan"] == 10000)
        solver.add(z3_vars["fee"] == 350)
        solver.add(Not(result))
        assert solver.check() == sat
