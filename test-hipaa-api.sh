#!/bin/bash
# Test HIPAA compliance API - debug the violation display issue

API_KEY="${AARE_API_KEY:-}"
API_URL="https://lofeorzpeh.execute-api.us-west-2.amazonaws.com/prod/verify"

# The exact text from the screenshot that shows "HIPAA VIOLATION DETECTED" but "0 constraints violated"
HIPAA_TEXT="Discharge Summary for Patient #12345 (de-identified per HIPAA §164.514):

Diagnosis: Type 2 Diabetes (ICD-10: E11.9).
Treatment Administered: Standard insulin regimen (details redacted for privacy).
No Known Allergies Noted.
Follow-up: Schedule with endocrinologist within 7 days.

Safeguards Applied: All PHI removed; report for authorized internal use only.
Clinician: Dr. Smith, Role: Attending Physician.
Report generated: 2025-11-30. No breach risk identified.
Encrypted transmission confirmed. Audit trail maintained."

echo "=========================================="
echo "Testing HIPAA Compliance API"
echo "=========================================="
echo ""
echo "Input text:"
echo "$HIPAA_TEXT"
echo ""
echo "=========================================="
echo "API Response:"
echo "=========================================="

# Escape the text for JSON
ESCAPED_TEXT=$(echo "$HIPAA_TEXT" | python3 -c 'import sys,json; print(json.dumps(sys.stdin.read()))')

curl -s -X POST "$API_URL" \
  -H "Content-Type: application/json" \
  -H "x-api-key: $API_KEY" \
  -d "{\"llm_output\": $ESCAPED_TEXT, \"ontology\": \"hipaa-v1\"}" | python3 -m json.tool

echo ""
echo "=========================================="
echo "Key fields to check:"
echo "- verified: should be true if 0 violations"
echo "- violations: should be empty array []"
echo "=========================================="
