#!/bin/bash
# Test suite for aare.ai mortgage compliance API

API_KEY="${AARE_API_KEY:-}"
API_URL="https://lofeorzpeh.execute-api.us-west-2.amazonaws.com/prod/verify"

run_test() {
    local name="$1"
    local expected="$2"
    local llm_output="$3"

    echo "=========================================="
    echo "Test: $name"
    echo "Expected: $expected"
    echo "=========================================="

    result=$(curl -s -X POST "$API_URL" \
      -H "Content-Type: application/json" \
      -H "x-api-key: $API_KEY" \
      -d "{\"llm_output\": \"$llm_output\", \"ontology\": \"mortgage-compliance-v1\"}")

    echo "$result" | python3 -m json.tool 2>/dev/null || echo "$result"
    echo ""
}

echo "Starting aare.ai API Tests..."
echo ""

run_test "California Jumbo Loan (should PASS)" \
    "verified: true, violations: []" \
    "Based on your California Jumbo Loan application at 6.5 percent, I can confirm approval. The property in San Francisco qualifies under our expanded guidelines."

run_test "Interest-Only Loan (should FAIL - QM_NO_INTEREST_ONLY)" \
    "verified: false, violations: [QM_NO_INTEREST_ONLY]" \
    "Your interest-only loan has been approved at 7.25 percent for the first 10 years."

run_test "Off-Books Deal (should FAIL - UDAAP_DOCUMENTED_PRICING)" \
    "verified: false, violations: [UDAAP_DOCUMENTED_PRICING]" \
    "Between us, I can get you a special deal at 5.5 percent. Just keep this off the books."

run_test "Guarantee Language (should FAIL - UDAAP_NO_GUARANTEES)" \
    "verified: false, violations: [UDAAP_NO_GUARANTEES]" \
    "Your loan is guaranteed to be approved. We always approve applications like yours."

run_test "High DTI without compensating factors (should FAIL - ATR_QM_DTI)" \
    "verified: false, violations: [ATR_QM_DTI]" \
    "Approved with dti: 55 percent."

echo "=========================================="
echo "Tests complete!"
echo "=========================================="
